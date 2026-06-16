# Schemat połączeń i zasilania

System zasilania jest **rozdzielony (izolowany)**: osobne źródło dla silników
("mięśnie") i osobne dla logiki ("mózg"). Zapobiega to zakłóceniom od silników
i przegrzewaniu stabilizatora na płytce Arduino.

## Tory zasilania

```
                ┌──────────────────────────┐
  230 V AC ───► │ Zasilacz 24 V / 8.3 A     │ (200 W, montażowy)
                │  "Mięśnie"                │
                └─────┬───────────┬─────────┘
                      │ +24V      │ GND
                      ▼           ▼
        ┌─────────────────────────────────────┐
        │  4× TB6600 (VCC / GND zasilania)     │
        │   - Z, Ramię, Efektor (+ rezerwa)    │
        └─────────────────────────────────────┘

                ┌──────────────────────────┐
  230 V AC ───► │ Zasilacz 9 V (DC jack)    │
                │  "Mózg"                   │
                └─────────────┬─────────────┘
                              ▼
                ┌──────────────────────────┐
                │ Arduino Mega 2560 (Vin)   │
                └─────────────┬─────────────┘
                              │ GND (logiki)
                              ▼
        ┌─────────────────────────────────────┐
        │  Wspólna masa sygnałowa (GND)        │
        │  Arduino GND  ⟷  TB6600 sygnały GND  │
        └─────────────────────────────────────┘
```

## Kluczowe zasady

1. **Masy mostkowane:** masa logiki Arduino musi być połączona z masą
   *sygnałową* sterowników TB6600 (wspólny punkt odniesienia PUL/DIR/ENA).
   **Nie** łącz +24 V z +5 V/+9 V.
2. **Zasilanie silników (+24 V):** prowadź grubszymi przewodami bezpośrednio do
   złącz zasilania każdego TB6600. Zadbaj o solidne, wspólne szyny +24 V i GND.
3. **Zasilanie logiki (9 V):** podłączone do gniazda DC Arduino Mega.
   9 V jest komfortowe dla wbudowanego stabilizatora (unikamy przegrzewania).
4. **Kolejność włączania:** najpierw logika (Arduino), potem zasilanie 24 V
   silników. Wyłączanie w odwrotnej kolejności.

## Krańcówki (czujniki optyczne)

- Zasilanie czujników: zwykle 5 V z Arduino (sprawdź wymagania konkretnego
  modułu z drukarki).
- Wyjście sygnału → piny D18 (Z) i D19 (Ramię).
- Polaryzację aktywnego stanu ustaw w `config.h` (`HOME_ACTIVE_STATE`),
  a pull-up w `HOME_USE_PULLUP`.

## Obudowa (Control Box)

- **Dół:** zasilacz 24 V.
- **Środek:** szyna DIN z Arduino Mega.
- **Góra/bok:** 4× TB6600 montowane pionowo, obok siebie.
- Struktura "plastra miodu" zapewnia pasywne chłodzenie + miejsce na
  wentylatory z odzysku.
