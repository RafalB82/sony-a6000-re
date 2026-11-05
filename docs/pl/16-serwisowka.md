# 16 — Serwisówka: mapa arkuszy, dostęp debugowania i okablowanie migawki

Service manual Level 3 to jedyne źródło warstwy elektrycznej, której firmware nie pokaże:
na której kuli SoC siedzi port debugowania, które elementy nie są montowane i jak faktycznie
napędzane są dwa elektromagnesy kurtyn oraz silnik naciągu. Ta strona jest mapą roboczą, nie
kopią dokumentu.

> **Źródło.** *SERVICE MANUAL LEVEL 3, ILCE-6000/6000L/6000Y*, rev 1.1, 54 strony, utworzony
> 2014-02-17, SHA-256 `4ab1630bffdba4aff01fa5934b8a1f3fe4bb54f4fefd6a7c19192836bda31aa5`
> (archiwum iFixit; identyczna kopia na photo-parts.com.ua). **Nie jest redystrybuowany** —
> numery stron poniżej to mapa. Każda tabela pinów została odczytana z PDF-a przez
> `pdftotext -bbox` (współrzędne słów), nie OCR-em ze zrzutu ekranu.

## 1. Jak to czytać

- Arkusze schematów mają identyfikator `6-N` w tabelce tytułowej; **strona PDF = N + 12**
  (arkusz `6-11` to strona 23). Rozdział 4 (strony 7–12) to schematy blokowe.
- Tabelka tytułowa (prawy dolny róg) podaje płytkę, numer arkusza i funkcję, np.
  `SY-1028 BOARD (8/23) / POWER CONTROL, MECHANISM CONTROL / 6-11`.
- **`pdftotext -layout` po cichu gubi całe bloki** na gęstych arkuszach — blok JTAG/eFuse ze
  strony 26 i net `XRESET_CR` ze strony 24 w takim zrzucie nie istnieją. Trzeba
  `pdftotext -bbox` (współrzędne), `pdftocairo -svg` albo `pdftoppm -r 600`, i parować piny
  z netami po wierszach i kolumnach.
- `XX` w opisie oznacza **nie montowane** w tym wariancie płytki (`XX MARK: NO MOUNT`). To
  stwierdzenie o wariancie, nie o konkretnym egzemplarzu.

## 2. Mapa arkuszy

| Strony | Arkusz | Płytka / funkcja |
|---|---|---|
| 1–2 | — | okładka, safety check-out |
| 3–6 | — | lista części (BOM), w tym zespoły płytkowe |
| 7–12 | 4-1 … 4-4 | **schematy blokowe**: całość (s. 7), płytki, rozdział wideo/audio i zasilania |
| 13 | 6-1 | rozdzielacz rozdziału 6 |
| 14 | 6-2 | `IS-095` — płytka matrycy CMOS |
| 15 | 6-3 | połączenie IS↔SY (pomijając druk) |
| 16–38 | 6-4 … 6-26 | **płytka główna `SY-1028`, 23 arkusze** (szczegóły niżej) |
| 39–41 | 6-27 … 6-29 | flex `ST-1018` — napęd lampy, terminal baterii, złącza |
| 42 | 6-30 | `FP-2045` / `MIS-2000` — stopka multi-interface |
| 43–46 | 6-31 … 6-34 | **płytka migawki `CN-1027`, 4 arkusze**: złącze, slot kart, **napęd migawki**, DC/DC |
| 47 | 6-35 | `LC-1018` — LCD |
| 48 | 6-36 | `RL-1024` — klawisze |
| 49–54 | 6-37 … 6-41 | widoki montażowe / druk |

`SY-1028` szczegółowo: 1 złącza · 2–4 DC/DC · 5 złącza · 6 przełącznik B+ · 7 zasilanie USB ·
**8 sterowanie zasilaniem i mechanizmem (Darwin)** · 9–12 CPU, DSP kamery, przetwarzanie AV,
sterowanie obiektywem, HDMI (IC6000 jest tu rozrysowany na 7 blokach, `(1/7)`…`(7/7)`) ·
13 przetwarzanie sygnału · 14 interfejs obiektywu · **15 napęd silnika naciągu, napęd anti-dust** ·
16 WLAN · 17 NFC · 18 napęd LED, czujnik przechyłu · 19 złącza · 20 procesor audio · 21 nie
używany · 22 HDMI, terminal Multi · 23 złącza.

