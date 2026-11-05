# 15 — Co „cicha migawka" faktycznie daje: ekspozycja wiersz po wierszu

2-bajtowy patch Darwina z [13](13-patch-darwina.md) zatrzymuje mechanizm, ale nie ujednolica
ekspozycji. Bez tylnej kurtyny każdy wiersz zbiera światło aż do odczytu, więc dół kadru
dostaje go więcej niż góra. Zmierzono to — dwukrotnie, dwiema niezależnymi metodami — a potem
poprawiono w RAM.

> **Źródło i status.** Z [`nicolvus/a6000-fw-decomp`](https://github.com/nicolvus/a6000-fw-decomp):
> E25-10 (dopasowanie po wierszach na 19 plikach ARW), E25-17 (matryca czasów, długie czasy),
> testy T044/T046/T047/T050, wiki strona 6. Etykiety ich autorstwa zachowane.
> **Nie sprawdzone przez nas.**

## 1. Pomiar

Aparat na 3.23, ISO 100, RAW 6024×4024, tryb M, 10 czasów × 2. Każda klatka pocięta na
32 pasma po ≈126 wierszy i dopasowana per pasmo:

```
linear_b(T) = s_b · (T + τ_b)
```

`s_b` to jasność sceny (nieznana per pasmo — dzięki temu scena wypada z równania), `T` to
ustawiony czas, a `τ_b` to ekspozycja, której czas **nie** kontroluje.

| Wynik | Wartość |
|---|---|
| Dopasowanie addytywne `T + τ` per pasmo | R² ≥ 0,988 we wszystkich 32 pasmach; błąd maks. 17 % (górne pasma, słaby sygnał), 7 % w pozostałych |
| τ, górne pasmo | **7,3 ms** (raz zmierzone 8,1 ms) |
| τ, dolne pasmo | **66,6 ms** |
| Rampa τ z wierszem | **liniowa, ≈15,2 µs na wiersz** (1,91 ms na pasmo, ≈59 ms od góry do dołu) |
| Model alternatywny „czas efektywny = max(T, podłoga)" | reszta 6,9× większa — **odrzucony** |

Czyli ekspozycja wiersza *i*:

```
E_i = T + 7 ms + 15,2 µs · i          odczyt ≈ 61 ms (15,2 µs × 4024 wiersze; ≈64 ms przy 4243 liniach)
```

Przy szybkich czasach dlatego kadr prawie nie ciemnieje wraz z czasem: między 1/4000 a 1/500
dominuje stała, a dół dostaje 3,7× więcej światła niż góra (0,095 → 0,350 względem 1/8).

**To nie usterka patcha.** T025 (3.22, przed B1a, JPEG) pokazywał już tę samą płaską podłogę
między 1/4000 a 1/250 i wzrost od 1/125. B1a tylko zatrzymuje mechanizm; gradient to wygląd
odczytu przewijanego, gdy nie ma kurtyny, która go utnie.

## 2. Poprawka, zmierzona w RAM

T046 wymusił dwa pola w RAM BIONZ (`ShutMode` pod `0x836d6fb6`, `r5` pod `0x836d7000`) i użył
trzech niepatchowanych referencji do kalibracji sceny. Ekspozycja = 1000·RAW/scena, przy 1/250:

| `r5` | Średnia ekspozycja | Po ósemkach |
|---|---|---|
| bez wymuszania | 64,9 ms | 65,0 … 65,0 |
| 0 | ≈0 (czarny kadr) | — |
| 1000 | 49,1 ms | 49,2 … 49,2 |
| 2000 | 33,8 ms | 33,9 … 33,8 |
| 3000 | 18,5 ms | 18,7 … 18,5 |
| 3500 | 10,9 ms | 11,1 … 11,0 |
| 4000 | 3,3 ms | 3,4 … 3,4 |
| 4100 | 1,8 ms | 1,9 … 1,8 |
| 4200 | 0,3 ms | 0,3 … 0,3 |
| 4300 | 64,9 ms | brak efektu |

Trzy wnioski, wszystkie zmierzone:

1. **`ShutMode 0` eksponuje każdy wiersz tyle samo** (±0,2 ms po ósemkach): to reset per
   wiersz, a nie reset globalny z następującym odczytem.
2. **`r5` zadaje ekspozycję w liniach: `E = (4219 − r5) × 15,2 µs`.** Zmierzony nachylenie
   (−15,2 µs na jednostkę) to te same 15,2 µs/wiersz, które niezależnie wyszły w §1 — to
   najmocniejszy dowód, że `r5` jest odległością między resetem a odczytem, a nie dowolnym
   rejestrem.
3. Przy 1/30 te same wartości `r5` dają te same ekspozycje co przy 1/250: **przy `ShutMode 0`
   ustawiony czas nie bierze udziału.**

T047 przewidział potem `r5` z docelowego czasu (4219 − T/15,2 µs) i sprawdził:
4203 → 0,24 ms, 4153 → 0,99 ms, 3956 → 4,03 ms, 3122 → 16,75 ms. Liniowość trzyma się w 3 %;
skala absolutna ma ±20 % (≈±25 % względem jednej referencji), co jest problemem kalibracji,
nie prawa.

## 3. Co to znaczy w praktyce

| Zastosowanie | Sam 3.23 | Z warstwą 2 (RAM) |
|---|---|---|
| 1/4000 – 1/500 | gradient do 3,7× góra-dół | równo, 0,25–4 ms |
| 1/250 – 1/60 | nadal widoczny | równo, 4–16,7 ms |
| 1/30 i wolniej | gradient mały względem T | równo do 1/30; **od 1/15 aparat wraca do normalnego trybu** |
| 1/8000 | — | tylko emulowane |
| Ruchomy obiekt | skos (odczyt ≈61 ms) | skos taki sam |
| BULB / >1/8 | niedostępne | niezaimplementowane |

Czyli „cicha migawka działa" jest prawdą warunkową: statyczny temat, umiarkowane czasy albo
patch RAM z podłączonym PC. Efekt przewijania jest nieusuwalny — 61 ms odczytu to trzy-cztery
razy wolniej niż kurtyna mechaniczna.

## 4. Warstwa 2 tak, jak jest używana

- To **wyłącznie patch RAM**: `ShutMode` i `r5` są zapisywane przez telnet (OpenMemories
  Tweak → telnetd na porcie 23) przed każdym zdjęciem lub serią i wycofywane po. Nic nie
  dotyka NVRAM, `nflasha3` ani flasha; restart czyści.
- **Watchdog w aparacie** przywraca bajty po 25 s, jeśli PC przestanie odpowiadać.
- T050: 12 zdjęć plus seria 4, między 1/4000 a 1/30, za każdym razem poprawne wycofanie.
- **Wersja po stronie aparatu padła z powodów procesowych, nie logiki:** w T049 aplikacja
  poprawnie patchowała i wycofywała na 6 zdjęciach, ale `RandomAccessFile` nie adresuje
  `/dev/mem` powyżej 2 GiB, a `Runtime.exec("dd")` z procesu ~100 MB przy ~8 MB wolnego
  zawiesił `fork` **między dwoma zapisami**, zostawiając wymuszony `ShutMode 0`. Ich wniosek:
  nigdy nie wołać `Runtime.exec` z aplikacji w trakcie zdjęcia; gadać z lokalnym telnetd
  i wykonywać oba zapisy w jednym poleceniu.

## 5. Długie czasy to osobny problem

Sufit ~65 ms należy do **ręcznej ścieżki `r5`**, nie do firmware: natywny producent
`0x4383fa40` już planuje 1/15 s … 30 s, zwracając `shd = 1` (podłoga), `svd = N−1` dodatkowych
pełnych klatek i rozszerzony VTS dla klatki z resztą (1 s → `svd 14`, 30 s → `svd 472`). BULB
jest czasowany po stronie hosta w plastrach jednej klatki (`0x438c74b0`,
`bulbFrameCount = cap+0x72c`). Brakuje więc długiej ekspozycji bez kurtyny, która kończy się
poprawnie — arytmetyka jest. W projekcie r5 to nadal niezaimplementowane.

## 6. Ograniczenia dowodu

- Jedna scena, jedno kadrowanie, ISO 100, tryb M, 1/4000–1/8; RAW bez korekcji winietowania
  i spadku obiektywu (założenie: stałe, pochłaniane przez `s_b`).
- Brak pomiaru na ruchomym obiekcie: skos jest wnioskiem z czasu odczytu, nie z obrazów
  szybkich przedmiotów.
- Skala absolutna ±20–25 %; *proporcje* między czasami do ~3 %.
- Lampa, wideo i Live View z aktywnym patchem nigdy nie były mierzone.

## 7. Dlaczego to ważne dla nas

To zamienia „cicha migawka" z twierdzenia w specyfikację: **brak tylnej kurtyny, 7 ms stałego
opóźnienia, 15,2 µs na wiersz, odczyt ≈61 ms**, równo tylko wtedy, gdy BIONZ dostanie reset
per wiersz. Każde porównanie z aparatem z prawdziwą migawką elektroniczną powinno zaczynać się
od tych czterech liczb, a każdy eksperyment oczekujący równej klatki z samego patcha Darwina
zmierzy gradient 3,7× i uzna, że patch nie zadziałał.

Raporty: [E25-10](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-10-exposicion-por-fila.md) (dopasowanie 32 pasm, T044),
[E25-17](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-17-bulb-exposicion-electronica-larga.md) (1/8000…30 s, BULB),
[E25-18](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-18-integracion-silent-todas-velocidades.md) (C3-B),
[T046/T047](https://github.com/nicolvus/a6000-fw-decomp/blob/main/docs/capture/e25-19-verificacion-fisica-exposicion-larga.md) (prawo `r5`, sprawdzenie predykcji),
[wiki 6](https://github.com/nicolvus/a6000-fw-decomp/wiki/6-Capa-2-exposicion-uniforme) (przepis warstwy 2).
