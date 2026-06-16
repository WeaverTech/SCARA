#include <AccelStepper.h>

/*
  Robot SCARA V1 - firmware startowy

  Sterownik: Arduino Mega 2560
  Drivery:   TB6600 w trybie STEP/DIR/ENA
  Biblioteka: AccelStepper

  Przed testami sprawdz:
  - ustawienie mikrokroku 1/16 na kazdym TB6600,
  - wspolna mase Arduino i wejsc sygnalowych TB6600,
  - kierunki osi po pierwszym ruchu testowym,
  - rzeczywisty przesuw osi Z na obrot silnika i przelozenie paska efektora.
*/

namespace Pins {
  // TB6600: PUL/STEP, DIR i ENA dla kazdej uzywanej osi.
  constexpr uint8_t Z_STEP = 2;
  constexpr uint8_t Z_DIR = 5;
  constexpr uint8_t Z_ENABLE = 8;

  constexpr uint8_t ARM_STEP = 3;
  constexpr uint8_t ARM_DIR = 6;
  constexpr uint8_t ARM_ENABLE = 9;

  constexpr uint8_t EFFECTOR_STEP = 4;
  constexpr uint8_t EFFECTOR_DIR = 7;
  constexpr uint8_t EFFECTOR_ENABLE = 10;

  // Optyczne krancowki szczelinowe. INPUT_PULLUP zaklada aktywne zwarcie do GND.
  constexpr uint8_t Z_HOME_SENSOR = 22;
  constexpr uint8_t ARM_HOME_SENSOR = 23;
}

namespace Motion {
  constexpr float MOTOR_FULL_STEPS_PER_REV = 200.0F;
  constexpr float MICROSTEPS = 16.0F;

  constexpr float ARM_GEAR_RATIO = 20.0F;
  constexpr float ARM_STEPS_PER_DEGREE =
      (MOTOR_FULL_STEPS_PER_REV * MICROSTEPS * ARM_GEAR_RATIO) / 360.0F;

  // TODO: zmierz rzeczywisty przesuw osi Z na jeden obrot silnika.
  // Dziala zarowno dla sruby, jak i napedu paskowego po przeliczeniu zebatek.
  constexpr float Z_TRAVEL_PER_REV_MM = 8.0F;
  constexpr float Z_STEPS_PER_MM =
      (MOTOR_FULL_STEPS_PER_REV * MICROSTEPS) / Z_TRAVEL_PER_REV_MM;

  // TODO: wpisz rzeczywiste przelozenie paska efektora: obroty silnika / obrot osi.
  constexpr float EFFECTOR_DRIVE_RATIO = 1.0F;
  constexpr float EFFECTOR_STEPS_PER_DEGREE =
      (MOTOR_FULL_STEPS_PER_REV * MICROSTEPS * EFFECTOR_DRIVE_RATIO) / 360.0F;

  constexpr float Z_MAX_SPEED_MM_S = 20.0F;
  constexpr float Z_ACCEL_MM_S2 = 80.0F;

  constexpr float ARM_MAX_SPEED_DEG_S = 30.0F;
  constexpr float ARM_ACCEL_DEG_S2 = 90.0F;

  constexpr float EFFECTOR_MAX_SPEED_DEG_S = 90.0F;
  constexpr float EFFECTOR_ACCEL_DEG_S2 = 180.0F;

  // Typowe moduly TB6600 maja wejscie ENA aktywne stanem niskim.
  constexpr bool ENABLE_ACTIVE_LOW = true;
}

AccelStepper zAxis(AccelStepper::DRIVER, Pins::Z_STEP, Pins::Z_DIR);
AccelStepper armAxis(AccelStepper::DRIVER, Pins::ARM_STEP, Pins::ARM_DIR);
AccelStepper effectorAxis(AccelStepper::DRIVER, Pins::EFFECTOR_STEP,
                          Pins::EFFECTOR_DIR);

void configureStepper(AccelStepper &stepper,
                      uint8_t enablePin,
                      float maxSpeed,
                      float acceleration,
                      bool invertDirection = false) {
  stepper.setEnablePin(enablePin);
  stepper.setPinsInverted(invertDirection, false, Motion::ENABLE_ACTIVE_LOW);
  stepper.setMaxSpeed(maxSpeed);
  stepper.setAcceleration(acceleration);
  stepper.enableOutputs();
}

long zMillimetersToSteps(float millimeters) {
  return lround(millimeters * Motion::Z_STEPS_PER_MM);
}

long armDegreesToSteps(float degrees) {
  return lround(degrees * Motion::ARM_STEPS_PER_DEGREE);
}

long effectorDegreesToSteps(float degrees) {
  return lround(degrees * Motion::EFFECTOR_STEPS_PER_DEGREE);
}

bool isZHomeTriggered() {
  return digitalRead(Pins::Z_HOME_SENSOR) == LOW;
}

