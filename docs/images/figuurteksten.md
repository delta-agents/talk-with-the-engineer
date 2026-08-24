# Teksten van de figuren

Losse tekst uit de SVG's in `docs/images`, zodat ze te kopiëren en te herschrijven zijn
zonder in de XML te hoeven. Handmatige regelafbrekingen uit de SVG zijn hier weer tot
hele zinnen samengevoegd.

Bij wijzigingen: dit bestand is de leesbare versie, de SVG is de bron. Pas ze samen aan.

---

## `world-model-eenvoudig.svg`

**Titel:** Een model waarin je kunt zoeken
**Ondertitel:** Wat een world model is, wat het onze is, en wat dat van onze modelbouw vraagt

### Band 1 — twee vragen

> **DE VRAAG DIE WE GEWEND ZIJN**
> "Hoe hoog komt het water bij deze bui?"

> **DE VRAAG VAN EEN ONTWERPER**
> "En hoe hoog komt het als ik dít doe?"

De tweede vraag is geen voorspelling: het model moet weten wat jóuw keuze met het systeem doet.

*Zo'n model heet in de informatica een world model. Verder is er niets magisch aan — het is een vorm, en die vorm is het hele verhaal.*

### Band 2, links — Zoals we een model meestal laten rekenen

*niets mis mee — hij is precies gebouwd voor de eerste vraag*

Keten: **de schematisatie** → **de gegevens** (het gebied, de bui) → **de berekening** (minuten tot uren) → **de uitvoer** (kaarten, reeksen, grafieken)

Doorgekruiste terugweg: **dit gaat niet terug naar binnen**

> Wat eruit komt is niet hetzelfde soort ding als wat erin ging.
> Een andere maatregel? Dan zet je een nieuwe berekening op.
> Een computer kan er dus niet zelf in zoeken.

### Band 2, rechts — Ons model, en waarom er wél in te zoeken is

*dezelfde massabalans — alleen een andere vorm eromheen*

Invoer: **één maatregel** + **de bui**

Keten: **de polder nu** (oppervlak, open water, gemaal, streefpeil) → **de stap** (drie regels waterbalans, 0,06 milliseconde) → **de polder daarna** (precies dezelfde soort gegevens)

Terugpijl: **en die gaat er zó weer in**

> Wat eruit komt is dezelfde polder, in dezelfde vorm.
> Dus je kunt het duizenden keren achter elkaar doen.
> En dan kan een computer het zoekwerk overnemen.

### Band 3 — drie voetkaarten

**En dan kan hij kiezen**
Noem een eis en een prijs, en hij loopt alle maatregelpakketten af en levert het goedkoopste dat eronder blijft.
*Eerlijk: peil omhoog kost geen euro's maar drooglegging, en die prijs hebben we niet.*

**Hier sluit het aan op de wiskunde**
Omdat de stap klein en glad is, kun je hem differentiëren. Dan werken de zoekalgoritmen uit de optimalisatie — en schaalt dezelfde vorm van één polder naar 8.500 gebieden, met de gradiënt erbij in tientallen ms.

**Geen netwerk, en geen AI-verhaal**
De term komt uit de robotica, waar de dynamiek niet op te schrijven is. In een polder kan dat wel: het is een massabalans. We lenen de vorm, niet de techniek.
*Het taalmodel rekent niet — dat vertaalt alleen.*

---

## `ribasim-en-wij-eenvoudig.svg`

**Titel:** Twee keer een world model, twee verschillende vragen
**Ondertitel:** Ribasim en onze vuistregels lijken op elkaar. Het verschil zit in wat er vastligt en wat er beweegt.

### Band 1 — wat ligt vast, wat beweegt

| | **Ribasim**<br>*een model om een watersysteem te laten dráaien* | **Onze vuistregels**<br>*een model om een watersysteem te ontwerpen* |
|---|---|---|
| **WAT VASTLIGT** | de polder: gemaal, stuw, sloten | de bui |
| **WAT BEWEEGT** | het water | de polder zelf |
| **DE VRAAG** | "wat gebeurt er met het water?" | "hoe moet de polder worden?" |

### Band 2 — De test: het gemaal

*twee maatregelen die op elkaar lijken, en waar de twee modellen precies omdraaien*

| | RIBASIM | ONZE VUISTREGELS |
|---|---|---|
| Het gemaal **ánders** aanzetten | ✓ regelregels per kunstwerk, met tijdreeksen | – alleen voorbemaling, en verder niet |
| Het gemaal **gróter** maken | ✗ wel in te voeren, geen stap in het model | ✓ één stap, met een prijs eraan |

