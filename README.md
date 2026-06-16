# 🤖 Robot SCARA (Wersja 1.0 – Uproszczona)

Projekt ramienia robotycznego typu **SCARA**, zbudowanego z profili aluminiowych
oraz elementów drukowanych w 3D (PET-G). Wersja 1.0 jest celowo uproszczoną
konstrukcją z **jedną główną osią obrotową ramienia** (z pominięciem "łokcia"
na etapie testów), **podnoszoną osią Z** oraz **obrotowym efektorem końcowym**.

> Narzędzie porusza się po stałym promieniu (łuku), co znacznie upraszcza
> matematykę sterowania na tym etapie rozwoju projektu.

---

## 📐 1. Kinematyka i Mechanika

**Architektura:** Uproszczona SCARA
(ruch w osi Z + jeden główny obrót ramienia + obrót efektora).

| Parametr | Wartość | Opis |
| --- | --- | --- |
| **Offset osi Z** | `165 mm` | Odległość od osi prętów/prowadnic pionowych do środka osi obrotu głównej przekładni. |
| **Promień ramienia (L1)** | `150 mm` | Odległość w linii prostej od osi obrotu przekładni cykloidalnej do osi efektora końcowego. |

### Osie

- **Oś Z (Góra/Dół):** napęd paskowy / śruba (do potwierdzenia po pomiarze skoku).
- **Główna oś obrotowa (Baza/Ramię):** autorska, drukowana w 3D **przekładnia
  cykloidalna** o matematycznym przełożeniu **20:1**.
- **Efektor końcowy:** oś obrotowa napędzana **paskiem zębatym**
  (silnik umieszczony na ramieniu).

---

## ⚡ 2. Elektronika i Zasilanie

| Komponent | Model / Wartość |
| --- | --- |
| **Mikrokontroler ("Mózg")** | Arduino Mega 2560 (logika 5 V) |
| **Sterowniki silników** | 4× TB6600 (zewnętrzne, przemysłowe) |
| **Mikrokrok** | 1/16 dla wszystkich osi |
| **Silnik osi Z** | NEMA 17 |
| **Silnik ramienia głównego** | NEMA 17 |
| **Silnik efektora** | NEMA 17 |

Sterowniki TB6600 podłączone są bezpośrednio do pinów cyfrowych Arduino Mega
(sygnały: `PUL`, `DIR`, `ENA`) ze **wspólnymi (mostkowanymi) masami GND**.

### System zasilania (rozdzielony / izolowany)

- **Zasilanie "Mięśni" (silników):** przemysłowy zasilacz montażowy
  **24 V / 8.3 A (200 W)**, podłączony bezpośrednio do złącz zasilania TB6600.
- **Zasilanie "Mózgu" (logiki):** osobny zasilacz **9 V** podłączony do gniazda
  zasilania Arduino Mega. Zapewnia izolację galwaniczną od zakłóceń silników
  i zapobiega przegrzewaniu stabilizatora na płytce Arduino.

### Krańcówki (Homing)

Optyczne **czujniki szczelinowe** (odzyskane z drukarki żywicznej Elegoo Saturn),
planowane dla:

- osi Z (górna pozycja),
- osi obrotowej ramienia.

---

## 🧮 3. Dane obliczeniowe dla kodu (biblioteka AccelStepper)

Wartości do zdefiniowania w oprogramowaniu przy mikrokroku **1/16**:

### Główne ramię (przekładnia cykloidalna 20:1)

```
(200 kroków silnika × 16 mikrokroków × 20 przełożenie) / 360° = 177.77 kroków / 1°
```

### Oś Z (śruba trapezowa)

```
[200 kroków × 16 mikrokroków] / skok gwintu w mm = kroki / 1 mm
```

> ⚠️ Skok śruby z Elegoo Saturn należy zmierzyć i wpisać do stałej `Z_LEAD_MM`
> w kodzie.

### Efektor (pasek zębaty)

```
[200 kroków × 16 mikrokroków × przełożenie zębatek] / 360° = kroki / 1°
```

> ⚠️ Przełożenie zębatek paska należy obliczyć (liczba zębów koła napędzanego /
> liczba zębów koła silnika) i wpisać do stałej `EFFECTOR_GEAR_RATIO` w kodzie.

Wszystkie powyższe stałe są zebrane i opisane w pliku
[`src/config.h`](src/config.h).

---

## 📦 4. Obudowa (Control Box)

Zaprojektowana i drukowana w 3D obudowa o strukturze **plastra miodu**
(pasywne chłodzenie + miejsce na wentylatory z odzysku).

- Na dole obudowy: zasilacz 24 V.
- Nad nim: zintegrowana **szyna DIN** utrzymująca Arduino Mega.
- Cztery sterowniki TB6600 zamontowane pionowo (obok siebie) dla optymalizacji
  przestrzeni.

---

## 🗂️ Struktura repozytorium

```
.
├── README.md            # Ten plik
├── src/                 # Kod Arduino (C++)
│   ├── main.ino         # Główny szkic (AccelStepper)
│   └── config.h         # Stałe: piny, przełożenia, prędkości
├── docs/                # Dokumentacja, schematy, obliczenia
│   ├── pinout.md        # Mapa pinów Arduino Mega → TB6600
│   ├── wiring.md        # Schemat połączeń i zasilania
│   └── calculations.md  # Wyprowadzenie stałych kroków/jednostkę
└── cad/                 # Modele 3D (STL / STEP) i pliki do druku
    └── README.md
```

---

## 🚀 Pierwsze kroki

1. Zainstaluj [Arduino IDE](https://www.arduino.cc/en/software).
2. Zainstaluj bibliotekę **AccelStepper**
   (`Tools → Manage Libraries… → "AccelStepper"`).
3. Otwórz `src/main.ino`.
4. Uzupełnij pomiary w `src/config.h` (skok śruby Z, przełożenie efektora).
5. Wybierz płytkę **Arduino Mega 2560** i odpowiedni port.
6. Wgraj szkic.

> ⚠️ **Bezpieczeństwo:** Przed pierwszym uruchomieniem upewnij się, że osie mają
> swobodę ruchu, a procedura homingu jest przetestowana "na sucho"
> (z odłączonym mechanizmem) — patrz puste szablony `home*()` w `main.ino`.

---

## 🛣️ Mapa rozwoju (Roadmap)

- [x] Wersja 1.0 – uproszczona SCARA (Z + 1 obrót ramienia + efektor).
- [ ] Implementacja i kalibracja procedur homingu.
- [ ] Pomiar i uzupełnienie stałych (skok Z, przełożenie efektora).
- [ ] Dodanie drugiego segmentu ramienia ("łokieć") – pełna kinematyka SCARA.
- [ ] Odwrotna kinematyka (przeliczanie X/Y → kąty).
- [ ] Interfejs komend (np. przez port szeregowy / G-code).

---

## 📄 Licencja

Projekt open-source. Szczegóły licencji do uzupełnienia przez autora.
