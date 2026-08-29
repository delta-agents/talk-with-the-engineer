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