> **Allebei een gat — en het zijn niet dezelfde gaten. Dát is het punt.**

### Band 3 — Dezelfde vragen, langs elkaar gelegd

| | RIBASIM | WIJ |
|---|---|---|
| Weet het hoe de polder er nu voor staat? | ja, veel preciezer dan wij | ja, in een handvol getallen |
| Zeg 'doe dit': krijg je een nieuwe polder terug? | nee, je past de invoer aan | ja, dat is de hele opzet |
| Rekent het uit wat een pakket kost? | nee, er zitten geen euro's in | ja — en het zegt wat geen prijs heeft |
| Verdeelt het bij tekort over veel gebruikers? | ja, en netter dan wij | alleen als ieder één bron heeft |

### Band 4 — drie voetkaarten

**Dus niet: wij zijn beter**
Ribasim is een world model voor het dráaien van een systeem, het onze voor het ontwerpen. Twee vragen, twee vormen.

**En niet: wij zijn sneller**
Ribasim rekent een veel zwaarder systeem door. Wij hebben geen snelheid nodig maar een som waarvan je duizenden kunt doen.

**Wat je hiermee wél kunt vragen**
"Wat is goedkoper: een groter gemaal of meer open water?" Dan moet een maatregel een ding zijn, met een prijs eraan.

---

## `rl-eenvoudig.svg`

**Titel:** Het duurste deel hebben we al
**Ondertitel:** Zelflerende computers — reinforcement learning — moeten de wereld eerst leren kennen. Onze polder staat er al, en hij is exact.

### Band 1 — de lus, twee keer

**Zoals het meestal gaat** · *de computer moet de wereld eerst leren kennen*

`de leerling` (probeert iets uit) → "ik probeer dit" → `de wereld` (gestippeld, met een vraagteken) → "zo staat het er nu voor, en dit was het waard" → terug

> Hier gaat bijna alle rekentijd naartoe.

**Bij ons** · *die wereld staat er al, en hij is exact*

`de zoeker` (kiest een maatregel) → "maak het gemaal 3 m³/s groter" → `de polder` (drie regels waterbalans, 0,06 milliseconde) → "dit is de nieuwe polder, en zoveel kostte het" → terug

> Dat leren hoeft dus niet. Wij weten het al.

### Band 2 — Vijf stukken heb je nodig. Vier liggen er.

*en die vier zijn precies waar de afgelopen maanden aan gebouwd is*

| | stuk |
|---|---|
| ✓ | de polder, in een paar getallen |
| ✓ | de maatregelen, met een prijs |
| ✓ | de bui, en de droge zomer |
| ✓ | de stap: nieuwe polder eruit |
| ✗ | het cijfer dat zegt hoe goed het was |

*Voor de uur-voor-uur variant is er nog iets kleins nodig: een tellertje dat de waterstand tussen de uren vasthoudt. Dat is een middag werk.*

### Band 3 — Hoe groter de vraag, hoe nuttiger een zelflerende aanpak

*bij de kleinste vraag zou hij het juist sléchter doen dan wat we nu hebben*

1. **één polder, één bui** — dit rekenen we nu al exact uit — niet doen
2. **en nu de tijd erbij** — wat bouw ik nu, wat stel ik uit, terwijl de norm nog schuift?
3. **en nu 8.500 gebieden tegelijk** — alle combinaties aflopen kan niet meer: dat zijn er te veel om te tellen. Híer valt echt iets te winnen.

### Band 4 — En het cijfer verzinnen we niet, we lezen af waar het antwoord kantelt

*wat een centimeter droge voeten waard is, is een vraag voor het waterschap. Het model zegt alleen wáár het omslaat.*

Prijsas — wat één centimeter peil omhoog mag kosten →

| vanaf | goedkoopste pakket |
|---|---|
| € 0 | gemaal groter + peil omhoog |
| € 0,14 mln | en er komt een beetje open water bij |
| € 1,5 mln | open water + peil omhoog |

---

## `kaart-is-een-keuze.svg`

**Titel:** De kaart is ook een keuze
**Ondertitel:** We rekenen maatregelen uit op een kaart die vastligt. Maar welke verbindingen er zouden móeten zijn, is nooit de vraag geweest.

### Band 1 — getal tegenover lijn

