#ifndef SCARA_CONFIG_H
#define SCARA_CONFIG_H

// ============================================================================
//  SCARA - konfiguracja sprzetowa i geometryczna (Arduino Mega 2560).
//  Wartosci geometryczne zmierzone w CAD - NIE zmieniac bez ponownego pomiaru.
// ============================================================================

// --- GEOMETRIA RAMION SCARA ---
#define ARM_L1_MM 139.928f       // Dlugosc ramienia J1 (Bark -> Lokiec)
#define ARM_L2_MM 140.000f       // Dlugosc ramienia J2 (Lokiec -> Efektor)
#define Z_AXIS_OFFSET_MM 165.0f  // Odleglosc kolumny Z od osi Barku
#define MAX_REACH_MM 279.928f    // Maksymalny zasieg w plaszczyznie XY (L1 + L2)
#define MIN_REACH_MM 0.072f      // Strefa martwa |L1 - L2|
#define Z_COL_EXCLUSION_R 45.0f  // Promien strefy wykluczenia wokol kolumny Z

// --- PRZELICZNIKI KROKOW (TB6600 1/16, NEMA 17 200 kr/obr) ---
#define STEPS_PER_DEG_J1 177.7778f // Przekladnia cykloidalna 20:1 -> (200*16*20)/360
#define STEPS_PER_DEG_J2 124.4444f // Przekladnia cykloidalna 14:1 -> (200*16*14)/360
#define STEPS_PER_MM_Z   400.0f    // Przelicznik dla sruby napedowej osi Z

// Efektor (TOOL) - pasek GT2; przelozenie do weryfikacji na maszynie.
#define TOOL_BELT_RATIO 1.0f
#define STEPS_PER_DEG_TOOL ((200.0f * 16.0f * TOOL_BELT_RATIO) / 360.0f)

// --- PINY KRANCOWEK (HOMING) ---
#define LIMIT_PIN_J1 2   // Opto/Hall krancowka osi 1 (przerwanie zewnetrzne)
#define LIMIT_PIN_J2 3   // Opto/Hall krancowka osi 2 (przerwanie zewnetrzne)
#define LIMIT_PIN_Z  18  // Krancowka osi Z (przerwanie zewnetrzne)

// Stan aktywny krancowek: opto szczelinowe zwykle LOW przy przeslonieciu.
#define LIMIT_ACTIVE_STATE LOW

// --- PINY STEROWNIKOW TB6600 (PUL / DIR / ENA) ---
#define PIN_Z_STEP 22
#define PIN_Z_DIR 23
#define PIN_Z_ENABLE 24

#define PIN_J1_STEP 26
#define PIN_J1_DIR 27
#define PIN_J1_ENABLE 28

#define PIN_J2_STEP 30
#define PIN_J2_DIR 31
#define PIN_J2_ENABLE 32

#define PIN_TOOL_STEP 34
#define PIN_TOOL_DIR 35
#define PIN_TOOL_ENABLE 36

// --- LIMITY PROGRAMOWE OSI (po homingu) ---
#define J1_MIN_DEG -125.0f
#define J1_MAX_DEG 125.0f
#define J2_MIN_DEG -145.0f
#define J2_MAX_DEG 145.0f
#define Z_MIN_MM 0.0f
#define Z_MAX_MM 150.0f
#define TOOL_MIN_DEG -180.0f
#define TOOL_MAX_DEG 180.0f

// --- HOMING ---
// Kierunek najazdu na krancowke (+1 / -1, w krokach silnika).
#define HOMING_DIR_J1 -1
#define HOMING_DIR_J2 -1
#define HOMING_DIR_Z  -1
// Pozycja osi w chwili zadzialania krancowki (ustawiana po homingu).
#define J1_HOME_POS_DEG (J1_MIN_DEG)
#define J2_HOME_POS_DEG (J2_MIN_DEG)
#define Z_HOME_POS_MM   (Z_MIN_MM)
// Predkosci homingu [kroki/s] i odjazd od krancowki [kroki].
#define HOMING_SEEK_SPEED 800.0f
#define HOMING_LATCH_SPEED 150.0f
#define HOMING_BACKOFF_STEPS 800L
#define HOMING_MAX_TRAVEL_STEPS 200000L

// --- DYNAMIKA RUCHU (kroki/s, kroki/s^2) ---
#define J1_MAX_SPEED 4000.0f
#define J1_ACCEL 2000.0f
#define J2_MAX_SPEED 4000.0f
#define J2_ACCEL 2000.0f
#define Z_MAX_SPEED 3000.0f
#define Z_ACCEL 1500.0f
#define TOOL_MAX_SPEED 1200.0f
#define TOOL_ACCEL 600.0f

// --- GRIPPER (serwo modelarskie SG90, sygnal PWM) ---
#define GRIPPER_SERVO_PIN 44
#define GRIPPER_OPEN_DEG 20    // kat serwa: gripper otwarty
#define GRIPPER_CLOSED_DEG 110 // kat serwa: gripper zamkniety

// --- PREDKOSC GLOBALNA ---
#define SPEED_PERCENT_MIN 10
#define SPEED_PERCENT_MAX 100
#define SPEED_PERCENT_DEFAULT 100

// --- KOMUNIKACJA ---
#define SERIAL_BAUD 115200
#define FW_VERSION "SCARA-FW 2.1"

// Prototyp bez drugiej przekladni cykloidalnej: ustaw 0, aby pominac J2.
#define ELBOW_PRESENT 1

#endif  // SCARA_CONFIG_H
