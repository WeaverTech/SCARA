#include <AccelStepper.h>

// Pin assignment for Arduino Mega 2560 -> TB6600 drivers.
constexpr uint8_t Z_STEP_PIN = 2;
constexpr uint8_t ARM_STEP_PIN = 3;
constexpr uint8_t TOOL_STEP_PIN = 4;

constexpr uint8_t Z_DIR_PIN = 5;
constexpr uint8_t ARM_DIR_PIN = 6;
constexpr uint8_t TOOL_DIR_PIN = 7;

constexpr uint8_t Z_ENABLE_PIN = 8;
constexpr uint8_t ARM_ENABLE_PIN = 9;
constexpr uint8_t TOOL_ENABLE_PIN = 10;

constexpr uint8_t Z_HOME_PIN = 22;
constexpr uint8_t ARM_HOME_PIN = 23;

// Adjust these states to match the actual TB6600 wiring and sensor boards.
constexpr uint8_t ENABLE_ACTIVE_STATE = LOW;
constexpr uint8_t ENABLE_INACTIVE_STATE = HIGH;
constexpr uint8_t HOME_SWITCH_ACTIVE_STATE = LOW;

constexpr float MOTOR_STEPS_PER_REV = 200.0f;
constexpr float MICROSTEPS = 16.0f;

constexpr float ARM_GEAR_RATIO = 20.0f;
constexpr float ARM_STEPS_PER_DEG =
    (MOTOR_STEPS_PER_REV * MICROSTEPS * ARM_GEAR_RATIO) / 360.0f;

// TODO: Replace this placeholder after measuring the actual Z screw / belt lead.
constexpr float Z_LEAD_MM_PER_REV = 8.0f;
constexpr float Z_STEPS_PER_MM =
    (MOTOR_STEPS_PER_REV * MICROSTEPS) / Z_LEAD_MM_PER_REV;

// TODO: Replace this placeholder after calculating the real pulley ratio.
constexpr float TOOL_RATIO = 1.0f;
constexpr float TOOL_STEPS_PER_DEG =
    (MOTOR_STEPS_PER_REV * MICROSTEPS * TOOL_RATIO) / 360.0f;

constexpr float Z_MAX_SPEED = 1500.0f;
constexpr float Z_ACCELERATION = 900.0f;

constexpr float ARM_MAX_SPEED = 3200.0f;
constexpr float ARM_ACCELERATION = 1800.0f;

constexpr float TOOL_MAX_SPEED = 2400.0f;
constexpr float TOOL_ACCELERATION = 1200.0f;

AccelStepper zAxis(AccelStepper::DRIVER, Z_STEP_PIN, Z_DIR_PIN);
AccelStepper armAxis(AccelStepper::DRIVER, ARM_STEP_PIN, ARM_DIR_PIN);
AccelStepper toolAxis(AccelStepper::DRIVER, TOOL_STEP_PIN, TOOL_DIR_PIN);

void configureAxis(AccelStepper& axis, float maxSpeed, float acceleration);
void enableDrivers();
void disableDrivers();

long zMmToSteps(float distanceMm);
long armDegToSteps(float angleDeg);
long toolDegToSteps(float angleDeg);

void moveToArcPose(float zMm, float armDeg, float toolDeg);
void homeAllAxes();
void homeZAxis();
void homeArmAxis();
void zeroToolAxis();

void setup() {
  Serial.begin(115200);

  pinMode(Z_ENABLE_PIN, OUTPUT);
  pinMode(ARM_ENABLE_PIN, OUTPUT);
  pinMode(TOOL_ENABLE_PIN, OUTPUT);

  pinMode(Z_HOME_PIN, INPUT_PULLUP);
  pinMode(ARM_HOME_PIN, INPUT_PULLUP);

  enableDrivers();

  configureAxis(zAxis, Z_MAX_SPEED, Z_ACCELERATION);
  configureAxis(armAxis, ARM_MAX_SPEED, ARM_ACCELERATION);
  configureAxis(toolAxis, TOOL_MAX_SPEED, TOOL_ACCELERATION);

  zAxis.setCurrentPosition(0);
  armAxis.setCurrentPosition(0);
  toolAxis.setCurrentPosition(0);

  Serial.println(F("SCARA v1.0 controller ready."));
  Serial.println(F("Fill in homing logic before running the machine."));
}

void loop() {
  zAxis.run();
  armAxis.run();
  toolAxis.run();
}

void configureAxis(AccelStepper& axis, float maxSpeed, float acceleration) {
  axis.setMaxSpeed(maxSpeed);
  axis.setAcceleration(acceleration);
}

void enableDrivers() {
  digitalWrite(Z_ENABLE_PIN, ENABLE_ACTIVE_STATE);
  digitalWrite(ARM_ENABLE_PIN, ENABLE_ACTIVE_STATE);
  digitalWrite(TOOL_ENABLE_PIN, ENABLE_ACTIVE_STATE);
}

void disableDrivers() {
  digitalWrite(Z_ENABLE_PIN, ENABLE_INACTIVE_STATE);
  digitalWrite(ARM_ENABLE_PIN, ENABLE_INACTIVE_STATE);
  digitalWrite(TOOL_ENABLE_PIN, ENABLE_INACTIVE_STATE);
}

long zMmToSteps(float distanceMm) {
  return static_cast<long>(distanceMm * Z_STEPS_PER_MM);
}

long armDegToSteps(float angleDeg) {
  return static_cast<long>(angleDeg * ARM_STEPS_PER_DEG);
}

long toolDegToSteps(float angleDeg) {
  return static_cast<long>(angleDeg * TOOL_STEPS_PER_DEG);
}

void moveToArcPose(float zMm, float armDeg, float toolDeg) {
  zAxis.moveTo(zMmToSteps(zMm));
  armAxis.moveTo(armDegToSteps(armDeg));
  toolAxis.moveTo(toolDegToSteps(toolDeg));
}

void homeAllAxes() {
  // Suggested order:
  // 1. Raise Z to a safe reference.
  // 2. Home the main arm rotation.
  // 3. Zero the end effector rotation if needed.
  homeZAxis();
  homeArmAxis();
  zeroToolAxis();
}

void homeZAxis() {
  // TODO:
  // - move the Z axis slowly toward the optical home sensor,
  // - detect HOME_SWITCH_ACTIVE_STATE on Z_HOME_PIN,
  // - back off a few steps and approach again for better repeatability,
  // - setCurrentPosition(0) or another machine reference value.
}

void homeArmAxis() {
  // TODO:
  // - rotate the main arm toward its optical home sensor,
  // - stop when ARM_HOME_PIN reaches HOME_SWITCH_ACTIVE_STATE,
  // - back off and re-approach for precision,
  // - setCurrentPosition(0) for the arm reference.
}

void zeroToolAxis() {
  // The end effector does not yet have a sensor in this scaffold.
  toolAxis.setCurrentPosition(0);
}
