#ifndef CONFIG_H
#define CONFIG_H

// ============================================================================
//  Robot SCARA v1.0 - Plik konfiguracyjny
// ----------------------------------------------------------------------------
//  Centralne miejsce na piny, przelozenia, predkosci i przyspieszenia.
//  Edytuj wartosci oznaczone "DO POMIARU" po zmierzeniu mechaniki.
// ============================================================================

// ----------------------------------------------------------------------------
//  1. PINY STEROWNIKOW TB6600 (Arduino Mega 2560)
//     Kazdy sterownik: PUL (krok), DIR (kierunek), ENA (wlaczenie).
//     Masy (GND) sterownikow sa mostkowane ze wspolna masa Arduino.
// ----------------------------------------------------------------------------

// Os Z (gora / dol)
#define Z_PUL_PIN   2
#define Z_DIR_PIN   3
#define Z_ENA_PIN   4

// Ramie glowne (przekladnia cykloidalna 20:1)
#define ARM_PUL_PIN 5
#define ARM_DIR_PIN 6
#define ARM_ENA_PIN 7

// Efektor koncowy (naped paskowy)
#define EFF_PUL_PIN 8
#define EFF_DIR_PIN 9
#define EFF_ENA_PIN 10

// ----------------------------------------------------------------------------
//  2. PINY KRANCOWEK (optyczne czujniki szczelinowe z Elegoo Saturn)
//     Czujniki optyczne sygnalizuja przeslonecie szczeliny.
//     Polaryzacje (HIGH/LOW przy aktywacji) ustaw w *_HOME_ACTIVE_STATE.
// ----------------------------------------------------------------------------

#define Z_HOME_PIN   18   // krancowka osi Z (gorna pozycja)
#define ARM_HOME_PIN 19   // krancowka osi obrotowej ramienia

// Stan logiczny pinu w momencie zadzialania czujnika.
// Dla wiekszosci czujnikow optycznych z drukarek aktywny stan to LOW.
#define HOME_ACTIVE_STATE LOW

// Czy wlaczyc wewnetrzne podciagniecie (pull-up) na pinach krancowek.
#define HOME_USE_PULLUP true

// ----------------------------------------------------------------------------
//  3. STALE MECHANICZNE / KROKI NA JEDNOSTKE
//     Mikrokrok 1/16 dla wszystkich osi, silniki 200 krokow/obrot.
// ----------------------------------------------------------------------------

#define MOTOR_FULL_STEPS 200.0f   // pelne kroki na obrot (NEMA 17 = 1.8 deg)
#define MICROSTEPPING    16.0f    // mikrokrok 1/16

// --- Ramie glowne: przekladnia cykloidalna 20:1 ---
// (200 * 16 * 20) / 360 = 177.777... krokow / 1 stopien
#define ARM_GEAR_RATIO   20.0f
#define ARM_STEPS_PER_DEG \
    ((MOTOR_FULL_STEPS * MICROSTEPPING * ARM_GEAR_RATIO) / 360.0f)

// --- Os Z: sruba trapezowa ---
// [200 * 16] / skok_gwintu_mm = krokow / 1 mm
// DO POMIARU: zmierz skok (lead) sruby z Elegoo Saturn i wpisz ponizej.
#define Z_LEAD_MM        8.0f     // <-- DO POMIARU (przyklad: 8 mm/obrot)
#define Z_STEPS_PER_MM \
    ((MOTOR_FULL_STEPS * MICROSTEPPING) / Z_LEAD_MM)

// --- Efektor: naped paskowy ---
// [200 * 16 * przelozenie] / 360 = krokow / 1 stopien
// DO POMIARU: przelozenie = zeby_kola_napedzanego / zeby_kola_silnika.
#define EFFECTOR_GEAR_RATIO 2.0f  // <-- DO POMIARU (przyklad: 2:1)
#define EFF_STEPS_PER_DEG \
    ((MOTOR_FULL_STEPS * MICROSTEPPING * EFFECTOR_GEAR_RATIO) / 360.0f)

// ----------------------------------------------------------------------------
//  4. GEOMETRIA (dla przyszlej kinematyki odwrotnej)
// ----------------------------------------------------------------------------

#define Z_AXIS_OFFSET_MM 165.0f   // offset osi Z
#define ARM_LENGTH_L1_MM 150.0f   // promien ramienia (L1)

// ----------------------------------------------------------------------------
//  5. PREDKOSCI I PRZYSPIESZENIA (w krokach/s oraz krokach/s^2)
//     Wartosci startowe - dostroj eksperymentalnie po montazu.
// ----------------------------------------------------------------------------

// Os Z
#define Z_MAX_SPEED   2000.0f
#define Z_ACCEL       1000.0f

// Ramie glowne (duze przelozenie -> mozna szybciej w krokach)
#define ARM_MAX_SPEED 4000.0f
#define ARM_ACCEL     2000.0f

// Efektor
#define EFF_MAX_SPEED 3000.0f
#define EFF_ACCEL     1500.0f

// ----------------------------------------------------------------------------
//  6. PARAMETRY HOMINGU
// ----------------------------------------------------------------------------

// Predkosc dojazdu do krancowki (kroki/s) - powolna, bezpieczna.
#define HOMING_SPEED        800.0f

// Kierunek najazdu na krancowke (+1 lub -1) dla kazdej osi.
#define Z_HOMING_DIR        (+1)   // Z bazuje "do gory"
#define ARM_HOMING_DIR      (-1)

// Maksymalna liczba krokow przy szukaniu krancowki (zabezpieczenie).
#define HOMING_MAX_STEPS    100000L

// Odjazd od krancowki po jej wykryciu (back-off), w krokach.
#define HOMING_BACKOFF_STEPS 200L

// Czy sterowniki sa aktywne przy stanie LOW na pinie ENA.
// Dla TB6600 czesto ENA jest aktywne nisko (LOW = wlaczony).
#define DRIVER_ENABLE_ACTIVE_LOW true

#endif  // CONFIG_H
