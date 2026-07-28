#include <AccelStepper.h>
#include <Servo.h>
#include <math.h>

#include "config.h"

// ============================================================================
//  SCARA robot firmware - Arduino Mega 2560 + 4x TB6600 + AccelStepper.
// ----------------------------------------------------------------------------
//  Osie:
//    J1   - bark   (cykloidalna 20:1), krancowka na pinie 2 (INT)
//    J2   - lokiec (cykloidalna 14:1), krancowka na pinie 3 (INT)
//    Z    - sruba napedowa,            krancowka na pinie 18 (INT)
//    TOOL - efektor (pasek GT2), bez krancowki (zero programowe)
//
//  Protokol szeregowy (115200, linie zakonczone '\n') dla hosta Python:
//    Kazda komenda otrzymuje dokladnie jedna linie odpowiedzi:
//      "OK[ dane]"  albo  "ERR <KOD> <opis>"
//    Po zakonczeniu kazdego ruchu kontroler wysyla asynchronicznie "DONE".
//
//  Komendy:
//    PING                        -> OK PONG
//    VERSION                     -> OK SCARA-FW 2.0
//    STATUS                      -> OK STATE=<IDLE|MOVING|HOMING> HOMED=<0|1>
//                                      X=.. Y=.. Z=.. J1=.. J2=.. TOOL=..
//    HOME                        homing wszystkich osi (Z -> J1 -> J2)
//    HOME J1|J2|Z                homing jednej osi
//    MOVE X<f> Y<f> [Z<f>] [T<f>] [E0|E1]   ruch IK do punktu (mm/stopnie);
//                                E0 = lokiec "down", E1 = "up" (domyslnie E1)
//    JOG J1|J2|TOOL <deg>        ruch osi do zadanego kata (bez IK)
//    JOG Z <mm>                  ruch osi Z do zadanej wysokosci
//    IK X<f> Y<f> [E0|E1]        tylko obliczenie IK (bez ruchu) -> OK J1=.. J2=..
//    SPEED <10-100>              globalny procent predkosci wszystkich osi
//    GRIP 0|1                    gripper (serwo SG90): 0 = otwarty, 1 = zamkniety
//    STOP                        zatrzymanie z rampa hamowania
//    ESTOP                       natychmiastowe zatrzymanie + DISABLE
//    ENABLE / DISABLE            zalaczenie / odlaczenie sterownikow
//
//  Kody bledow: BAD_CMD, NOT_HOMED, OUT_OF_REACH, EXCLUSION_ZONE,
//               JOINT_LIMIT, BUSY, LIMIT_HIT, HOMING_FAIL, AXIS_DISABLED
// ============================================================================

AccelStepper axisJ1(AccelStepper::DRIVER, PIN_J1_STEP, PIN_J1_DIR);
AccelStepper axisJ2(AccelStepper::DRIVER, PIN_J2_STEP, PIN_J2_DIR);
AccelStepper axisZ(AccelStepper::DRIVER, PIN_Z_STEP, PIN_Z_DIR);
AccelStepper axisTool(AccelStepper::DRIVER, PIN_TOOL_STEP, PIN_TOOL_DIR);

Servo gripperServo;
bool gripperClosed = false;
uint8_t speedPercent = SPEED_PERCENT_DEFAULT;

enum class State : uint8_t { IDLE, MOVING, HOMING };

State state = State::IDLE;
bool homedJ1 = false;
bool homedJ2 = false;
bool homedZ = false;
bool motionDoneReported = true;

// Flagi ustawiane w ISR krancowek. Poza homingiem trafienie krancowki
// oznacza utrate pozycji -> natychmiastowy stop i wymagany ponowny homing.
volatile bool limitHitJ1 = false;
volatile bool limitHitJ2 = false;
volatile bool limitHitZ = false;
volatile bool limitMonitoringEnabled = false;

char lineBuffer[96];
uint8_t lineLength = 0;