**Zo verdelen we het water nu** · *de kaart ligt vast; wij draaien aan de knoppen erop*
Chips op de knopen: `+100 ha berging`, `+3 m³/s gemaal`. Ketting A → B → C → zee.
Elke maatregel is een getal dat omhoog gaat op iets dat er al staat: gemaal, open water, peil.

> De lijnen op de kaart doen niet mee.

**Zo zou het ook kunnen** · *een kanaal is geen groter getal, het is een nieuwe lijn*
IJsselmeer — – – een kanaal – – → C ("hier is het droog").
Voor hoog Nederland is niet de capaciteit de klem maar de beschikbaarheid. Een knop helpt niet.

> De lijn zelf is dan de maatregel.

### Band 2 — Wat het kost om per polder te beslissen

*gemeten op een ketting van vijf polders: dezelfde twee maatregelen, los en gekoppeld*

| | afvoeren | bergen |
|---|---|---|
| los gerekend, per polder | € 66 k | € 178 k |
| gekoppeld, als systeem | € 502 k | € 101 k |

**De rangorde klapt om.** Los is pompen goedkoop. Gekoppeld is het zeven keer duurder, en bergen wint. *Bij elke opvoerhoogte die echt voorkomt: 1 tot 5 m.*

### Band 3 — De trap van ambitie, en waar het model nu staat

*de onderste twee treden zijn de praktijk van vandaag; de bovenste is de stip*

| trede | vraag | status |
|---|---|---|
| één polder | "Welke maatregel, en hoe groot?" | kan nu, en exact |
| één regio | "Klopt mijn idee qua orde van grootte?" | kan nu — híer zit de praktijk |
| één stroomgebied | "Wie moet bergen zodat de buur niet pompt?" | bijna: de verdeling ontbreekt |
| heel Nederland | "Welke lijnen zouden er moeten zijn?" | nog niet — en híer komt RL binnen |

### Band 4 — Het kanaal naar Enschede, doorgerekend tot waar het kan

*Twente, 4000 ha met 1 % open water, een tekort van 4 mm per dag over 30 dagen*

**Wat het model nu al zegt**
Nodig: **4,68 miljoen m³** in een maand. De eigen buffer is 3,0 mm, dus de bodem na 0,7 dag.
*Een debiet klinkt haalbaar. Dit getal nodigt uit tot narekenen.*

**Wat het nog niet zegt**
Of het IJsselmeer dat kan missen. Wat een kanaal kost: een verbinding heeft geen prijs in het model.
*En of dít de goedkoopste lijn zou zijn. Daarvoor moet je lijnen kunnen vergelijken.*

**Waarom dit de RL-vraag is**
Bij 8.500 gebieden zijn er miljoenen lijnen die je zou kunnen trekken. Ze allemaal aflopen kan niet.
*Zoeken over líjnen in plaats van over getallen — dát is wat er nieuw is.*

---

## `nederland-nu-en-straks.svg`

**Titel:** Nederland, nu en misschien straks
**Ondertitel:** Links hoe we het water nu verdelen. Rechts een gedachtenexperiment: niet een uitkomst van het model, maar de vraag die het zou moeten kunnen stellen.

Schematische kaart, twee keer dezelfde omtrek. Geen geografie — een hoekige contour, drie Waddeneilanden en het IJsselmeer als blok.

### Links — Nu

*8.500 stukjes, elk met een eigen som en een eigen gemaal*

Fijn raster over het land, dikke bruine lijnen er dwars doorheen, zes pijlen naar buiten. Twente en Achterhoek in oranje.

Legenda: `8.500 eenheden` · `grenzen van vroeger` · `elk pompt naar buiten` · `water is hier schaars`

> Ieder rekent zijn eigen stuk, en de grenzen volgen het water niet.

### Rechts — Misschien straks

*grovere stukken, en lijnen die er nu nog niet liggen*

Grof raster, geen bestuursgrenzen, twee groene stippellijnen van het IJsselmeer naar Twente en de Achterhoek, en nog maar twee pijlen naar buiten. Stempel in de kaart: **verzonnen, niet gerekend**.

Legenda: `ongeveer 250 districten` · `nieuwe verbindingen` · `hier is dan wél water` · `minder naar buiten`

> Beslissen waar de koppeling zit, en de lijn zelf mag de maatregel zijn.

### Voet — Wat hiervan gemeten is, en wat niet

**Dit is gemeten** — Per polder beslissen geeft het verkeerde antwoord: afvoeren gaat van € 66 k naar € 502 k per cm, en bergen wint.