Cztery strony, które liczą się przy pracy z firmware: **23** (Darwin), **26** (blok
debugowania IC6000), **37** (terminal Multi), **38** (CN4906), **45** (napęd migawki),
**30** (silnik naciągu).

## 3. Dostęp debugowania

### 3.1 IC6000 (BIONZ X) — arkusz 6-14, strona 26, blok `(4/7)`

| Sygnał | Bola | Połączenie |
|---|---|---|
| TDI | G25 | podciągnięte do `D_3.15V_MSS` |
| TCK | H25 | podciągnięte do `D_3.15V_MSS` |
| TMS | F26 | podciągnięte do `D_3.15V_MSS` |
| TDO | F25 | brak wyprowadzenia serwisowego |
| RTCK | G26 | brak wyprowadzenia serwisowego |
| NTRST | H26 | net `XRESET_CR` — ten sam co wejście resetu układu (`XRESET`, bola K6, przez `R6000` = XX) |
| FUSE_EN | T12 | podciągnięte do `D_3.15V` (normalne: układ czyta fusy przy starcie) |
| FUSE_CLK | R12 | brak sieci na tym arkuszu |
| **SWCLK** | **W25** | wolne, dochodzi do pola serwisowego przez `R4911` (XX) |
| **SWDIO** | **W26** | wolne, dochodzi przez `R4912` (XX) |

Odczyt: klasyczny JTAG jest bezużyteczny (trzy z pięciu linii na stałe w stanie wysokim),
a osobnego resetu TAP nie ma — `NTRST` to reset całego SoC. Zostaje tylko SWD i tylko przez
dwa pady.

### 3.2 CN4906 — pole serwisowe, 18 pinów, arkusz 6-26, strona 38

| Pin | Net | Pin | Net |
|---|---|---|---|
| 1 | REG_GND | 10 | RTCK (bez sieci) |
| 2 | BOOT_MODE_1 | 11 | **TCK(SWCLK)** — `SWCLK` BIONZ + `TCK_DWN` Darwina |
| 3 | EVER_3.15V | 12 | **TMS(SWDIO)** — `SWDIO` BIONZ + `TMS_DWN` Darwina |
| 4 | UART_RXD_MSS (UART0 BIONZ) | 13 | TDI (`TDI_DWN` Darwina) |
| 5 | UART_TXD_MSS | 14 | NTRST (`TRST_DWN` Darwina) |
| 6 | UART_RXD_DWN (Darwin) | 15 | DEBUG_MODE — `VIO_FLD` + `XDWN_RESET` Darwina |
| 7 | UART_TXD_DWN | 16–18 | REG_GND |
| 8 | NSRST (`MD0_DWN` Darwina) | | |
| 9 | TDO (`TDO_DWN` Darwina) | | |

Sam `CN4906` jest oznaczony **XX** (tylko pole lutownicze), a sygnały Darwina dochodzą do
niego przez nieobsadzone wysepki `CL701`–`CL707` na arkuszu 6-11. To pole nie jest więc
portem BIONZ: to **wspólny nagłówek debugowania BIONZ + Darwin**, a piny 11/12 są
**wspólnym węzłem** padów SWD BIONZ i `TCK`/`TMS` Darwina — dlatego sondowanie SWD może
zakłócać MCU zasilania.

### 3.3 CN4001 — terminal Multi, 15 + 4 piny, arkusz 6-25, strona 37

1 `USB_VBUS` · 2 `USB_D-` · 3 `USB_D+` · 4 `USB_ID` · 5 `GND` · 6 `D_3.1V/LANC_DC`
(`R4001` XX) · 7 `XRESET_REQ` (`R4008` XX) · 8 `UART_TX/LANC_SIG` (`CM4008` montowany) ·
9 `UART_RX/BOOT_IN` (`R4002`/`R4003` XX, zmostkowane do pinu 10 przez `CM4002` montowany) ·
10 `AD_JACK_IN` (`CM4003` montowany) · 11 `ROUT/XAELOCK` · 12 `LOUT/XSHUT` (`R4004` XX) ·
13 `VIDEO` · 14 `AV_GND` · 15 `XPWR_ON` · 16–19 ekran/`REG_GND`.