// ---------------------------------------------------------------- ISR
void isrLimitJ1() {
  if (limitMonitoringEnabled) limitHitJ1 = true;
}
void isrLimitJ2() {
  if (limitMonitoringEnabled) limitHitJ2 = true;
}
void isrLimitZ() {
  if (limitMonitoringEnabled) limitHitZ = true;
}

// ------------------------------------------------------------- helpers
bool allHomed() { return homedJ1 && homedZ && (homedJ2 || !ELBOW_PRESENT); }

float scaledSpeed(float base) { return base * (float)speedPercent / 100.0f; }

// Skalowanie predkosci wszystkich osi wg globalnego procentu.
void applySpeedScale() {
  axisJ1.setMaxSpeed(scaledSpeed(J1_MAX_SPEED));
  axisJ2.setMaxSpeed(scaledSpeed(J2_MAX_SPEED));
  axisZ.setMaxSpeed(scaledSpeed(Z_MAX_SPEED));
  axisTool.setMaxSpeed(scaledSpeed(TOOL_MAX_SPEED));
}

bool limitPressed(uint8_t pin) { return digitalRead(pin) == LIMIT_ACTIVE_STATE; }

float j1Degrees() { return axisJ1.currentPosition() / STEPS_PER_DEG_J1; }
float j2Degrees() { return axisJ2.currentPosition() / STEPS_PER_DEG_J2; }
float zMillimeters() { return axisZ.currentPosition() / STEPS_PER_MM_Z; }
float toolDegrees() { return axisTool.currentPosition() / STEPS_PER_DEG_TOOL; }

bool anyAxisMoving() {
  return axisJ1.distanceToGo() != 0 || axisZ.distanceToGo() != 0 ||
         axisTool.distanceToGo() != 0 ||
         (ELBOW_PRESENT && axisJ2.distanceToGo() != 0);
}

void sendOk() { Serial.println(F("OK")); }

void sendErr(const __FlashStringHelper* code, const __FlashStringHelper* msg) {
  Serial.print(F("ERR "));
  Serial.print(code);
  Serial.print(F(" "));
  Serial.println(msg);
}

// --------------------------------------------------------- kinematyka
// Kinematyka prosta: katy stawow [deg] -> pozycja TCP [mm] w ukladzie barku.
void forwardKinematics(float j1Deg, float j2Deg, float& x, float& y) {
  const float t1 = radians(j1Deg);
  const float t12 = radians(j1Deg + j2Deg);
  x = ARM_L1_MM * cosf(t1) + ARM_L2_MM * cosf(t12);
  y = ARM_L1_MM * sinf(t1) + ARM_L2_MM * sinf(t12);
}

// Kinematyka odwrotna: (x, y) [mm] -> katy stawow [deg].
// elbowUp: true -> t2 >= 0 ("up"), false -> t2 <= 0 ("down").
// Zwraca false, gdy punkt jest poza pierscieniem zasiegu.
bool inverseKinematics(float x, float y, bool elbowUp, float& j1Deg, float& j2Deg) {
  const float r2 = x * x + y * y;
  const float r = sqrtf(r2);
  if (r > MAX_REACH_MM + 0.001f || r < MIN_REACH_MM - 0.001f) {
    return false;
  }

  float cosT2 = (r2 - ARM_L1_MM * ARM_L1_MM - ARM_L2_MM * ARM_L2_MM) /
                (2.0f * ARM_L1_MM * ARM_L2_MM);
  cosT2 = constrain(cosT2, -1.0f, 1.0f);
  float t2 = acosf(cosT2);
  if (!elbowUp) t2 = -t2;

  const float t1 = atan2f(y, x) -
                   atan2f(ARM_L2_MM * sinf(t2), ARM_L1_MM + ARM_L2_MM * cosf(t2));

  j1Deg = degrees(t1);
  j2Deg = degrees(t2);
  return true;
}