**Dit is verzonnen** — Elke grens en elke lijn op de rechterkaart. Er zit geen echte topologie in het model; de meting hierboven is een ketting van vijf.

**Dit is er nodig** — Een maatregel die een líjn toevoegt, een prijs voor een verbinding, en een bron die eindig is en gedeeld wordt.

---

## `de-knoop-is-oppervlak.svg`

**Titel:** De knoop is geen punt
**Ondertitel:** Een gebied neemt ruimte in — de knopen bedekken samen heel Nederland, precies één keer. Dan is niet alleen de lijn een keuze, maar ook de indeling zelf.

### Band 1 — punt tegenover oppervlak

**Zo schrijven we het netwerk-probleem meestal op** · *de knoop is een punt; alleen de lijn is nieuw*
Ketting A → B → C, met een gestippelde groene boog ("een lijn erbij?") eroverheen.
Een knoop is een punt zonder oppervlak. Je kunt er alleen een lijn bij tekenen.

> Alleen de lijn is een keuze.

**Maar bij ons is de knoop oppervlak** · *elk gebied is een stuk land; samen bedekken ze Nederland, precies één keer*
Een betegeld vlak, opgedeeld in drie gebieden A, B, C.
De knoop hééft oppervlak, en de som is behouden. Dus hoe je de stukken groepeert, is óók een keuze.

> De indeling is dan óók een maatregel.

### Band 2 — twee assen van ontwerp, en de derde ligt er al

*de knoop en de lijn zijn allebei een keuze; de maatregel binnen een knoop lost het model al exact op*

| as | de beslissing | beeld |
|---|---|---|
| **As 1 · de partitie** (de knopen) | welke stukjes vormen samen één knoop | 8.500 eenheden → ±250 districten; grenzen die het water volgen, niet die van vroeger |
| **As 2 · de topologie** (de lijnen) | welke lijnen liggen tussen de knopen | een lijn is geen groter getal — het is een nieuwe verbinding, en hij hangt af van waar de grens ligt |
| **As 3 · de maatregel** (ín de knoop) | hoeveel open water, gemaal, peil | ✓ dit lost `optimize` al exact op |

### Band 3 — en de twee assen zijn gekoppeld

*'los' en 'gekoppeld' zijn geen twee scenario's — het zijn twee indelingen van hetzelfde oppervlak*

| | afvoeren | bergen |
|---|---|---|
| los gerekend, per polder (vijf losse knopen) | € 66 k | € 178 k |
| gekoppeld, als systeem (vijf cellen, één knoop) | € 502 k | € 101 k |

**Waar je de grens trekt, bepaalt wat over een lijn loopt.** Dezelfde vijf polders, twee indelingen. Daarom klapt de rangorde om: los is pompen goedkoop, gekoppeld wint bergen. De partitie en de lijn zijn één probleem.

---

## Onderbouwing van de Ribasim-uitspraken

Nagelezen in `Deltares/Ribasim` op `main`, augustus 2026.

| uitspraak in de figuur | bron |
|---|---|
| het kunstwerk is een instelling, niet een toestand | `core/src/parameter.jl`: `@kwdef struct Pump <: AbstractParameterNode`, met `max_flow_rate::Vector{ScalarConstantInterpolation}` |
| het water is de toestand | `core/src/parameter.jl`: `const state_components = (:tabulated_rating_curve, :pump, :outlet, :user_demand_inflow, :user_demand_outflow, :linear_resistance, :manning_resistance, :evaporation, :infiltration, :integral)` — cumulatieve fluxen; bergingen zijn een reductie daarvan |
| regelregels wijzigen een parameterinstelling | `core/src/parameter.jl`: `DiscreteControl` met `ControlStateUpdate`; en `concept.html`: *"change a parameter setting of an infrastructure element"* |
| er zitten geen euro's in | `core/src/allocation_optim.jl`: doelfuncties zijn tekort, fairness en routeprioriteit — geen kosten |
| de verdeling is een LP per prioriteit | `core/src/allocation_optim.jl`: *"Lexicographic goal programming: … add constraint: obj_i ≤ optimal_i + ε"* (JuMP; HiGHS volgens de docs) |
| Ribasim differentieert, maar een andere afgeleide | `core/src/differentiation.jl`: `Jf(u) = Jg(A*u)*A` via DifferentiationInterface.jl — dus `∂f/∂u` voor de impliciete solver, niet `∂J/∂a` |
