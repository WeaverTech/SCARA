# Robot SCARA v1.0 (Uproszczona konstrukcja)

Repozytorium zawiera punkt startowy dla uproszczonego robota SCARA budowanego z profili aluminiowych oraz elementow drukowanych w 3D z PET-G. Wersja 1.0 skupia sie na uruchomieniu trzech osi:

- **Z** - ruch gora/dol,
- **ramie glowne** - jeden glowny obrot wokol osi bazy,
- **efektor koncowy** - niezalezny obrot narzedzia.

Na tym etapie nie ma jeszcze drugiego czlonu ramienia ("lokcia"), dlatego narzedzie porusza sie po luku o stalym promieniu.

## Zalozenia mechaniczne

| Parametr | Wartosc | Opis |
| --- | ---: | --- |
| Offset osi Z | 165 mm | Odleglosc od osi pionowych prowadnic do srodka glownej osi obrotu |
| Promien ramienia `L1` | 150 mm | Odleglosc od osi przekladni do osi efektora |
| Os Z | naped paskiem | Ruch pionowy gora/dol |
| Os ramienia | przekladnia cykloidalna 20:1 | Autorska przekladnia drukowana w 3D |
| Efektor | naped paskiem zebatym | Silnik zamontowany na ramieniu |

## Elektronika

| Element | Konfiguracja |
| --- | --- |
| Mikrokontroler | Arduino Mega 2560 |
| Sterowniki | 4x TB6600, mikrokrok 1/16 |
| Silniki | NEMA 17 dla osi Z, ramienia i efektora |
| Zasilanie silnikow | 24 V / 8.3 A / 200 W |
| Zasilanie logiki | osobny zasilacz 9 V dla Arduino Mega |
| Homing | optyczne czujniki szczelinowe dla osi Z i ramienia |

Aktualny szkic programu obsluguje **3 aktywne osie** (Z, ramie, efektor), a czwarty sterownik pozostaje rezerwa pod przyszla rozbudowe.

## Control box

Planowana obudowa sterowania jest drukowana w 3D i oparta o strukture plastra miodu, co wspiera pasywne chlodzenie i pozwala dolozyc wentylatory z odzysku. Uklad mechaniczny obudowy zaklada:

- zasilacz 24 V w dolnej czesci,
- zintegrowana szyne DIN dla Arduino Mega nad zasilaczem,
- pionowy montaz czterech sterownikow TB6600 obok siebie.

## Dane do oprogramowania

### Glowna os obrotowa

Przy mikrokroku 1/16 oraz przelozeniu 20:1:

```text
(200 krokow silnika * 16 mikrokrokow * 20) / 360 stopni
= 177.777... kroku / stopien
```

W kodzie zostalo to zdefiniowane jako stala `ARM_STEPS_PER_DEG`.

### Os Z

Wymaga uzupelnienia po pomiarze rzeczywistego skoku sruby / napedu:

```text
(200 krokow silnika * 16 mikrokrokow) / skok_w_mm
```

W szkicu Arduino przygotowano stala `Z_LEAD_MM_PER_REV`, ktora nalezy ustawic po pomiarze.

### Efektor

Wymaga przeliczenia przelozenia na podstawie zebatek paska:

```text
(200 krokow silnika * 16 mikrokrokow * przelozenie) / 360 stopni
```

W szkicu przygotowano stala `TOOL_RATIO`.

## Struktura repozytorium

```text
.
├── cad/
│   └── README.md
├── docs/
│   ├── kinematics.md
│   └── wiring.md
├── src/
│   └── main.ino
└── README.md
```

## Co jest juz przygotowane

- profesjonalny opis projektu i architektury,
- dokumentacja podstawowej kinematyki,
- sugerowany pinout Arduino Mega -> TB6600,
- startowy szkic `src/main.ino` oparty o biblioteke `AccelStepper`,
- gotowe szablony funkcji do procedury homingu osi Z i osi ramienia.

## Uruchomienie

1. Zainstaluj biblioteke **AccelStepper** w Arduino IDE.
2. Otworz plik `src/main.ino`.
3. Zweryfikuj pinout z `docs/wiring.md`.
4. Ustaw prawidlowe wartosci:
   - `Z_LEAD_MM_PER_REV`,
   - `TOOL_RATIO`,
   - logike aktywacji czujnikow i linii `ENA`.
5. Wgraj szkic na Arduino Mega 2560.

## Najblizsze kroki

- zmierzyc skok osi Z i uzupelnic stale w kodzie,
- policzyc przelozenie efektora,
- dodac rzeczywista sekwencje homingu,
- dodac proste sterowanie przez port szeregowy lub G-code,
- rozbudowac projekt o drugi czlon ramienia w kolejnej wersji.
