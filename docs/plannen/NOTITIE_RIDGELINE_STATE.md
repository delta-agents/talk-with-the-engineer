# Notitie — de toestand als ridgeline: een compacte vorm voor PolderState en SystemState

Vastgelegd om verder te verkennen, nog geen plan. De vraag: bestaat er één compacte
visualisatievorm die de onderdelen van een `PolderState` of `SystemState` naast elkaar
zet zonder dashboard te worden? De kandidaat is de **categorical ridgeline** (gestapelde
dichtheden of gestapelde reeksen met bewuste overlap), zie
[drhill.io/blog/ridgelineplots](https://drhill.io/blog/ridgelineplots/) en het
ggridges-gedachtegoed daarachter.

De drie varianten hieronder draaien op échte modeluitvoer (`simulate` en
`simulate_network` op de referentiepolder), via `scripts/verkenning_ridgelines.py`.

## Variant 1 — SystemState: de keten, elke knoop een rij

![keten](../images/verkenning/ridgeline-keten.png)

Zes knopen in een kralenketting, oplopende capaciteit stroomafwaarts, de rand met het
boezemgemaal. Elke rij is de waterstandsreeks van één knoop; de rijen overlappen bewust
zodat de cascade als één beeld leest. **Bevinding uit de eerste poging:** met gelijke
capaciteiten klemmen de middenknopen alle vier op exact dezelfde stand — de ridgeline
maakt in één oogopslag zichtbaar dat de keten tegen één klem loopt, wat in een tabel
vier keer hetzelfde getal was geweest. Dat is precies het soort systeemuitspraak
(vergelijk `CascadeOutput`: de bindende beperking en waar hij zit) waar deze vorm goed
in is.

## Variant 2 — herhaaltijden: de verdeling schuift op met T

![herhaaltijden](../images/verkenning/ridgeline-herhaaltijden.png)

Dezelfde polder, acht buien (T=2 t/m 1000), per rij de verdeling van de uurlijkse
waterstanden. De tweetoppigheid is echt: de linkerbult is het begin van de bui, de
rechterbult het plateau waar het gemaal het niet meer bijhoudt. Dit is de **ruwe
grondstof van de overschrijdingsfrequentielijn** uit `VERKENNING_BUDGETVRAAG.md` §6 —
dezelfde veeg, als verdeling getoond in plaats van als lijn.

## Variant 3 — PolderState: maatregelen tegen hun referentie

![maatregelen](../images/verkenning/ridgeline-maatregelen.png)

Eén bui, vier toestanden: de referentie en drie maatregelen, elk met de referentie als
grijs spook erachter. De vorm laat het karakter van elke maatregel zien — vasthouden
vertraagt, bergen dempt, afvoeren pompt de staart weg — en dat is de visuele
tegenhanger van de bijdrage-per-maatregel uit de frequentielijn-discussie.

## Ontwerpkeuzes tot nu toe

* **De ordening van de rijen draagt de betekenis**: stroomafwaarts (variant 1),
  oplopende T (variant 2), of maatregel-identiteit (variant 3). Nooit alfabetisch.
* **Kleur volgt het werk**: sequentieel één blauw, licht → donker, voor geordende rijen
  (diepte, T); categorische kleuren in vaste volgorde alleen waar de rij een identiteit
  is (maatregelen).
* **Overlap is een instelling, geen ongeluk** — het ggridges-`scale`-idee; hier ~0,85
  van de rijafstand voor reeksen en ~1,5 voor dichtheden.
* De uren van een bui zijn **geen onafhankelijke steekproef** (autocorrelatie); de
  dichtheden van variant 2 zijn dus een beeld van "waar de toestand zijn tijd
  doorbrengt", geen kansverdeling. Dat hoort in elk bijschrift.

## Open vragen voor de volgende ronde

1. Welke onderdelen van de toestand verdragen één gedeelde as? Waterstand wel;
   voorraad, marge en kosten hebben elk hun eigen eenheid — een ridgeline per grootheid,
   of normaliseren tegen de eigen norm?
2. De MGA-koppeling: de romp uit `VERKENNING_BUDGETVRAAG.md` §5 als ridgeline — per
   maatregel de verdeling van zijn maatvoering over de near-optimale pakketten.
3. Renderkanaal: als los beeld (zoals hier), of interactief via MCP Apps bij een
   toolresultaat (spec 2026-07-28). Eerst moet de vorm zelf overtuigen.
4. Donkere modus en het huisstijlpalet: dit is het referentiepalet uit de verkenning,
   niet de HKV-huisstijl.

---

## Ronde 2 — de waterdraad: van rijen naar draden

De ridgeline-varianten hierboven splitsen op de y-as uit. De tweede ronde kantelt dat
naar het beeld waar de zoektocht eigenlijk om draaide: de topologie als **één
horizontaal vat** — elke knoop een verwijding (de waterstandsverdeling als rechtopstaand
blaasje), elke verbinding een vernauwing met zijn capaciteit als dikte, elk gemaal een
klep, en de bui die doortrekt als peristaltiek. Interactief (SVG/JS, geen matplotlib):
het prototype staat in `waterdraad.html` naast deze notitie, de data komt uit
`scripts/verkenning_waterdraad.py` (vier echte `simulate_network`-runs: referentie plus
cumulatief vasthouden, bergen en afvoeren op Middelblok).

![vormmodus](../images/verkenning/waterdraad-vorm.png)

![gewichtsmodus, uur 120](../images/verkenning/waterdraad-gewicht.png)

### Wat deze ronde leerde

1. **De vulling hoort verticaal.** De eerste versie vulde de violin langs zijn
   waarde-as, dus zijwaarts — cognitief verkeerd om voor water. De blaasjes staan nu
   rechtop (hoogte = waterstand, breedte = dichtheid) en lopen bij het afspelen van
   onderaf vol en leeg.
2. **Toestanden zijn losse draden onder elkaar, geen schillen in één draad.** Een
   eerdere versie stapelde de voor/na-verdelingen als schillen in dezelfde verwijding;
   dat werd onleesbaar zodra een maatregel een verdeling liet gróeien. Vier complete
   draden onder elkaar (referentie + drie maatregelstappen) brengen de
   ridgeline-gedachte terug — rijen = toestanden, kolommen = knopen — en één tijdlijn
   drijft ze synchroon.
3. **De referentie-omtrek als gestreept spook in elke rij eronder** maakt voor/na per
   blaasje leesbaar, en maakt afwenteling tot één beeld: afvoeren op Middelblok laat
   het eigen blaasje in zijn spook krimpen (2,21 naar 0,37 m) terwijl het blaasje van
   Zuidplas er b&uacute;iten groeit (0,25 naar 1,37 m; zijn rand van 108 naar 144 u op
   capaciteit).
4. **Breedte is een keuze met twee eerlijke standen.** Vormmodus (gelijke breedte)
   vergelijkt verdelingsvormen; gewichtsmodus (breedte evenredig met het
   open-wateroppervlak) leest als visuele massa — de boezem wordt het brede stille vat
   dat hij is, Hooghout het smalle. Het is een proxy en geen kuubs, en zo staat het ook
   op de pagina.
5. **KDE-hygiëne**: de omtrek is afgekapt op het echt bereikte bereik van de reeks;
   zonder die afkap tekende de staart een haarlijn boven de werkelijke piek.

### Open voor ronde 3

* de droge kant als tweede helft van het vat (onder de draad), zodra de
  voorraden-doorrekening per knoop beschikbaar is;
* vertakkende topologieën — dit is een ketting, een boom vraagt splitsende draden;
* de MGA-romp (VERKENNING_BUDGETVRAAG.md §5) als band om elk blaasje: niet één
  verdeling per toestand maar de bandbreedte van de near-optimale pakketten;
* het buiprofiel als klein verloop bij de tijdlijn, zodat de peristaltiek aan zijn
  aanleiding gekoppeld is;
* normalisatie per blaasje versus over de hele draad — nu per blaasje, en dat blijft
  een gemelde keuze.
