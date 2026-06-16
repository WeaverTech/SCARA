#include <AccelStepper.h>
#include <math.h>

// ============================================================================
//  SCARA robot - full target configuration (4 axes).
// ----------------------------------------------------------------------------
//  Kinematic chain:
//    Z        - vertical lift, GT2 belt drive (NEMA 17)
//    SHOULDER - main arm rotation, cycloidal drive 20:1 (NEMA 17)
//    ELBOW    - middle joint rotation, cycloidal drive 20:1 (NEMA 17)
//    TOOL     - end effector rotation, GT2 belt drive (NEMA 17)
//
//  All four axes use external TB6600 drivers (PUL/DIR/ENA) at 1/16 microstep.
//
//  NOTE (physical prototype): the ELBOW joint is modeled and supported here as
//  the final design, but the second cycloidal gearbox may not be built yet.
//  For bench testing without the elbow gearbox set ELBOW_PRESENT = false:
//  the controller will then skip enabling/homing/moving that axis.
// ============================================================================

// Arduino Mega 2560 pin map for external TB6600 drivers.
namespace Pins {
constexpr uint8_t Z_STEP = 22;
constexpr uint8_t Z_DIR = 23;
constexpr uint8_t Z_ENABLE = 24;

constexpr uint8_t SHOULDER_STEP = 26;
constexpr uint8_t SHOULDER_DIR = 27;
constexpr uint8_t SHOULDER_ENABLE = 28;

constexpr uint8_t ELBOW_STEP = 30;
constexpr uint8_t ELBOW_DIR = 31;
constexpr uint8_t ELBOW_ENABLE = 32;

constexpr uint8_t TOOL_STEP = 34;
constexpr uint8_t TOOL_DIR = 35;
constexpr uint8_t TOOL_ENABLE = 36;

// Optical slot endstops (homing). The TOOL axis has no endstop.
constexpr uint8_t Z_HOME = 40;
constexpr uint8_t SHOULDER_HOME = 41;
constexpr uint8_t ELBOW_HOME = 42;
}  // namespace Pins

// Set to false to run the prototype without the second (elbow) cycloidal drive.
// Keep true for the full, target machine.
constexpr bool ELBOW_PRESENT = true;

namespace Mechanics {
constexpr float MOTOR_STEPS_PER_REV = 200.0F;
constexpr float MICROSTEPS = 16.0F;
constexpr float STEPS_PER_REV = MOTOR_STEPS_PER_REV * MICROSTEPS;  // 3200

// --- Rotary joints: cycloidal drive 20:1 ---
// (200 * 16 * 20) / 360 = 177.7778 steps per output degree.
constexpr float SHOULDER_GEAR_RATIO = 20.0F;
constexpr float ELBOW_GEAR_RATIO = 20.0F;

constexpr float SHOULDER_STEPS_PER_DEGREE =
    (STEPS_PER_REV * SHOULDER_GEAR_RATIO) / 360.0F;
constexpr float ELBOW_STEPS_PER_DEGREE =
    (STEPS_PER_REV * ELBOW_GEAR_RATIO) / 360.0F;

// --- Z axis: GT2 belt drive ---
// Travel per motor revolution = pulley teeth * belt pitch (GT2 = 2 mm).
// steps/mm = STEPS_PER_REV / (Z_PULLEY_TEETH * Z_BELT_PITCH_MM).
// TODO: confirm the Z pulley tooth count from the CAD/BOM.
constexpr float Z_BELT_PITCH_MM = 2.0F;   // GT2
constexpr float Z_PULLEY_TEETH = 20.0F;   // TODO: verify (20T assumed)
constexpr float Z_STEPS_PER_MM =
    STEPS_PER_REV / (Z_PULLEY_TEETH * Z_BELT_PITCH_MM);

// --- Tool (effector): GT2 belt drive with reduction ---
// ratio = driven pulley teeth / motor pulley teeth.
// steps/deg = (STEPS_PER_REV * ratio) / 360.
// TODO: count pulley teeth and update the ratio.
constexpr float TOOL_BELT_RATIO = 1.0F;   // TODO: verify
constexpr float TOOL_STEPS_PER_DEGREE =
    (STEPS_PER_REV * TOOL_BELT_RATIO) / 360.0F;

// --- Geometry (link lengths, for future inverse kinematics) ---
// L1 = shoulder axis -> elbow axis, L2 = elbow axis -> tool axis.
// The brief gives 150 mm from the main rotary axis to the effector for the
// single-link simplification; with the elbow present the two links must be
// measured separately from the model.
// TODO: measure ARM1_LENGTH_MM and ARM2_LENGTH_MM from SCARA.step.
constexpr float Z_AXIS_OFFSET_MM = 165.0F;
constexpr float ARM1_LENGTH_MM = 150.0F;  // TODO: measure shoulder->elbow
constexpr float ARM2_LENGTH_MM = 150.0F;  // TODO: measure elbow->tool
}  // namespace Mechanics

