# Sugerowany pinout Arduino Mega 2560

Ponizsza tabela opisuje przykladowe przypisanie pinow dla trzech osi uzywanych w wersji 1.0.

## Sterowniki TB6600

| Os | STEP / PUL | DIR | ENA |
| --- | ---: | ---: | ---: |
| Z | D2 | D5 | D8 |
| Ramie | D3 | D6 | D9 |
| Efektor | D4 | D7 | D10 |

## Krancowki optyczne

| Czujnik | Pin Arduino Mega |
| --- | ---: |
| Home Z | D22 |
| Home ramie | D23 |

## Uwagi montazowe

- Wszystkie masy (`GND`) musza byc wspolne pomiedzy Arduino i sterownikami TB6600.
- Zasilanie mocy 24 V podlaczaj bezposrednio do sterownikow TB6600.
- Arduino Mega pozostaje na osobnym zasilaczu 9 V zgodnie z zalozeniem separacji logiki od napedow.
- Zaleznie od wersji TB6600 mozna spotkac dwa popularne sposoby polaczenia linii sterujacych:
  - **common cathode** - `PUL-`, `DIR-`, `ENA-` do GND, a sygnaly z Arduino na wejscia `+`,
  - **common anode** - `PUL+`, `DIR+`, `ENA+` do +5 V, a Arduino steruje wejsciami `-`.
- Jesli logika aktywacji `ENA` lub stan czujnika jest odwrotny niz w szkicu, zmien odpowiednie stale w `src/main.ino`.

## Rezerwa na rozbudowe

W projekcie przewidziano 4 sterowniki TB6600, wiec pozostaje wolny tor pod:

- druga os ramienia ("lokiec"),
- chwytak,
- dodatkowy obrot lub os liniowa.
