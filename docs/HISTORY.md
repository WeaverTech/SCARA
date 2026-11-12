# Historia wrzutów

`main` długo zawierał tylko nagłówek `# SCARA`. Prawdziwa praca lądowała na gałęziach `cursor/*` i w PR-ach, często jeden na drugi, nie na `main`. Ten plik mówi, co z każdego wrzutu weszło do dzisiejszego `main`, a czego nie wolno wskrzeszać.

Kolejność jest chronologiczna względem zawartości, nie numerów PR.

## Zostało w `main`

| Wrzut | Co wniósł i gdzie to teraz jest |
| --- | --- |
| `cursor/scara-project-scaffold-4a95_GPT` (PR #3, szkic) | Szkielet, który urósł w resztę projektu: firmware z kinematyką odwrotną (`src/main/`), klient `host/`, model `sim/`, panel `webapp/`, pliki STEP i rendery (dziś `cad/v1/`). |
| `cursor/fw-version-check-18c3` (PR #5, zmergowany do gałęzi roboczej) | `JOG` / `JOGR` / `SETHOME` parsowane bez `sscanf %f` (na AVR `%f` nie działa) oraz sprawdzenie wersji firmware przy połączeniu z panelu. |
| `cursor/ping-retry-connect-18c3` (PR #6, zmergowany) | Ponowienie `PING` po resecie Mega, bo bootloader potrafi zjeść pierwszą komendę. |
| `cursor/serial-read-timeout-18c3` (PR #7, zmergowany) | Port szeregowy na Windows nie jest konfigurowany przy każdym odczycie (ginął bufor RX). |
| `cursor/fix-web-arduino-serial-0df9` (PR #4, szkic) | Handshake panelu z Arduino i czytelne błędy połączenia. Gałąź zbierała PR #5–#8, ale PR #4 celuje w stary scaffold, nie w `main`. |
| `cursor/z-gantry-v2-redesign-b578` (PR #8, zmergowany do gałęzi wyżej, nie do `main`) | Analiza sztywności v1 i parametryczna oś Z v2. Dziś `cad/v2/`. |
| Uporządkowanie na `main` | Przeniesienie całości na `main`, podział CAD na `v1/` i `v2/`, usunięcie zdublowanego renderu oraz dokumentów, które przeczyły firmware. |

Z wczesnych opisów zostało też to, co się nie zdezaktualizowało: rozdzielone zasilanie 24 V (silniki) i 9 V (Arduino), mostek masy sygnałowej, przekładnia cykloidalna 20:1 na barku, profile 2020, PETG, obudowa sterownika z miejscem na cztery TB6600. Aktualny schemat jest w [`WIRING.md`](WIRING.md).

## Nie wracać do tego

Te gałęzie startują z pustego `main` i **nie zawierają** późniejszego firmware. Ich pliki wyglądają kompletnie, ale kłócą się ze sobą i z maszyną.

| Wrzut | Dlaczego nie |
| --- | --- |
| `cursor/scara-project-bootstrap-abad` | Szkic `src/main.ino` w korzeniu `src/`. Zastąpiony przez `src/main/`. |
| `cursor/scara-project-scaffold-7917` | Robot bez łokcia, L1 = 150 mm, piny D2–D10, krańcówki D22/D23. Inna kinematyka niż obecna. |
| `cursor/scara-robot-v1-8f9e` (PR #1, zamknięty bez merge) | v1.0 bez łokcia w kodzie: `src/config.h` + `src/main.ino`, piny D2–D10, krańcówki D18/D19, przykładowe przełożenie efektora 2:1 i śruba „do zmierzenia”. |
| `cursor/setup-dev-environment-0d67` (PR #2, zamknięty bez merge) | `AGENTS.md` z informacją, że repozytorium jest puste. To już nieprawda. |
| Stary `docs/README.md` | Własna tabela pinów (krańcówki 40/41/42) i łokieć 20:1. Usunięty przy porządkowaniu, bo dało się go wziąć za schemat. |
| Duplikat renderu | `Zrzut ekranu 2026-06-09 221726 — kopia.png` był bajt w bajt taki sam jak plik bez „kopia”. Został jeden plik: `cad/v1/renders/full-machine-2026-06-09.png`. |

## Pull requesty

Wszystkie są zamknięte. Zostały numery, nie ma otwartej roboty.

| PR | Stan | Dlaczego nie jest osobną linią pracy |
| --- | --- | --- |
| [#1](https://github.com/WeaverTech/SCARA/pull/1) | zamknięty, bez merge | Szkic v1.0 bez łokcia i ze starymi pinami. |
| [#2](https://github.com/WeaverTech/SCARA/pull/2) | zamknięty, bez merge | Opis pustego `main`. |
| [#3](https://github.com/WeaverTech/SCARA/pull/3) | zmergowany | Wczesny firmware i panel. Nowszy stan jest dalej na `main`. |
| [#4](https://github.com/WeaverTech/SCARA/pull/4) | zamknięty, bez merge | Handshake jest już na `main`; PR celował w stary scaffold. |
| [#5](https://github.com/WeaverTech/SCARA/pull/5)–[#8](https://github.com/WeaverTech/SCARA/pull/8) | zmergowane | Poprawki szeregowe i oś Z v2. Commity są w historii `main`. |
| [#9](https://github.com/WeaverTech/SCARA/pull/9) | zmergowany | Uporządkowanie, które wstawiło cały projekt na `main`. |

Gałęzie `cursor/*` zostały skasowane po tym zamknięciu. Zostaje `main`. Commity odrzuconych szkiców nadal da się otworzyć z zamkniętych PR #1 i #2; nie trzeba ich przywracać jako gałęzi.