// Kolumna Z stoi w punkcie (-Z_AXIS_OFFSET_MM, 0) ukladu barku.
// Punkt docelowy nie moze wejsc w strefe wykluczenia wokol kolumny.
bool insideColumnExclusion(float x, float y) {
  const float dx = x + Z_AXIS_OFFSET_MM;
  const float dy = y;
  return (dx * dx + dy * dy) < (Z_COL_EXCLUSION_R * Z_COL_EXCLUSION_R);
}

bool jointsWithinLimits(float j1Deg, float j2Deg) {
  if (j1Deg < J1_MIN_DEG || j1Deg > J1_MAX_DEG) return false;
  if (ELBOW_PRESENT && (j2Deg < J2_MIN_DEG || j2Deg > J2_MAX_DEG)) return false;
  return true;
}

// --------------------------------------------------------------- ruch
void enableAll() {
  axisJ1.enableOutputs();
  axisZ.enableOutputs();
  axisTool.enableOutputs();
  if (ELBOW_PRESENT) axisJ2.enableOutputs();
}

void disableAll() {
  axisJ1.disableOutputs();
  axisJ2.disableOutputs();
  axisZ.disableOutputs();
  axisTool.disableOutputs();
}

void stopAllRamped() {
  axisJ1.stop();
  axisJ2.stop();
  axisZ.stop();
  axisTool.stop();
}

void emergencyStop() {
  // Zerujemy zadane cele w miejscu - bez rampy.
  axisJ1.setCurrentPosition(axisJ1.currentPosition());
  axisJ2.setCurrentPosition(axisJ2.currentPosition());
  axisZ.setCurrentPosition(axisZ.currentPosition());
  axisTool.setCurrentPosition(axisTool.currentPosition());
  disableAll();
  homedJ1 = homedJ2 = homedZ = false;
  state = State::IDLE;
  motionDoneReported = true;
}

void runAllAxes() {
  axisJ1.run();
  axisZ.run();
  axisTool.run();
  if (ELBOW_PRESENT) axisJ2.run();
}

// ------------------------------------------------------------- homing
// Sekwencja: szybki najazd -> odjazd -> wolny najazd (latch) -> zero osi.
bool homeAxisBlocking(AccelStepper& axis, uint8_t limitPin, int8_t dir,
                      long homeSteps, float restoreSpeed) {
  limitMonitoringEnabled = false;  // ISR nie moze przerywac homingu

  const float savedSpeed = restoreSpeed;

  // Faza 1: szybki najazd na krancowke.
  axis.setMaxSpeed(HOMING_SEEK_SPEED);
  axis.move((long)dir * HOMING_MAX_TRAVEL_STEPS);
  while (!limitPressed(limitPin)) {
    if (axis.distanceToGo() == 0) {
      axis.setMaxSpeed(savedSpeed);
      return false;  // przejechano caly zakres bez trafienia
    }
    axis.run();
  }
  axis.stop();
  while (axis.distanceToGo() != 0) axis.run();

  // Faza 2: odjazd od krancowki.
  axis.move((long)(-dir) * HOMING_BACKOFF_STEPS);
  while (axis.distanceToGo() != 0) axis.run();

  // Faza 3: wolny najazd - dokladny latch pozycji.
  axis.setMaxSpeed(HOMING_LATCH_SPEED);
  axis.move((long)dir * (HOMING_BACKOFF_STEPS * 4L));
  while (!limitPressed(limitPin)) {
    if (axis.distanceToGo() == 0) {
      axis.setMaxSpeed(savedSpeed);
      return false;
    }
    axis.run();
  }
  axis.setCurrentPosition(homeSteps);

  // Odjazd na pozycje spoczynkowa tuz za krancowka.
  axis.setMaxSpeed(savedSpeed);
  axis.move((long)(-dir) * HOMING_BACKOFF_STEPS);
  while (axis.distanceToGo() != 0) axis.run();

  limitMonitoringEnabled = true;
  return true;
}

