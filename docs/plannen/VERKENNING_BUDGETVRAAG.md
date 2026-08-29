# Verkenning — de budgetvraag: van "goedkoopste" naar prijs-kwaliteit en meekoppelkansen

De aanleiding is een vraag die elke adviseur herkent en die de pakketzoeker in zijn huidige
vraagrichting niet kan beantwoorden:

> *"We hebben 10 miljoen euro tot onze beschikking. Wat is het beste maatregelenpakket
> voor ons waterschap, voor zowel watertekort als wateroverlast — zeg beide op een niveau
> dat eens per vijftig jaar voorkomt?"*

`PLAN_PAKKETZOEKER_ALS_TOOL.md` blijft staan als fase 1: de deur naar `optimize`. Deze
verkenning ontwerpt wat er dóór die deur bereikbaar moet worden, en corrigeert onderweg
één woord in dat plan: het gaat niet om "cheapest". De vraag van een waterschap is niet
"wat is het minste geld waarmee ik wegkom" maar **"waar koopt een euro veel bescherming,
waar houdt dat op, en welke maatregelen hebben we sowieso geen spijt van"** —
prijs-kwaliteit en meekoppelkansen.

De centrale bevinding van deze verkenning: **daar is geen nieuwe optimalisator voor
nodig.** De budgetvraag, de prijs-kwaliteitvraag en twee van de drie meekoppelvragen zijn
aflezingen van één object — het kostenvlak over de beschermingsniveaus — en elke cel van
dat vlak is één aanroep van de bestaande `optimize`. Wat ontbreekt is de veeg en de
leeslaag, niet de rekenkern. De machinerie voor de leeslaag ligt er bovendien half:
`switch_price_of` citeert de MGA-literatuur al, `MeasureRole` ís de no-regret-uitspraak,
en `distinct_answers` levert de "verschillende soorten pakketten".

---

## 0. De vraag ontleed: drie vragen en een ontbrekende weging

"Het beste pakket voor 10 miljoen, voor beide assen" bevat drie vragen:

1. **Haalbaarheid** — past wat we moeten halen binnen wat we kunnen besteden?
2. **Afruil** — als het budget knelt: wat kopen we op de natte as, wat op de droge, en
   welke combinaties liggen op de rand?
3. **Karakter** — zijn er wezenlijk verschillende pakketten voor hetzelfde geld, en welke
   maatregelen zitten in állemaal?

"Het beste" heeft daarbij geen antwoord zolang niemand zegt hoe een millimeter minder
tekort zich verhoudt tot een centimeter minder peilstijging. Die weging gaat het model
**niet zelf invullen** — dat is dezelfde discipline als bij `near_optimal` (geen winnaar
uitroepen die het model niet draagt) en bij de verdringingsreeks (gelijk tekort is een
gemelde proxy, geen waarheid). Het model levert de afruil; de weging is aan het
waterschap. Alles hieronder is erop gebouwd om die afruil zó te presenteren dat de weging
een bespreekbare vraag wordt in plaats van een verborgen aanname.

---

## 1. Kwaliteit heeft al een as: het beschermingsniveau als herhaaltijd

De verrassing van deze verkenning is hoe weinig er ontbreekt. "Kwaliteit" klinkt als een
nieuw begrip, maar beide assen zitten al als eersteklas invoer in de toolset:

* **nat**: `return_period` uit de STOWA-neerslagstatistiek (0,5 t/m 100 jaar);
* **droog**: `drought_return_period` uit de STOWA-droogtestatistiek (2, 5, 10, 25, 50,
  100), per regio en klimaatscenario.

Definieer het **beschermingsniveau** van een gebied als het paar (T_nat, T_droog) dat het
aankan terwijl de normen gehaald worden — de inundatienorm (`max_dh_total_m`) aan de
natte kant, de tekortnorm (`max_shortfall_mm`) aan de droge. De normen liggen vast (NBW,
peilbesluit); de herhaaltijden zijn de kwaliteitsas. De openingsvraag wordt dan exact
uitspreekbaar met invoer die vandaag bestaat:

    return_period=50, drought_return_period=50, normen uit het gebied
    → optimize → pakket + prijs(band)

Dat is fase 1. Alles hierna is de vraag wat er gebeurt als je die (50, 50) laat lopen.

---

## 2. Het centrale ontwerp: één kostenvlak, vier aflezingen

Laat T_nat en T_droog over hun roosters lopen en reken per combinatie het goedkoopste
pakket uit:

    kosten(T_nat, T_droog),  met per cel het pakket, de band, en de near-optimale set

Elke cel is één `optimize`-aanroep: eenendertig SLSQP-runs op een doorrekening van
0,06 ms — orde honderd milliseconden per cel, dus een rooster van 6 × 8 cellen is
**secondenwerk**, en de cellen zijn onafhankelijk (triviaal parallel, en cachebaar per
gebied). Geen nieuwe optimalisator, geen convergentievraag die er nog niet was.

