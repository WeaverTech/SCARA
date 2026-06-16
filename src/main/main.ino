#include <AccelStepper.h>

// Arduino Mega 2560 pin map for external TB6600 drivers.
// TB6600 inputs are typically labeled PUL, DIR and ENA.
namespace Pins {
constexpr uint8_t Z_STEP = 22;
constexpr uint8_t Z_DIR = 23;
constexpr uint8_t Z_ENABLE = 24;

constexpr uint8_t ARM_STEP = 26;
constexpr uint8_t ARM_DIR = 27;
constexpr uint8_t ARM_ENABLE = 28;

constexpr uint8_t TOOL_STEP = 30;
constexpr uint8_t TOOL_DIR = 31;
constexpr uint8_t TOOL_ENABLE = 32;

constexpr uint8_t Z_HOME = 40;
constexpr uint8_t ARM_HOME = 41;
}  // namespace Pins

namespace Mechanics {
constexpr float MOTOR_STEPS_PER_REV = 200.0F;
constexpr float MICROSTEPS = 16.0F;
constexpr float ARM_GEAR_RATIO = 20.0F;

constexpr float ARM_STEPS_PER_DEGREE =
    (MOTOR_STEPS_PER_REV * MICROSTEPS * ARM_GEAR_RATIO) / 360.0F;

// TODO: Measure the real belt/screw motion and update before production use.
constexpr float Z_STEPS_PER_MM = (MOTOR_STEPS_PER_REV * MICROSTEPS) / 8.0F;

// TODO: Update after counting pulley teeth and final belt ratio.
constexpr float TOOL_STEPS_PER_DEGREE = (MOTOR_STEPS_PER_REV * MICROSTEPS) / 360.0F;
}  // namespace Mechanics

namespace Motion {
constexpr float Z_MAX_SPEED = 1200.0F;
constexpr float Z_ACCELERATION = 600.0F;

constexpr float ARM_MAX_SPEED = 900.0F;
constexpr float ARM_ACCELERATION = 450.0F;

constexpr float TOOL_MAX_SPEED = 1200.0F;
constexpr float TOOL_ACCELERATION = 600.0F;

constexpr float HOMING_SPEED = 250.0F;
constexpr long HOMING_SEARCH_TRAVEL_STEPS = -200000L;
}  // namespace Motion

AccelStepper zAxis(AccelStepper::DRIVER, Pins::Z_STEP, Pins::Z_DIR);
AccelStepper armAxis(AccelStepper::DRIVER, Pins::ARM_STEP, Pins::ARM_DIR);
AccelStepper toolAxis(AccelStepper::DRIVER, Pins::TOOL_STEP, Pins::TOOL_DIR);

String serialLine;

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
  pinMode(Pins::ARM_HOME, INPUT_PULLUP);

  setupAxis(zAxis, Pins::Z_ENABLE, Motion::Z_MAX_SPEED, Motion::Z_ACCELERATION);
  setupAxis(armAxis, Pins::ARM_ENABLE, Motion::ARM_MAX_SPEED, Motion::ARM_ACCELERATION);
  setupAxis(toolAxis, Pins::TOOL_ENABLE, Motion::TOOL_MAX_SPEED, Motion::TOOL_ACCELERATION);

  enableAllAxes();

  Serial.println(F("SCARA V1.0 controller ready."));
  Serial.println(F("Commands: STATUS, HOME Z, HOME ARM, MOVE Z <mm>, MOVE ARM <deg>, MOVE TOOL <deg>, STOP"));
}

void loop() {
  handleSerial();
  runAllAxes();
}

void enableAllAxes() {
  zAxis.enableOutputs();
  armAxis.enableOutputs();
  toolAxis.enableOutputs();
}

void disableAllAxes() {
  zAxis.disableOutputs();
  armAxis.disableOutputs();
  toolAxis.disableOutputs();
}

void runAllAxes() {
  zAxis.run();
  armAxis.run();
  toolAxis.run();
}

bool isHomeTriggered(uint8_t pin) {
  // Optical slot sensors commonly pull the signal low when blocked.
  return digitalRead(pin) == LOW;
}

void homeZAxis() {
  Serial.println(F("Homing Z axis..."));
  zAxis.setMaxSpeed(Motion::HOMING_SPEED);
  zAxis.moveTo(Motion::HOMING_SEARCH_TRAVEL_STEPS);

  while (!isHomeTriggered(Pins::Z_HOME)) {
    zAxis.run();
  }

  zAxis.stop();
  zAxis.setCurrentPosition(0);
  zAxis.setMaxSpeed(Motion::Z_MAX_SPEED);
  Serial.println(F("Z axis homed."));
}

void homeArmAxis() {
  Serial.println(F("Homing main arm axis..."));
  armAxis.setMaxSpeed(Motion::HOMING_SPEED);
  armAxis.moveTo(Motion::HOMING_SEARCH_TRAVEL_STEPS);

  while (!isHomeTriggered(Pins::ARM_HOME)) {
    armAxis.run();
  }

  armAxis.stop();
  armAxis.setCurrentPosition(0);
  armAxis.setMaxSpeed(Motion::ARM_MAX_SPEED);
  Serial.println(F("Main arm axis homed."));
}

void moveZToMillimeters(float millimeters) {
  zAxis.moveTo(lround(millimeters * Mechanics::Z_STEPS_PER_MM));
}

void moveArmToDegrees(float degrees) {
  armAxis.moveTo(lround(degrees * Mechanics::ARM_STEPS_PER_DEGREE));
}

void moveToolToDegrees(float degrees) {
  toolAxis.moveTo(lround(degrees * Mechanics::TOOL_STEPS_PER_DEGREE));
}

void stopMotion() {
  zAxis.stop();
  armAxis.stop();
  toolAxis.stop();
}

void printStatus() {
  Serial.print(F("Z steps: "));
  Serial.print(zAxis.currentPosition());
  Serial.print(F(" | Arm steps: "));
  Serial.print(armAxis.currentPosition());
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

  if (command == F("STATUS")) {
    printStatus();
  } else if (command == F("HOME Z")) {
    homeZAxis();
  } else if (command == F("HOME ARM")) {
    homeArmAxis();
  } else if (command.startsWith(F("MOVE Z "))) {
    moveZToMillimeters(command.substring(7).toFloat());
  } else if (command.startsWith(F("MOVE ARM "))) {
    moveArmToDegrees(command.substring(9).toFloat());
  } else if (command.startsWith(F("MOVE TOOL "))) {
    moveToolToDegrees(command.substring(10).toFloat());
  } else if (command == F("STOP")) {
    stopMotion();
  } else if (command == F("DISABLE")) {
    disableAllAxes();
  } else if (command == F("ENABLE")) {
    enableAllAxes();
  } else {
    Serial.print(F("Unknown command: "));
    Serial.println(command);
  }
}