bool homeZ() {
  const bool ok = homeAxisBlocking(
      axisZ, LIMIT_PIN_Z, HOMING_DIR_Z,
      lroundf(Z_HOME_POS_MM * STEPS_PER_MM_Z), scaledSpeed(Z_MAX_SPEED));
  homedZ = ok;
  return ok;
}

bool homeJ1() {
  const bool ok = homeAxisBlocking(
      axisJ1, LIMIT_PIN_J1, HOMING_DIR_J1,
      lroundf(J1_HOME_POS_DEG * STEPS_PER_DEG_J1), scaledSpeed(J1_MAX_SPEED));
  homedJ1 = ok;
  return ok;
}

bool homeJ2() {
  if (!ELBOW_PRESENT) {
    homedJ2 = true;
    axisJ2.setCurrentPosition(0);
    return true;
  }
  const bool ok = homeAxisBlocking(
      axisJ2, LIMIT_PIN_J2, HOMING_DIR_J2,
      lroundf(J2_HOME_POS_DEG * STEPS_PER_DEG_J2), scaledSpeed(J2_MAX_SPEED));
  homedJ2 = ok;
  return ok;
}

// ---------------------------------------------------------- komendy
// Wyszukuje w komendzie parametr postaci "<litera><liczba>", np. X120.5.
bool parseParam(const char* cmd, char key, float& out) {
  for (const char* p = cmd; *p != '\0'; ++p) {
    if (*p == key && (p == cmd || *(p - 1) == ' ')) {
      out = atof(p + 1);
      return true;
    }
  }
  return false;
}

void printStatus() {
  float x, y;
  forwardKinematics(j1Degrees(), j2Degrees(), x, y);
  Serial.print(F("OK STATE="));
  switch (state) {
    case State::IDLE: Serial.print(F("IDLE")); break;
    case State::MOVING: Serial.print(F("MOVING")); break;
    case State::HOMING: Serial.print(F("HOMING")); break;
  }
  Serial.print(F(" HOMED="));
  Serial.print(allHomed() ? 1 : 0);
  Serial.print(F(" X="));
  Serial.print(x, 3);
  Serial.print(F(" Y="));
  Serial.print(y, 3);
  Serial.print(F(" Z="));
  Serial.print(zMillimeters(), 3);
  Serial.print(F(" J1="));
  Serial.print(j1Degrees(), 3);
  Serial.print(F(" J2="));
  Serial.print(j2Degrees(), 3);
  Serial.print(F(" TOOL="));
  Serial.print(toolDegrees(), 3);
  Serial.print(F(" SPEED="));
  Serial.print(speedPercent);
  Serial.print(F(" GRIP="));
  Serial.println(gripperClosed ? 1 : 0);
}

void commandSpeed(const char* args) {
  const int pct = atoi(args);
  if (pct < SPEED_PERCENT_MIN || pct > SPEED_PERCENT_MAX) {
    sendErr(F("BAD_CMD"), F("uzycie: SPEED <10-100>"));
    return;
  }
  speedPercent = (uint8_t)pct;
  applySpeedScale();
  sendOk();
}

void commandGrip(const char* args) {
  if (args[0] == '0' && args[1] == '\0') {
    gripperClosed = false;
    gripperServo.write(GRIPPER_OPEN_DEG);
  } else if (args[0] == '1' && args[1] == '\0') {
    gripperClosed = true;
    gripperServo.write(GRIPPER_CLOSED_DEG);
  } else {
    sendErr(F("BAD_CMD"), F("uzycie: GRIP 0|1"));
    return;
  }
  sendOk();
}

void commandHome(const char* args) {
  state = State::HOMING;
  bool ok = true;
  if (args[0] == '\0') {
    ok = homeZ() && homeJ1() && homeJ2();  // Z pierwsze - unosi ramie
  } else if (strcmp(args, "Z") == 0) {
    ok = homeZ();
  } else if (strcmp(args, "J1") == 0) {
    ok = homeJ1();
  } else if (strcmp(args, "J2") == 0) {
    ok = homeJ2();
  } else {
    state = State::IDLE;
    sendErr(F("BAD_CMD"), F("uzycie: HOME [J1|J2|Z]"));
    return;
  }
  state = State::IDLE;
  limitMonitoringEnabled = true;
  if (ok) {
    sendOk();
  } else {
    sendErr(F("HOMING_FAIL"), F("krancowka nieosiagnieta w zakresie ruchu"));
  }
}