Op dat ene vlak zijn alle gestelde vragen een aflezing:

| vraag | aflezing |
|---|---|
| "wat kost bescherming (50, 50)?" | één cel — dit is fase 1, de pakketzoeker |
| "wat koopt €10 mln?" | de iso-kostenlijn: alle (T_nat, T_droog) met kosten ≤ budget |
| "is T=50 verstandig, of is T=25 bijna even duur?" | de stapkosten langs een as — prijs-kwaliteit, §3 |
| "wat levert het op dat één maatregel beide assen dient?" | de synergiewinst per cel — meekoppelen, §4a |
| "waar hebben we geen spijt van?" | de rol van elke maatregel óver het vlak — §4b |
| "welke wezenlijk verschillende pakketten zijn er voor dit geld?" | de near-optimale set in de budgetcellen — §5 |

Eén eerlijkheid vooraf, en die moet in elke uitvoer doorklinken: door de kostenbanden
(bergen −11/+70 %) is het vlak een **band**, geen oppervlak. Het bestaande
epsilon-dominantie-criterium (`cost_epsilon`) bepaalt al wanneer twee pakketten niet te
onderscheiden zijn; hier bepaalt het wanneer twee *cellen* dat niet zijn. "T=100 is
duurder dan T=50" mag alleen gezegd worden als de banden het dragen — en "die twee
beschermingsniveaus kosten hetzelfde, voor zover wij prijzen kennen" is een volwaardig en
vaak het waardevolste antwoord.

---

## 3. Prijs-kwaliteit, concreet: stapkosten en knikpunten

Prijs-kwaliteitverhouding is op het vlak een gewone afgeleide: **wat kost de volgende stap
in herhaaltijd, per as.**

    van (25, 50) naar (50, 50): +€1,8 mln   (band 1,6–2,4)
    van (50, 50) naar (100, 50): +€7,1 mln  (band 6,4–9,8)

Het **knikpunt** — waar de stapkosten een sprong maken — is de prijs-kwaliteituitspraak
waar een bestuurder iets aan heeft: "tot T=50 koopt u bescherming voor minder dan twee
miljoen per stap; daarboven verviervoudigt de prijs per stap." Dat is geen advies en geen
weging; het is de vorm van het vlak, en die draagt het model wél.

Waarom de stap duurder wordt is bovendien uitlegbaar met wat er al is: het duurder worden
valt samen met een wissel in het pakket (een maatregel loopt tegen zijn bereik aan, een
duurdere komt erbij), en dat is per cel afleesbaar uit `binding` en de pakketsamenstelling.
De uitvoer hoort die twee aan elkaar te koppelen: *"boven T=50 is bergen uitgeput en gaat
elke verdere stap via het gemaal."*

Ook hier de discipline van §2: een stap waarvan de kostenbanden overlappen is **geen
knikpunt** maar "niet te onderscheiden", en zo hoort hij benoemd.

---

## 4. Meekoppelkansen: drie soorten, en voor twee ligt de machinerie er al

"Meekoppelen" betekent in de praktijk drie verschillende dingen, en het ontwerp moet ze
uit elkaar houden omdat ze verschillende antwoorden hebben.

### 4a. Interne synergie: één maatregel, twee assen

Bergen vergroot de inundatiemarge én de voorraad; peilopzet koopt voorraad maar snoept
inundatiemarge — een negatieve koppeling. De maat daarvoor is per cel uit te rekenen met
drie aanroepen die er al zijn:

    synergiewinst(T_nat, T_droog) =
        kosten(alleen nat) + kosten(alleen droog) − kosten(beide tegelijk)

Een positieve winst is de meekoppelkans in euro's: *"de natte en droge opgave samen
aanpakken is €2,1 mln goedkoper dan ze apart oplossen, en dat verschil is bergen."* Een
negatieve zou een modelfout zijn (samen mag nooit duurder dan apart, de eisen zijn een
superset) — dat is meteen een gratis consistentietoets op de rekenkern.

### 4b. No-regret: de rol van een maatregel óver het vlak

`MeasureRole` zegt per gebied al FORCED / OPTIONAL / ABSENT — zit een maatregel in elk
near-optimaal pakket, in sommige, of in geen. Til die uitspraak van één cel naar het
geveegde gebied en je hebt de no-regret-lijst:

* **FORCED over het hele vlak** — deze maatregel zit in elk verdedigbaar pakket, bij elke
  ambitie: begin hier, ongeacht wat het bestuur nog beslist;
* **OPTIONAL** — hier is de keuze, en het vlak laat zien wáár hij speelt;
* **ABSENT over het hele vlak** — draagt niet bij; van tafel.

