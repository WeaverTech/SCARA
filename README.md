# Robot SCARA V1

Repozytorium dla uproszczonego robota typu SCARA budowanego z profili
aluminiowych oraz elementów drukowanych w 3D z PET-G. Wersja 1.0 skupia się
na uruchomieniu podstawowej kinematyki: ruchu osi Z, jednego głównego obrotu
ramienia oraz obrotu efektora końcowego.

## Założenia mechaniczne

Robot jest uproszczoną konstrukcją SCARA bez osi "łokcia" na etapie testów.
Narzędzie porusza się po łuku o stałym promieniu, co upraszcza sterowanie i
pozwala zweryfikować mechanikę, elektronikę oraz procedury bazowania przed
rozbudową układu.

| Parametr | Wartość / opis |
| --- | --- |
| Architektura | Z + główny obrót ramienia + obrót efektora |
| Offset osi Z | 165 mm od osi prowadnic pionowych do środka osi głównej przekładni |
| Promień ramienia L1 | 150 mm od osi przekładni cykloidalnej do osi efektora |
| Os Z | Napęd paskiem lub mechanizm odzyskany z osi Z, kalibracja po pomiarze skoku |
| Główna oś obrotowa | Drukowana przekładnia cykloidalna 20:1 |
| Efektor końcowy | Oś obrotowa napędzana paskiem zębatym z silnika na ramieniu |

## Elektronika i zasilanie

| Element | Konfiguracja |
| --- | --- |
| Mikrokontroler | Arduino Mega 2560, logika 5 V |
| Sterowniki | 4x TB6600, sygnały PUL/DIR/ENA z pinów cyfrowych Arduino |
| Mikrokrok | 1/16 dla wszystkich osi |
| Silniki | NEMA 17 dla osi Z, ramienia głównego i efektora |
| Zasilanie silników | Zasilacz przemysłowy 24 V / 8.3 A / 200 W |
| Zasilanie logiki | Oddzielny zasilacz 9 V do gniazda Arduino Mega |
| Krańcówki | Optyczne czujniki szczelinowe dla osi Z i osi ramienia |

Masy zasilania logiki i sterowników muszą być połączone na potrzeby sygnałów
sterujących TB6600. Zasilanie silników pozostaje oddzielone od zasilania
Arduino, co ogranicza zakłócenia i odciąża stabilizator na płytce.

## Dane obliczeniowe dla firmware

Firmware startowy znajduje sie w `src/main.ino` i korzysta z biblioteki
AccelStepper.

| Os | Przeliczenie |
| --- | --- |
| Ramię główne | `(200 kroków * 16 mikrokroków * 20) / 360 = 177.7778 kroku/stopień` |
| Os Z | `Z_STEPS_PER_MM = (200 * 16) / przesuw_mm_na_obrot` - wymaga pomiaru mechanizmu |
| Efektor | Wymaga wpisania przełożenia paskowego po doborze zebatek |

## Struktura repozytorium

```text
.
├── cad/          # Modele 3D, eksporty STL/STEP i dokumentacja mechaniczna
├── docs/         # Schematy, notatki kalibracyjne i procedury uruchomieniowe
├── src/          # Kod Arduino
│   └── main.ino  # Szkic startowy dla Arduino Mega + TB6600
└── README.md
```

## Uruchomienie firmware

1. Zainstaluj Arduino IDE albo Arduino CLI.
2. Zainstaluj bibliotekę `AccelStepper` przez Library Manager.
3. Otwórz `src/main.ino`.
4. Sprawdź przypisanie pinów `STEP`, `DIR`, `ENA` oraz pinów krańcówek.
5. Ustaw rzeczywisty przesuw osi Z i przełożenie efektora w sekcji stałych.
6. Wgraj szkic na Arduino Mega 2560.
7. Testuj osie pojedynczo przy odłączonym narzędziu i ograniczonej prędkości.

## Najbliższe kroki

- Zmierzyć rzeczywisty przesuw osi Z na jeden obrót silnika i wpisać go do
  `Z_TRAVEL_PER_REV_MM`.
- Wyliczyć przełożenie paskowe efektora i zaktualizować
  `EFFECTOR_DRIVE_RATIO`.
- Podłączyć i przetestować optyczne krańcówki.
- Uzupełnić procedury homingu w `src/main.ino`.
- Dodać schemat połączeń TB6600, Arduino Mega, zasilaczy i czujników do
  katalogu `docs/`.