void commandMove(const char* args) {
  if (!allHomed()) {
    sendErr(F("NOT_HOMED"), F("wykonaj HOME przed ruchem"));
    return;
  }
  float x = NAN, y = NAN, z = NAN, tool = NAN, elbowFlag = 1.0f;
  const bool hasX = parseParam(args, 'X', x);
  const bool hasY = parseParam(args, 'Y', y);
  const bool hasZ = parseParam(args, 'Z', z);
  const bool hasTool = parseParam(args, 'T', tool);
  parseParam(args, 'E', elbowFlag);

  if (!hasX || !hasY) {
    sendErr(F("BAD_CMD"), F("uzycie: MOVE X<mm> Y<mm> [Z<mm>] [T<deg>] [E0|E1]"));
    return;
  }
  if (insideColumnExclusion(x, y)) {
    sendErr(F("EXCLUSION_ZONE"), F("punkt w strefie kolizji z kolumna Z"));
    return;
  }

  float j1, j2;
  if (!inverseKinematics(x, y, elbowFlag >= 0.5f, j1, j2)) {
    sendErr(F("OUT_OF_REACH"), F("punkt poza zasiegiem ramienia"));
    return;
  }
  // Bez fizycznego lokcia osiagalne sa tylko punkty z J2 = 0.
  if (!ELBOW_PRESENT && fabsf(j2) > 0.05f) {
    sendErr(F("OUT_OF_REACH"), F("lokiec wylaczony - punkt nieosiagalny"));
    return;
  }
  if (!jointsWithinLimits(j1, j2)) {
    sendErr(F("JOINT_LIMIT"), F("rozwiazanie IK poza limitami stawow"));
    return;
  }
  if (hasZ && (z < Z_MIN_MM || z > Z_MAX_MM)) {
    sendErr(F("JOINT_LIMIT"), F("Z poza zakresem"));
    return;
  }
  if (hasTool && (tool < TOOL_MIN_DEG || tool > TOOL_MAX_DEG)) {
    sendErr(F("JOINT_LIMIT"), F("TOOL poza zakresem"));
    return;
  }

  axisJ1.moveTo(lroundf(j1 * STEPS_PER_DEG_J1));
  if (ELBOW_PRESENT) axisJ2.moveTo(lroundf(j2 * STEPS_PER_DEG_J2));
  if (hasZ) axisZ.moveTo(lroundf(z * STEPS_PER_MM_Z));
  if (hasTool) axisTool.moveTo(lroundf(tool * STEPS_PER_DEG_TOOL));

  state = State::MOVING;
  motionDoneReported = false;
  Serial.print(F("OK J1="));
  Serial.print(j1, 3);
  Serial.print(F(" J2="));
  Serial.println(j2, 3);
}