WP12 mat al dat de rangorde robuuster is dan de maatvoering (0 van 162 combinaties draaide
om); dit is dezelfde bevinding, één abstractieniveau hoger, en de aggregatie is het enige
nieuwe stukje code.

### 4c. Externe meekoppeling: als een derde meebetaalt

De echte "meekoppelkans" van de gebiedsontwikkelaar: bergen wordt goedkoper als het
meelift met woningbouw of natuurontwikkeling. Dat is in dit model een **prijsvraag**, en
het antwoord bestaat al bijna: `switch_price_of` varieert een prijs en leest af waar het
goedkoopste pakket omslaat — nu alleen voor prijsloze maatregelen (peilopzet, aanvoeren).
Generaliseer hem naar geprijsde maatregelen (`_priced` kan het al) en de vraag wordt:

> *"Vanaf welke bijdrage van derden komt bergen in het voorkeurspakket?"*
> → "bij meer dan €0,9–1,2 mln cofinanciering wisselt het pakket van gemaal naar berging."

Dat is voor een waterschap een onderhandelingsgetal, en het model produceert het in
plaats van dat iemand het aanneemt — precies de MGA-redenering die al in de docstring van
`switch_price_of` staat. Invoer-kant: een optioneel prijsscenario per maatregel (bijdrage
van derden, of een afwijkende `UnitCost` met bron), zodat "reken eens met grond die al
verworven is" een gewone aanroep is.

---

## 5. Verschillende pakketten voor dezelfde euro's

"Ook met euro's zijn er verschillende soorten maatregelenpakketten op te stellen" — dat
is letterlijk waar, en het model zegt het al: `distinct_answers` ontdubbelt de
near-optimale set op samenstelling, en op de referentiecasus zijn er meerdere pakketten
binnen elkaars kostenband. De budgetvraag hoort dus nooit één pakket terug te geven maar
de **wezenlijk verschillende alternatieven**, elk met samenstelling, band en rol:

    binnen €10 mln, bescherming (50, 50):
      A  gemaal + berging        €8,7 mln (7,9–10,4)   snel uitvoerbaar, geen grond nodig
      B  berging + vasthouden    €9,2 mln (7,4–12,1)   ruimtelijk, meekoppelbaar met §4c
      → niet te onderscheiden binnen de prijsband; vasthouden is in beide FORCED

De karakterisering ("snel uitvoerbaar", "ruimtelijk") is presentatie op basis van de
samenstelling — het model kent alleen de maatregelen en hun getallen, en de uitvoer moet
dat onderscheid bewaken: samenstelling en banden zijn model; duiding is tekst die de
`terugkoppelen`-toets moet doorstaan.

Dit is Modelling to Generate Alternatives in zijn eenvoudigste vorm, en de code verwijst
er al naar. De volgende MGA-stap — actief zoeken naar het pakket dat *maximaal verschilt*
van het voorkeurspakket binnen het budget — noemt `ranges_of` in zijn docstring al als
vervolg ("de echte romp is bij vier variabelen exact uit te rekenen"). Die stap is voor
later; de aflezing hierboven kan zonder.

---

## 6. Het netwerk: waarom de pakketzoeker één gebied ziet, en de weg erheen

De verbazing is terecht — de netwerklaag (`simulate_network`, exact per topologische
diepte; `allocate`, waterfilling op een boom met wettelijke schillen) is af en getest, en
`optimize` gebruikt hem niet. Dat is geen vergissing maar een echte drempel, en die hoort
hier benoemd:

1. **De acties zijn per gebied gedefinieerd.** `apply` neemt één `PolderState` en levert
   er één terug; "bergen in gebied 3" bestaat nog niet als actie op een `SystemState`.
2. **De enumeratie explodeert.** Eenendertig mixen per gebied wordt 31^N over N gebieden.
   De uitlegbaarheid van "we enumereren de mixen" — de bestaansreden van de aanpak —
   overleeft dat niet ongewijzigd.
3. **De koppeling maakt gebieden niet-scheidbaar,** en aan twee kanten verschillend: nat
   is hij lokaal maar gericht (mijn uitstroom is jouw aanvoer: een goedkoop pakket
   bovenstrooms kan benedenstrooms geld kosten), droog is hij globaal (alle gebieden
   trekken aan dezelfde bron).

De weg erheen is daarom gefaseerd, en elke fase is op zichzelf al een antwoord:

* **Fase A — optimaliseer per gebied, toets op het netwerk.** Reken per gebied het
  pakket, zet de pakketten samen, en laat `simulate_network` en `allocate` zeggen waar de
  eengebiedsaanname breekt: welke gebieden na koppeling hun norm alsnog missen, en waar
  de slack zit. Dit gebruikt alles wat er is, kost niets nieuws behalve de lus, en maakt
  de koppelingsfout **zichtbaar in plaats van afwezig**.