bool isArmHomeTriggered() {
  return digitalRead(Pins::ARM_HOME_SENSOR) == LOW;
}

void homeZAxis() {
  // TODO:
  // 1. Ustaw mala predkosc homingu w gore osi Z.
  // 2. Jedz do aktywacji optycznej krancowki Z.
  // 3. Cofnij os o kilka mm.
  // 4. Powtorz dojazd wolniej.
  // 5. Ustaw pozycje osi: zAxis.setCurrentPosition(0).
}

void homeArmAxis() {
  // TODO:
  // 1. Ustaw bezpieczna predkosc obrotu ramienia.
  // 2. Obracaj do aktywacji optycznej krancowki ramienia.
  // 3. Cofnij ramie od czujnika.
  // 4. Powtorz dojazd wolniej.
  // 5. Ustaw pozycje bazowa: armAxis.setCurrentPosition(0).
}

void homeEffectorAxis() {
  // TODO:
  // Efektor nie ma jeszcze zdefiniowanej krancowki. Dodaj czujnik albo
  // procedure recznego zerowania przed wlaczeniem ruchow automatycznych.
}

void homeAllAxes() {
  homeZAxis();
  homeArmAxis();
  homeEffectorAxis();
}

void printStatus() {
  Serial.println(F("SCARA V1 status"));
  Serial.print(F("Z steps/mm: "));
  Serial.println(Motion::Z_STEPS_PER_MM, 4);
  Serial.print(F("Arm steps/deg: "));
  Serial.println(Motion::ARM_STEPS_PER_DEGREE, 4);
  Serial.print(F("Effector steps/deg: "));
  Serial.println(Motion::EFFECTOR_STEPS_PER_DEGREE, 4);

  Serial.print(F("Z position [steps]: "));
  Serial.println(zAxis.currentPosition());
  Serial.print(F("Arm position [steps]: "));
  Serial.println(armAxis.currentPosition());
  Serial.print(F("Effector position [steps]: "));
  Serial.println(effectorAxis.currentPosition());

  Serial.print(F("Z home sensor: "));
  Serial.println(isZHomeTriggered() ? F("TRIGGERED") : F("open"));
  Serial.print(F("Arm home sensor: "));
  Serial.println(isArmHomeTriggered() ? F("TRIGGERED") : F("open"));
}

void handleSerialCommand(const String &command) {
  if (command == F("status")) {
    printStatus();
  } else if (command == F("enable")) {
    zAxis.enableOutputs();
    armAxis.enableOutputs();
    effectorAxis.enableOutputs();
    Serial.println(F("Drivers enabled"));
  } else if (command == F("disable")) {
    zAxis.disableOutputs();
    armAxis.disableOutputs();
    effectorAxis.disableOutputs();
    Serial.println(F("Drivers disabled"));
  } else if (command == F("home")) {
    Serial.println(F("Homing templates are not implemented yet"));
    homeAllAxes();
  } else if (command.length() > 0) {
    Serial.println(F("Unknown command. Available: status, enable, disable, home"));
  }
}

void readSerial() {
  static String command;

  while (Serial.available() > 0) {
    const char incoming = static_cast<char>(Serial.read());

    if (incoming == '\n' || incoming == '\r') {
      command.trim();
      handleSerialCommand(command);
      command = "";
    } else {
      command += incoming;
    }
  }
}

void setup() {
  Serial.begin(115200);

  pinMode(Pins::Z_HOME_SENSOR, INPUT_PULLUP);
  pinMode(Pins::ARM_HOME_SENSOR, INPUT_PULLUP);

  configureStepper(zAxis,
                   Pins::Z_ENABLE,
                   Motion::Z_MAX_SPEED_MM_S * Motion::Z_STEPS_PER_MM,
                   Motion::Z_ACCEL_MM_S2 * Motion::Z_STEPS_PER_MM);
  configureStepper(armAxis,
                   Pins::ARM_ENABLE,
                   Motion::ARM_MAX_SPEED_DEG_S * Motion::ARM_STEPS_PER_DEGREE,
                   Motion::ARM_ACCEL_DEG_S2 * Motion::ARM_STEPS_PER_DEGREE);
  configureStepper(effectorAxis,
                   Pins::EFFECTOR_ENABLE,
                   Motion::EFFECTOR_MAX_SPEED_DEG_S *
                       Motion::EFFECTOR_STEPS_PER_DEGREE,
                   Motion::EFFECTOR_ACCEL_DEG_S2 *
                       Motion::EFFECTOR_STEPS_PER_DEGREE);

  Serial.println(F("SCARA V1 firmware ready"));
  Serial.println(F("Commands: status, enable, disable, home"));
}

void loop() {
  readSerial();

  zAxis.run();
  armAxis.run();
  effectorAxis.run();
}