void commandJog(const char* args) {
  if (!allHomed()) {
    sendErr(F("NOT_HOMED"), F("wykonaj HOME przed ruchem"));
    return;
  }
  char axisName[8];
  float value;
  if (sscanf(args, "%7s %f", axisName, &value) != 2) {
    sendErr(F("BAD_CMD"), F("uzycie: JOG J1|J2|Z|TOOL <wartosc>"));
    return;
  }
  if (strcmp(axisName, "J1") == 0) {
    if (value < J1_MIN_DEG || value > J1_MAX_DEG) {
      sendErr(F("JOINT_LIMIT"), F("J1 poza zakresem"));
      return;
    }
    axisJ1.moveTo(lroundf(value * STEPS_PER_DEG_J1));
  } else if (strcmp(axisName, "J2") == 0) {
    if (!ELBOW_PRESENT) {
      sendErr(F("AXIS_DISABLED"), F("lokiec wylaczony (ELBOW_PRESENT=0)"));
      return;
    }
    if (value < J2_MIN_DEG || value > J2_MAX_DEG) {
      sendErr(F("JOINT_LIMIT"), F("J2 poza zakresem"));
      return;
    }
    axisJ2.moveTo(lroundf(value * STEPS_PER_DEG_J2));
  } else if (strcmp(axisName, "Z") == 0) {
    if (value < Z_MIN_MM || value > Z_MAX_MM) {
      sendErr(F("JOINT_LIMIT"), F("Z poza zakresem"));
      return;
    }
    axisZ.moveTo(lroundf(value * STEPS_PER_MM_Z));
  } else if (strcmp(axisName, "TOOL") == 0) {
    if (value < TOOL_MIN_DEG || value > TOOL_MAX_DEG) {
      sendErr(F("JOINT_LIMIT"), F("TOOL poza zakresem"));
      return;
    }
    axisTool.moveTo(lroundf(value * STEPS_PER_DEG_TOOL));
  } else {
    sendErr(F("BAD_CMD"), F("nieznana os (J1|J2|Z|TOOL)"));
    return;
  }
  state = State::MOVING;
  motionDoneReported = false;
  sendOk();
}

void commandIkOnly(const char* args) {
  float x = NAN, y = NAN, elbowFlag = 1.0f;
  if (!parseParam(args, 'X', x) || !parseParam(args, 'Y', y)) {
    sendErr(F("BAD_CMD"), F("uzycie: IK X<mm> Y<mm> [E0|E1]"));
    return;
  }
  parseParam(args, 'E', elbowFlag);
  float j1, j2;
  if (!inverseKinematics(x, y, elbowFlag >= 0.5f, j1, j2)) {
    sendErr(F("OUT_OF_REACH"), F("punkt poza zasiegiem ramienia"));
    return;
  }
  Serial.print(F("OK J1="));
  Serial.print(j1, 4);
  Serial.print(F(" J2="));
  Serial.print(j2, 4);
  Serial.print(F(" REACHABLE="));
  Serial.println(jointsWithinLimits(j1, j2) && !insideColumnExclusion(x, y) ? 1 : 0);
}

void processCommand(char* cmd) {
  // Normalizacja: wielkie litery.
  for (char* p = cmd; *p != '\0'; ++p) *p = toupper(*p);

  if (state == State::MOVING && anyAxisMoving() &&
      strncmp(cmd, "STOP", 4) != 0 && strncmp(cmd, "ESTOP", 5) != 0 &&
      strncmp(cmd, "STATUS", 6) != 0 && strncmp(cmd, "PING", 4) != 0 &&
      strncmp(cmd, "SPEED", 5) != 0 && strncmp(cmd, "GRIP", 4) != 0) {
    sendErr(F("BUSY"), F("ruch w toku - uzyj STOP lub poczekaj na DONE"));
    return;
  }

  if (strcmp(cmd, "PING") == 0) {
    Serial.println(F("OK PONG"));
  } else if (strcmp(cmd, "VERSION") == 0) {
    Serial.print(F("OK "));
    Serial.println(F(FW_VERSION));
  } else if (strcmp(cmd, "STATUS") == 0) {
    printStatus();
  } else if (strncmp(cmd, "HOME", 4) == 0) {
    const char* args = cmd + 4;
    while (*args == ' ') ++args;
    commandHome(args);
  } else if (strncmp(cmd, "MOVE ", 5) == 0) {
    commandMove(cmd + 5);
  } else if (strncmp(cmd, "JOG ", 4) == 0) {
    commandJog(cmd + 4);
  } else if (strncmp(cmd, "IK ", 3) == 0) {
    commandIkOnly(cmd + 3);
  } else if (strncmp(cmd, "SPEED ", 6) == 0) {
    commandSpeed(cmd + 6);
  } else if (strncmp(cmd, "GRIP ", 5) == 0) {
    commandGrip(cmd + 5);
  } else if (strcmp(cmd, "STOP") == 0) {
    stopAllRamped();
    sendOk();
  } else if (strcmp(cmd, "ESTOP") == 0) {
    emergencyStop();
    sendOk();
  } else if (strcmp(cmd, "ENABLE") == 0) {
    enableAll();
    sendOk();
  } else if (strcmp(cmd, "DISABLE") == 0) {
    disableAll();
    homedJ1 = homedJ2 = homedZ = false;  // pozycja niepewna po odlaczeniu
    sendOk();
  } else {
    sendErr(F("BAD_CMD"), F("nieznana komenda"));
  }
}