* **Fase B — het budget over gebieden verdelen** als buitenste lus over de per-gebied
  kostenvlakken uit §2. De klassieke leesregel is dan gelijke marginale beschermingskosten
  over de gebieden — "een euro moet overal evenveel bescherming kopen" — en dat is §3 op
  systeemschaal. Geen netwerk-optimalisator; wel het antwoord op "10 miljoen voor ons
  waterschap" zolang fase A geen grote koppelingsfouten laat zien.
* **Fase C — pas als A en B aantonen dat de koppeling het antwoord verandert:** gekoppeld
  optimaliseren. En dan nog steeds eerst de vraag of het enumeratief-uitlegbaar kan (de
  natte koppeling is een boom; de droge is één bron), voordat er een generieke solver in
  het pad komt.

---

## 7. Tools en namen

De verleiding is twee symmetrische inversen te bouwen ("kosten gegeven eisen" en
"prestatie gegeven budget"). Deze verkenning komt ergens anders uit: de twee vragen
verschillen niet in richting maar in **vorm van het antwoord** — een punt tegenover een
vlak-met-aflezingen. Dat geeft twee tools:

1. **De puntvraag** (fase 1, het bestaande plan): eisen en herhaaltijden erin, pakket met
   band, alternatieven en rollen eruit. De naam uit het plan —
   `find_cheapest_package_given_constraints` — verliest daarbij twee woorden: *cheapest*,
   omdat het antwoord uitdrukkelijk méér is dan het goedkoopste punt (near-optimaal,
   rollen, omslagprijzen), en *constraints*, omdat de agent-zijde in beschermingsniveaus
   praat. Voorstel: **`find_package_given_protection`**.
2. **De vlakvraag** (deze verkenning): normen, roosters en optioneel een budget en
   prijsscenario's erin; het vlak met zijn aflezingen eruit (iso-kostenlijn als er een
   budget is, stapkosten en knikpunten, synergiewinst, no-regret-lijst, alternatieven in
   de budgetcellen). Voorstel: **`explore_protection_given_budget`**, waarbij het budget
   weglaatbaar is — zonder budget is het antwoord het vlak zelf.

De naamgeving is uitdrukkelijk een open punt (zo is hij ook in het gesprek gemarkeerd);
het besluit hoort te vallen wanneer de `read_me`-module wordt geschreven, want de naam en
de handleiding zijn samen de interface. Wat wél vastligt: het worden er **twee en niet
vijf** — de aflezingen van §3 t/m §5 zijn uitvoer van de vlakvraag, geen eigen tools —
en de budgetvraag krijgt geen eigen "beste pakket"-knop die de ontbrekende weging stil
zou invullen.

Voor de agent is de taakverdeling dan uit te leggen in één zin per tool: *weet u wat u
wilt halen → de puntvraag; wilt u weten wat halen kost of wat uw geld koopt → de
vlakvraag.* De openingsvraag van dit document is vlakvraag met budget, en het antwoord
is: de iso-lijn, de knikpunten eromheen, de no-regret-lijst, en de wezenlijk
verschillende pakketten binnen de €10 mln — mét de melding welke daarvan binnen de
prijsband niet te onderscheiden zijn.

---

## 8. Volgorde

1. **Fase 1 zoals gepland** (`PLAN_PAKKETZOEKER_ALS_TOOL.md`), met de hernoeming uit §7.
2. **De veeg als bibliotheekfunctie** (`explore.py` naast `optimize.py`): het vlak, de
   stapkosten, de synergiewinst en de rol-aggregatie, met de consistentietoets uit §4a in
   de tests. Nog geen tool — eerst laten zien dat de aflezingen kloppen op de
   referentiecasus.
3. **De vlakvraag als tool**, met de uitvoerdiscipline uit §2 (banden, onderscheidbaarheid)
   en §5 (samenstelling is model, duiding is tekst).
4. **Prijsscenario's en de gegeneraliseerde omslagprijs** (§4c).
5. **Netwerk fase A**, en pas daarna B — elk met de toetsvraag vooraf of de vorige fase
   koppelingsfouten liet zien die het antwoord veranderen.

---

## 9. Wat deze verkenning niet is

Geen maatschappelijke kosten-batenanalyse: schadefuncties en de waardering van droog
tegen nat blijven buiten het model, om dezelfde reden als bij de verdringingsreeks — wij
kennen ze niet, en een verzonnen weging is erger dan een gemelde afruil. Geen belofte van
netwerkbrede optimalisatie: fase C bestaat alleen als A en B hem nodig maken. En geen
herziening van de rekenkern: elke cel van elk vlak in dit document is de bestaande
`optimize`, ongewijzigd.
