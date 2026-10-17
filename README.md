# Mulle Meck på en ny dator

Spela de gamla Mulle Meck-spelen från 90-talet på Windows 10/11 och Steam
Deck. Med handkontroll om du vill, och med skarpare bilder (HD).

> **Testat på Windows och Steam Deck.** Det finns en Linux-version också,
> men den är inte testad på andra datorer än Steam Deck.

| Spel | |
|---|---|
| Bygg bilar med Mulle Meck | fungerar |
| Bygg båtar med Mulle Meck | fungerar |
| Bygg hus med Mulle Meck | fungerar |
| Upptäck rymden med Mulle Meck | kommer senare |

## Ladda ner

### ➜ [Ladda ner för Windows](https://github.com/dankar89/mellemuck/releases/latest/download/MulleMeck-Windows.zip)

(För Linux, otestad: [MulleMeck-Linux.tar.gz](https://github.com/dankar89/mellemuck/releases/latest/download/MulleMeck-Linux.tar.gz).
Alla versioner: [Releases](https://github.com/dankar89/mellemuck/releases).)

**Spelen ingår inte.** Du behöver din egen kopia av spelet: skivan, eller en
skivavbild (`.iso`) eller `.zip` med spelet.

## Så här gör du

1. **Packa upp** zip-filen: högerklicka på den och välj **Extrahera alla...**
   Lägg mappen på till exempel Skrivbordet (inte i "Program Files").
2. Öppna mappen **MulleMeck** och dubbelklicka på **Mulle Meck.exe**.
   Säger Windows *"Windows skyddade datorn"*? Klicka **Mer information** och
   sedan **Kör ändå**. (Det står så för alla program som inte kommer från ett
   stort företag.)
3. Klicka **Hitta spelet**. Har du skivan i datorn, eller spelfilen i Hämtade
   filer, på Skrivbordet eller i Dokument, hittar Mulle Meck den själv.
4. Klicka på den gula knappen **Spela**.

Vill du ha skarpare bilder: klicka **Gör HD-bilder**. Det görs på din dator
och tar 15-50 minuter per spel; du kan spela under tiden.

Allt annat (handkontroll, Steam Deck, sparningar, ny version) står i filen
**LÄS MIG.txt** i mappen.

## Något krånglar?

[Skriv här](https://github.com/dankar89/mellemuck/issues) och berätta vilket
spel, vad du gjorde och vad som hände.

---

Ett hobbyprojekt av fans, utan koppling till Mulle Meck-böckerna eller spelens
utgivare. Spelen tillhör sina upphovspersoner; här finns bara fri programvara.

## For developers (English)

The games are Macromedia Director 6-8.5 projects. They run unchanged in our
build of [ScummVM](https://www.scummvm.org)'s Director engine
(`patches/scummvm-mulle.patch`, on ScummVM commit `c420cad105`) with fixes,
HD art, gamepad driving and sailing, a pause menu and per-player saves. The
launcher (`launcher/`, Python with pygame-ce) finds the player's disc, makes
the HD art on their GPU (Real-ESRGAN, `tools/`) and copies everything to a
Steam Deck. Nothing from the games is in this repository.

- [docs/README.md](docs/README.md): the Director file format, per-game notes,
  every ScummVM fix and why, upscaling, the launcher, tooling.
- Building: `tools/build-windows.sh`, `tools/build-linux.sh`,
  `tools/build-launcher-windows.sh`, then `tools/build-release.sh VERSION`
  (see [docs/tooling.md](docs/tooling.md)).

Licences: the ScummVM changes are GPL-3.0, as ScummVM. The bundled parts are
listed in [release/LICENSER.txt](release/LICENSER.txt).