Czyli linia szeregowa BootROM dociera do terminala Multi wyłącznie jako **deklaracja
w schemacie**: oba rezystory szeregowe nie są montowane.

## 4. BIONZ ↔ Darwin: łącza, którymi idzie protokół migawki

Nety na arkuszu 6-11 (`IC5700`, `MB9AF004BGL-G-103-ERE1`):

| Net | Kierunek | Rola |
|---|---|---|
| `MSS_SCK_DWN`, `MSS_SI_DWN`, `MSS_SO_DWN` | BIONZ → Darwin | **zegar/dane SPI** — to fizyczny transport 22-bajtowego pakietu `0x0c`, w którym jedzie `pkt[0x0e]` |
| `DWN_CSREQ_MSS`, `DWN_CSDIR_MSS` | oba | chip-select / uzgadnianie kierunku |
| `CA_1ST_CURTAIN_START` | BIONZ → Darwin | polecenie „zaczynaj sekwencję" |
| `CA_RELEASE_LOCK_MSS` | BIONZ → Darwin | zwolnienie blokady |
| `CA_XRESET_OUT_MSS` | BIONZ → Darwin | reset Darwina |
| `DWN_USB_SEL`, `USB_D+_DWN`, `USB_D-_DWN` | oba | własne USB Darwina (interfejs `054c:0994`) |
| `UART_RXD_DWN` / `UART_TXD_DWN` | oba | konsola Darwina, tylko na CN4906 6/7 |

Wniosek dla prac nad migawką elektroniczną: bajt trybu nie dochodzi do Darwina z powodu tego,
co dzieje się na **SPI**, a nie na UART. Analizator logiczny dla tego pytania podpina się pod
`MSS_SCK_DWN`/`MSS_SI_DWN`, czyli na płycie SY-1028, a nie na polu serwisowym.

## 5. Okablowanie migawki

### 5.1 Droga

```
Darwin IC5700 (SY-1028, arkusz 6-11)
   1ST_CURTAIN_MG / 2ND_CURTAIN_MG / SHUTTER_PI_ON ─┐
   SHUTTER_PI (ADC) / SHUTTER_ID ◄──────────────────┤
                                                    ▼
                        CN4900 (61-pinowy flex) na SY-1028, arkusz 6-26
                        piny 9 / 11 / 10 · 8 / 4 · 7 · 12–15 (SHUTTER_5.5V)
                                                    ▼
                        płytka CN-1027, arkusz 6-33 „SHUTTER DRIVE"
                        Q6830 / Q6831 (RN1102MFV) · Q6832 (MTM765200LBF, XX)
                        D6830 / D6831 (diody Zenera) · R6830/R6831 100k · R6832 4,7k · R6834 100
                                                    ▼
                        CN302 (10 pinów) → zespół migawki
```

### 5.2 CN302 do zespołu migawki (arkusz 6-33)

| Pin | Net | Znaczenie |
|---|---|---|
| 1 | 1C | elektromagnes pierwszej kurtyny |
| 2, 3 | COMMON | `SHUTTER_5.5V` |
| 4 | 2C | elektromagnes drugiej kurtyny |
| 5 | PI-A | anoda LED fotoprzerwacza |
| 6 | PI-K | katoda LED |
| 7 | PI-E | emiter fototranzystora |
| 8 | PI-C | kolektor fototranzystora |
| 9 | ID | `SHUTTER_ID` — rezystor identyfikacyjny czytany przez Darwina |
| 10 | GND | masa |

Migawka to więc **dwa elektromagnesy 5,5 V** plus 4-przewodowy optyczny czujnik pozycji,
wszystko napędzane z małej płytki (`CN-1027`) odrębnej od płyty głównej.

### 5.3 Silnik naciągu (arkusz 6-18, strona 30)

`SC_M_1` / `SC_M_2` z Darwina wchodzą do `IC6800 = TC7SH86FU`, bramki **XOR**. Jej wyjście
`OUT_Y` steruje `Q6800` (`RN1102MFV`) i `Q6801` (`US6M2GTR`, XX) do `CN1800` (16 pinów)
`CM+` / `CM-`, czyli silnikiem naciągu w `MB CHARGE UNIT`, z `CM_TEMP` wracającym na
`CHARGE_MOTOR_TEMP`.