namespace Motion {
constexpr float Z_MAX_SPEED = 1200.0F;
constexpr float Z_ACCELERATION = 600.0F;

constexpr float SHOULDER_MAX_SPEED = 900.0F;
constexpr float SHOULDER_ACCELERATION = 450.0F;

constexpr float ELBOW_MAX_SPEED = 900.0F;
constexpr float ELBOW_ACCELERATION = 450.0F;

constexpr float TOOL_MAX_SPEED = 1200.0F;
constexpr float TOOL_ACCELERATION = 600.0F;

constexpr float HOMING_SPEED = 250.0F;
constexpr long HOMING_SEARCH_TRAVEL_STEPS = -200000L;
}  // namespace Motion

AccelStepper zAxis(AccelStepper::DRIVER, Pins::Z_STEP, Pins::Z_DIR);
AccelStepper shoulderAxis(AccelStepper::DRIVER, Pins::SHOULDER_STEP, Pins::SHOULDER_DIR);
AccelStepper elbowAxis(AccelStepper::DRIVER, Pins::ELBOW_STEP, Pins::ELBOW_DIR);
AccelStepper toolAxis(AccelStepper::DRIVER, Pins::TOOL_STEP, Pins::TOOL_DIR);

String serialLine;

void setupAxis(AccelStepper& axis, uint8_t enablePin, float maxSpeed, float acceleration);
void enableAllAxes();
void disableAllAxes();
void runAllAxes();
bool isHomeTriggered(uint8_t pin);
void homeZAxis();
void homeShoulderAxis();
void homeElbowAxis();
void moveZToMillimeters(float millimeters);
void moveShoulderToDegrees(float degrees);
void moveElbowToDegrees(float degrees);
void moveToolToDegrees(float degrees);
void stopMotion();
void printStatus();
void handleSerial();
void processCommand(String command);

void setupAxis(AccelStepper& axis, uint8_t enablePin, float maxSpeed, float acceleration) {
  axis.setEnablePin(enablePin);
  axis.setPinsInverted(false, false, true);
  axis.setMaxSpeed(maxSpeed);
  axis.setAcceleration(acceleration);
  axis.disableOutputs();
}

void setup() {
  Serial.begin(115200);

  pinMode(Pins::Z_HOME, INPUT_PULLUP);
  pinMode(Pins::SHOULDER_HOME, INPUT_PULLUP);
  pinMode(Pins::ELBOW_HOME, INPUT_PULLUP);

  setupAxis(zAxis, Pins::Z_ENABLE, Motion::Z_MAX_SPEED, Motion::Z_ACCELERATION);
  setupAxis(shoulderAxis, Pins::SHOULDER_ENABLE, Motion::SHOULDER_MAX_SPEED, Motion::SHOULDER_ACCELERATION);
  setupAxis(elbowAxis, Pins::ELBOW_ENABLE, Motion::ELBOW_MAX_SPEED, Motion::ELBOW_ACCELERATION);
  setupAxis(toolAxis, Pins::TOOL_ENABLE, Motion::TOOL_MAX_SPEED, Motion::TOOL_ACCELERATION);

  enableAllAxes();

  Serial.println(F("SCARA controller ready (4 axes: Z, SHOULDER, ELBOW, TOOL)."));
  if (!ELBOW_PRESENT) {
    Serial.println(F("ELBOW disabled in firmware (ELBOW_PRESENT = false)."));
  }
  Serial.println(F("Commands: STATUS, HOME Z|SHOULDER|ELBOW, MOVE Z <mm>, "
                   "MOVE SHOULDER|ELBOW|TOOL <deg>, STOP, ENABLE, DISABLE"));
}

void loop() {
  handleSerial();
  runAllAxes();
}

void enableAllAxes() {
  zAxis.enableOutputs();
  shoulderAxis.enableOutputs();
  if (ELBOW_PRESENT) {
    elbowAxis.enableOutputs();
  }
  toolAxis.enableOutputs();
}

void disableAllAxes() {
  zAxis.disableOutputs();
  shoulderAxis.disableOutputs();
  elbowAxis.disableOutputs();
  toolAxis.disableOutputs();
}

void runAllAxes() {
  zAxis.run();
  shoulderAxis.run();
  if (ELBOW_PRESENT) {
    elbowAxis.run();
  }
  toolAxis.run();
}