void handleSerial() {
  while (Serial.available() > 0) {
    const char incoming = (char)Serial.read();
    if (incoming == '\n' || incoming == '\r') {
      if (lineLength > 0) {
        lineBuffer[lineLength] = '\0';
        processCommand(lineBuffer);
        lineLength = 0;
      }
      continue;
    }
    if (lineLength < sizeof(lineBuffer) - 1) {
      lineBuffer[lineLength++] = incoming;
    }
  }
}

void checkLimitFlags() {
  if (limitHitJ1 || limitHitJ2 || limitHitZ) {
    const bool j1 = limitHitJ1, j2 = limitHitJ2, z = limitHitZ;
    limitHitJ1 = limitHitJ2 = limitHitZ = false;
    emergencyStop();
    Serial.print(F("ERR LIMIT_HIT osie:"));
    if (j1) Serial.print(F(" J1"));
    if (j2) Serial.print(F(" J2"));
    if (z) Serial.print(F(" Z"));
    Serial.println(F(" - wymagany ponowny HOME"));
  }
}

void setupAxis(AccelStepper& axis, uint8_t enablePin, float maxSpeed, float accel) {
  axis.setEnablePin(enablePin);
  // TB6600: ENA aktywny w stanie niskim.
  axis.setPinsInverted(false, false, true);
  axis.setMaxSpeed(maxSpeed);
  axis.setAcceleration(accel);
  axis.disableOutputs();
}

void setup() {
  Serial.begin(SERIAL_BAUD);

  pinMode(LIMIT_PIN_J1, INPUT_PULLUP);
  pinMode(LIMIT_PIN_J2, INPUT_PULLUP);
  pinMode(LIMIT_PIN_Z, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(LIMIT_PIN_J1), isrLimitJ1,
                  LIMIT_ACTIVE_STATE == LOW ? FALLING : RISING);
  attachInterrupt(digitalPinToInterrupt(LIMIT_PIN_J2), isrLimitJ2,
                  LIMIT_ACTIVE_STATE == LOW ? FALLING : RISING);
  attachInterrupt(digitalPinToInterrupt(LIMIT_PIN_Z), isrLimitZ,
                  LIMIT_ACTIVE_STATE == LOW ? FALLING : RISING);

  setupAxis(axisJ1, PIN_J1_ENABLE, J1_MAX_SPEED, J1_ACCEL);
  setupAxis(axisJ2, PIN_J2_ENABLE, J2_MAX_SPEED, J2_ACCEL);
  setupAxis(axisZ, PIN_Z_ENABLE, Z_MAX_SPEED, Z_ACCEL);
  setupAxis(axisTool, PIN_TOOL_ENABLE, TOOL_MAX_SPEED, TOOL_ACCEL);

  gripperServo.attach(GRIPPER_SERVO_PIN);
  gripperServo.write(GRIPPER_OPEN_DEG);

  enableAll();
  limitMonitoringEnabled = true;

  Serial.print(F("READY "));
  Serial.println(F(FW_VERSION));
}

void loop() {
  handleSerial();
  runAllAxes();
  checkLimitFlags();

  if (state == State::MOVING && !anyAxisMoving() && !motionDoneReported) {
    state = State::IDLE;
    motionDoneReported = true;
    Serial.println(F("DONE"));
  }
}