Warto to powiedzieć precyzyjnie, bo poprawia jeden odczyt pracy nad firmware: przy bramce XOR
`P40 = P41 = 1` daje `OUT_Y = 0`, czyli **brak napędu**, a nie rozkazany hamulec. Czy silnik
jest zwierany (hamowanie dynamiczne), zależy od stopnia drivera, nie od bramki; schemat nie
mówi, żeby awaryjna operacja 5 przykładała hamulec.

## 6. Czego manual nie daje

- **Stan eFuse blokującego debug.** `FUSE_EN` podciągnięty w górę to normalne „czytaj moje
  fusy"; to, co jest w fusie zapisane, nie jest w żadnym pliku.
- **Pełnej tablicy pinów CXD90014.** Porty multipleksowane są nazwane funkcją
  (tylko `GPIO_S_0..16`, `GPIO_SB_0..6`); kuli np. dla portu 14 w dokumencie nie ma.
- **Osobnego układu NAND.** `IC6000` to pakiet ze stosem pamięci (strona 27 pokazuje
  połączenia POP/LPDDR2); nie ma dyskretnej NAND z modelem i pinoutem — dlatego zewnętrzny
  zrzut NAND oznacza podnoszenie SoC.
- **Obsady w egzemplarzu.** `XX` opisuje wariant. Czy dany aparat ma `R4911`, czy `CN4906`,
  rozstrzyga pomiar ciągłości.
- **Semantyki firmware.** Nic o `ShutMode`, `r5`, `pkt[0x0e]`.

## 7. Do czego się przydaje

1. **Wybór punktu pomiarowego.** Prąd silnika naciągu na `CN1800 CM+/CM-`; elektromagnesy
   kurtyn na `CN302` piny 1/4; fotoprzerwacz na pinach 5–8; `SHUTTER_5.5V` na pinie 3.
2. **Odpowiedź „czy mechanizm się rusza?"** bez zgadywania z dźwięku: magnesy są sterowane
   dwoma tranzystorami cyfrowymi, więc sondowanie `1ST/2ND_CURTAIN_MG` pokazuje zamiar,
   a `CN302` — obciążenie.
3. **Wyjaśnienie mapy software'owej**: `P4D`/`P4E` (pisarze pod `0x234`/`0x238` w Darwinie)
   odpowiadają dwóm elektromagnesom kurtyn; `P40`/`P41` — silnikowi naciągu przez XOR; kanał
   ADC czytany z `SHUTTER_PI` to pozycja mechanizmu, którą firmware nazywa `ShutPIAdValue`.
4. **Naprawa i BOM**: `IC5700 MB9AF004BGL-G-103-ERE1`, `IC6200 CXD90027GF`,
   `IC6000 MHZ4G8G01A`, `IC6800 TC7SH86FU`, `Q6800/Q6830/Q6831 RN1102MFV`,
   `Q6801 US6M2GTR`, `Q6832 MTM765200LBF`.

## 8. Korekty naszych notatek

- [01-sprzet.md](01-sprzet.md) mówi, że manual ma „5 arkuszy" — ma **54 strony**, a istotna
  część to 23 arkusze `SY-1028` plus 4 `CN-1027`.
- Darwin to `MB9AF004BGL-G-103-ERE1` (kod zamówieniowy), a jego arkusz to 6-11, nie strony
  zasilania, gdzie lokuje go nasza notatka.
- Nasze zdanie „migawka to Darwin + cewki" można teraz uściślić: dwa magnesy 5,5 V na osobnej
  płytce, 4-przewodowy fotoprzerwacz i silnik naciągu za bramką XOR.

Źródła: tekst stron wyciągnięty przez `pdftotext -bbox` z PDF-a zweryfikowanego hashem;
skonfrontowane z pinoutami opublikowanymi w `nicolvus/a6000-fw-decomp` (E26-R29 dla
CN4001/CN4906, E26-R42 dla mapy kul) — zgodność na każdym porównanym pinie.