bool isHomeTriggered(uint8_t pin) {
  // Optical slot sensors commonly pull the signal low when blocked.
  return digitalRead(pin) == LOW;
}

// Generic homing helper: jog toward the endstop, zero the position, restore speed.
void homeAxis(AccelStepper& axis, uint8_t homePin, float runSpeed,
              const __FlashStringHelper* name) {
  Serial.print(F("Homing "));
  Serial.print(name);
  Serial.println(F(" axis..."));

  axis.setMaxSpeed(Motion::HOMING_SPEED);
  axis.moveTo(Motion::HOMING_SEARCH_TRAVEL_STEPS);

  while (!isHomeTriggered(homePin) && axis.distanceToGo() != 0) {
    axis.run();
  }

  axis.stop();
  axis.setCurrentPosition(0);
  axis.setMaxSpeed(runSpeed);

  if (isHomeTriggered(homePin)) {
    Serial.print(name);
    Serial.println(F(" axis homed."));
  } else {
    Serial.print(name);
    Serial.println(F(" homing stopped: sensor not reached."));
  }
}

void homeZAxis() {
  homeAxis(zAxis, Pins::Z_HOME, Motion::Z_MAX_SPEED, F("Z"));
}

void homeShoulderAxis() {
  homeAxis(shoulderAxis, Pins::SHOULDER_HOME, Motion::SHOULDER_MAX_SPEED, F("shoulder"));
}

void homeElbowAxis() {
  if (!ELBOW_PRESENT) {
    Serial.println(F("ELBOW disabled (ELBOW_PRESENT = false), homing skipped."));
    return;
  }
  homeAxis(elbowAxis, Pins::ELBOW_HOME, Motion::ELBOW_MAX_SPEED, F("elbow"));
}

void moveZToMillimeters(float millimeters) {
  zAxis.moveTo(lround(millimeters * Mechanics::Z_STEPS_PER_MM));
}

void moveShoulderToDegrees(float degrees) {
  shoulderAxis.moveTo(lround(degrees * Mechanics::SHOULDER_STEPS_PER_DEGREE));
}

void moveElbowToDegrees(float degrees) {
  if (!ELBOW_PRESENT) {
    Serial.println(F("ELBOW disabled (ELBOW_PRESENT = false), move ignored."));
    return;
  }
  elbowAxis.moveTo(lround(degrees * Mechanics::ELBOW_STEPS_PER_DEGREE));
}

void moveToolToDegrees(float degrees) {
  toolAxis.moveTo(lround(degrees * Mechanics::TOOL_STEPS_PER_DEGREE));
}

void stopMotion() {
  zAxis.stop();
  shoulderAxis.stop();
  elbowAxis.stop();
  toolAxis.stop();
}

void printStatus() {
  Serial.print(F("Z steps: "));
  Serial.print(zAxis.currentPosition());
  Serial.print(F(" | Shoulder steps: "));
  Serial.print(shoulderAxis.currentPosition());
  Serial.print(F(" | Elbow steps: "));
  Serial.print(elbowAxis.currentPosition());
  Serial.print(F(" | Tool steps: "));
  Serial.println(toolAxis.currentPosition());
}

void handleSerial() {
  while (Serial.available() > 0) {
    const char incoming = Serial.read();

    if (incoming == '\n' || incoming == '\r') {
      if (serialLine.length() > 0) {
        processCommand(serialLine);
        serialLine = "";
      }
      continue;
    }

    serialLine += incoming;
  }
}

void processCommand(String command) {
  command.trim();
  command.toUpperCase();

  if (command == "STATUS") {
    printStatus();
  } else if (command == "HOME Z") {
    homeZAxis();
  } else if (command == "HOME SHOULDER") {
    homeShoulderAxis();
  } else if (command == "HOME ELBOW") {
    homeElbowAxis();
  } else if (command.startsWith("MOVE Z ")) {
    moveZToMillimeters(command.substring(7).toFloat());
  } else if (command.startsWith("MOVE SHOULDER ")) {
    moveShoulderToDegrees(command.substring(14).toFloat());
  } else if (command.startsWith("MOVE ELBOW ")) {
    moveElbowToDegrees(command.substring(11).toFloat());
  } else if (command.startsWith("MOVE TOOL ")) {
    moveToolToDegrees(command.substring(10).toFloat());
  } else if (command == "STOP") {
    stopMotion();
  } else if (command == "DISABLE") {
    disableAllAxes();
  } else if (command == "ENABLE") {
    enableAllAxes();
  } else {
    Serial.print(F("Unknown command: "));
    Serial.println(command);
  }
}
