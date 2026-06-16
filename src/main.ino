// ============================================================================
//  Robot SCARA v1.0 (Uproszczona) - Szkic glowny
// ----------------------------------------------------------------------------
//  Plytka:     Arduino Mega 2560 (logika 5 V)
//  Sterowniki: 4x TB6600 (mikrokrok 1/16), sygnaly PUL / DIR / ENA
//  Biblioteka: AccelStepper (Tools -> Manage Libraries -> "AccelStepper")
//
//  Osie uzywane w wersji 1.0:
//    - Z        : podnoszenie (gora / dol)
//    - ARM      : glowne ramie (przekladnia cykloidalna 20:1)
//    - EFFECTOR : obrotowy efektor koncowy (naped paskowy)
//
//  Wszystkie piny, przelozenia i predkosci znajduja sie w pliku config.h.
// ============================================================================

#include <AccelStepper.h>
#include "config.h"

// ----------------------------------------------------------------------------
//  Obiekty silnikow (tryb DRIVER: 2 piny - step + dir)
// ----------------------------------------------------------------------------
AccelStepper stepperZ(AccelStepper::DRIVER, Z_PUL_PIN, Z_DIR_PIN);
AccelStepper stepperArm(AccelStepper::DRIVER, ARM_PUL_PIN, ARM_DIR_PIN);
AccelStepper stepperEff(AccelStepper::DRIVER, EFF_PUL_PIN, EFF_DIR_PIN);

// Flaga: czy robot zostal zbazowany (homing wykonany).
bool isHomed = false;

// ----------------------------------------------------------------------------
//  Funkcje pomocnicze - wlaczanie / wylaczanie sterownikow (pin ENA)
// ----------------------------------------------------------------------------
void enableDriver(int enaPin, bool enable) {
  // enable == true  -> WLACZ sterownik (silnik trzyma moment)
  // Dla TB6600 ENA jest czesto aktywne nisko (LOW = wlaczony).
  bool level;
  if (DRIVER_ENABLE_ACTIVE_LOW) {
    level = enable ? LOW : HIGH;
  } else {
    level = enable ? HIGH : LOW;
  }
  digitalWrite(enaPin, level);
}

void enableAllDrivers(bool enable) {
  enableDriver(Z_ENA_PIN, enable);
  enableDriver(ARM_ENA_PIN, enable);
  enableDriver(EFF_ENA_PIN, enable);
}

// Czy krancowka danej osi jest aktualnie wcisnieta/przeslonieta?
bool isHomeTriggered(int homePin) {
  return digitalRead(homePin) == HOME_ACTIVE_STATE;
}

// ----------------------------------------------------------------------------
//  Konwersje jednostek (uzyteczne przy wydawaniu komend ruchu)
// ----------------------------------------------------------------------------
long mmToStepsZ(float mm)        { return (long)(mm  * Z_STEPS_PER_MM); }
long degToStepsArm(float deg)    { return (long)(deg * ARM_STEPS_PER_DEG); }
long degToStepsEff(float deg)    { return (long)(deg * EFF_STEPS_PER_DEG); }

// ============================================================================
//  SZABLONY PROCEDUR HOMINGU (do uzupelnienia / dostrojenia)
// ----------------------------------------------------------------------------
//  Zalecany przebieg dla kazdej osi:
//    1) Jesli krancowka juz aktywna -> odjedz (back-off) az przestanie byc.
//    2) Jedz powoli w kierunku krancowki az do jej zadzialania.
//    3) Zatrzymaj sie, odjedz o HOMING_BACKOFF_STEPS (dla powtarzalnosci).
//    4) Ustaw biezaca pozycje jako 0 (setCurrentPosition(0)).
// ============================================================================

// --- Homing osi Z (krancowka: gorna pozycja) ---
void homeZ() {
  // TODO: zaimplementowac bazowanie osi Z.
  // Szkielet:
  //   stepperZ.setMaxSpeed(HOMING_SPEED);
  //   stepperZ.setAcceleration(Z_ACCEL);
  //   ... najazd na Z_HOME_PIN w kierunku Z_HOMING_DIR ...
  //   stepperZ.setCurrentPosition(0);
}

// --- Homing osi ramienia (krancowka: pozycja referencyjna ramienia) ---
void homeArm() {
  // TODO: zaimplementowac bazowanie ramienia.
  // Szkielet:
  //   stepperArm.setMaxSpeed(HOMING_SPEED);
  //   stepperArm.setAcceleration(ARM_ACCEL);
  //   ... najazd na ARM_HOME_PIN w kierunku ARM_HOMING_DIR ...
  //   stepperArm.setCurrentPosition(0);
}

// --- Efektor: brak krancowki w wersji 1.0 ---
// Os efektora nie ma czujnika homingu. Po starcie przyjmujemy pozycje
// biezaca jako zero. Jesli w przyszlosci pojawi sie krancowka, dodaj homeEff().
void homeEffector() {
  stepperEff.setCurrentPosition(0);
}

// --- Pelna procedura bazowania wszystkich osi ---
void homeAll() {
  // TODO: dobrac bezpieczna kolejnosc (zwykle najpierw Z w gore, potem ramie).
  homeZ();
  homeArm();
  homeEffector();
  isHomed = true;
}

// ============================================================================
//  SETUP
// ============================================================================
void setup() {
  Serial.begin(115200);
  Serial.println(F("Robot SCARA v1.0 - inicjalizacja..."));

  // Piny ENA jako wyjscia.
  pinMode(Z_ENA_PIN, OUTPUT);
  pinMode(ARM_ENA_PIN, OUTPUT);
  pinMode(EFF_ENA_PIN, OUTPUT);

  // Piny krancowek jako wejscia (z opcjonalnym pull-up).
  pinMode(Z_HOME_PIN, HOME_USE_PULLUP ? INPUT_PULLUP : INPUT);
  pinMode(ARM_HOME_PIN, HOME_USE_PULLUP ? INPUT_PULLUP : INPUT);

  // Konfiguracja predkosci i przyspieszen (z config.h).
  stepperZ.setMaxSpeed(Z_MAX_SPEED);
  stepperZ.setAcceleration(Z_ACCEL);

  stepperArm.setMaxSpeed(ARM_MAX_SPEED);
  stepperArm.setAcceleration(ARM_ACCEL);

  stepperEff.setMaxSpeed(EFF_MAX_SPEED);
  stepperEff.setAcceleration(EFF_ACCEL);

  // Wlacz sterowniki.
  enableAllDrivers(true);

  // Wydruk wyliczonych stalych (pomocne przy kalibracji).
  Serial.print(F("ARM_STEPS_PER_DEG = ")); Serial.println(ARM_STEPS_PER_DEG);
  Serial.print(F("Z_STEPS_PER_MM    = ")); Serial.println(Z_STEPS_PER_MM);
  Serial.print(F("EFF_STEPS_PER_DEG = ")); Serial.println(EFF_STEPS_PER_DEG);

  // UWAGA: homing wywolaj swiadomie po sprawdzeniu mechaniki.
  // homeAll();

  Serial.println(F("Gotowy."));
}

// ============================================================================
//  LOOP
// ----------------------------------------------------------------------------
//  AccelStepper wymaga ciaglego wywolywania run() dla kazdego silnika,
//  aby realizowac profil predkosci (rampy przyspieszen).
// ============================================================================
void loop() {
  stepperZ.run();
  stepperArm.run();
  stepperEff.run();

  // TODO: tutaj dodaj logike komend (np. odczyt z portu szeregowego /
  //       kolejka ruchow / kinematyka). Pamietaj, by nie blokowac loop().
}
