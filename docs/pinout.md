# Mapa pinów — Arduino Mega 2560 → TB6600

Wszystkie sygnały są w logice 5 V. Masy (GND) sterowników TB6600 są
**mostkowane** ze wspólną masą Arduino (wspólny punkt odniesienia sygnałów).

## Sterowniki silników (PUL / DIR / ENA)

| Oś | Silnik | PUL (krok) | DIR (kierunek) | ENA (enable) |
| --- | --- | --- | --- | --- |
| **Z** (góra/dół) | NEMA 17 | D2 | D3 | D4 |
| **Ramię** (cykloidalna 20:1) | NEMA 17 | D5 | D6 | D7 |
| **Efektor** (pasek) | NEMA 17 | D8 | D9 | D10 |
| *(rezerwa: łokieć v2.0)* | — | — | — | — |

> Czwarty sterownik TB6600 jest fizycznie zamontowany w obudowie (rezerwa pod
> przyszły "łokieć"), ale nie jest używany w kodzie v1.0.

## Krańcówki (optyczne czujniki szczelinowe)

| Oś | Funkcja | Pin |
| --- | --- | --- |
| **Z** | Górna pozycja (home) | D18 |
| **Ramię** | Pozycja referencyjna | D19 |

Piny D18/D19 na Mega obsługują przerwania sprzętowe (`INT.5`/`INT.4`), więc w
przyszłości można je wykorzystać do natychmiastowego zatrzymania.

## Uwagi do podłączenia TB6600

- Wejścia TB6600 są optoizolowane. Typowe podłączenie dla logiki 5 V:
  połącz wspólne anody (`PUL+`, `DIR+`, `ENA+`) do **+5 V**, a sygnały Arduino
  podaj na katody (`PUL-`, `DIR-`, `ENA-`) — **lub** odwrotnie (wspólna masa),
  zależnie od przyjętej konwencji. Trzymaj się jednej, spójnej dla wszystkich
  sterowników.
- Mikrokrok ustaw przełącznikami DIP na **1/16** dla każdego sterownika.
- Prąd (DIP) ustaw zgodnie ze specyfikacją użytych NEMA 17.

> Numery pinów odpowiadają definicjom w [`src/config.h`](../src/config.h).
> Zmiana pinów wymaga edycji wyłącznie tego pliku.
