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

Onderweg bleek dat twee comments onder issue #37 — Mattijns vraag naar
overschrijdingsfrequentielijnen en Tons zaagtandverloop van het risico in de tijd — geen
zijsporen zijn maar de twee sluitstukken van ditzelfde ontwerp: de lijn is de uitleg van
één pakket (§6), de tijdas is de film waarvan het kostenvlak één beeld is (§7). Ze staan
hieronder ingewerkt.

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

## 2. Het centrale ontwerp: één kostenvlak, zes aflezingen

Laat T_nat en T_droog over hun roosters lopen en reken per combinatie het goedkoopste
pakket uit:

    kosten(T_nat, T_droog),  met per cel het pakket, de band, en de near-optimale set

Elke cel is één `optimize`-aanroep, en die kost — **gemeten op 2026-08-29, via de
testsuite** — 4 tot 10 seconden, afhankelijk van het aantal eisen en of er een droogte
wordt doorgerekend. (Een eerdere versie van deze verkenning zei "secondenwerk" voor het
hele vlak, geëxtrapoleerd uit de 0,06 ms per doorrekening; dat was een aanname en hij
was fout — de zoeker eromheen kost vijf ordes meer.) Een rooster van 6 × 8 cellen is
sequentieel dus **minutenwerk**, en dat heeft drie ontwerpgevolgen: het standaardrooster
is klein (3 × 3 rond het gevraagde niveau, verfijnen op verzoek), de cellen zijn
onafhankelijk en horen parallel gerekend en per gebied gecachet, en voor de vlakvraag
is de MCP Tasks-extensie — die §2 van het externe ijkpunt voor de púntvraag terecht
afwees — wel degelijk te heroverwegen. Geen nieuwe optimalisator, geen convergentievraag
die er nog niet was; wel een latentie die eerlijk in de tooldescription hoort.

Op dat ene vlak zijn alle gestelde vragen een aflezing:

| vraag | aflezing |
|---|---|
| "wat kost bescherming (50, 50)?" | één cel — dit is fase 1, de pakketzoeker |
| "wat koopt €10 mln?" | de iso-kostenlijn: alle (T_nat, T_droog) met kosten ≤ budget |
| "is T=50 verstandig, of is T=25 bijna even duur?" | de stapkosten langs een as — prijs-kwaliteit, §3 |
| "wat levert het op dat één maatregel beide assen dient?" | de synergiewinst per cel — meekoppelen, §4a |
| "waar hebben we geen spijt van?" | de rol van elke maatregel óver het vlak — §4b |
| "welke wezenlijk verschillende pakketten zijn er voor dit geld?" | de near-optimale set in de budgetcellen — §5 |
| "waar komt de bescherming van dít pakket vandaan?" | de frequentielijn per pakket — §6 |
| "en hoe houdt dit pakket zich over de beleidshorizon?" | de tijdas: het zaagtandverloop — §7 |

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
nieuwe stukje code. Eén voorbehoud, en §5.2 lost het op: deze rollen zijn zo sterk als de
verzameling pakketten waarover ze zijn uitgesproken — pas met de actieve MGA-verkenning
van §5.1 is FORCED een uitspraak over de hele romp in plaats van over de gevonden
pakketten.

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

## 5. Verschillende pakketten voor dezelfde euro's: MGA met maximaal bereik

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

### 5.1 Van passief naar actief: de alternatieven die de enumeratie toevallig vond zijn niet genoeg

Wat er nu staat is Modelling to Generate Alternatives in zijn passieve vorm:
`distinct_answers` ontdubbelt de pakketten die de mix-enumeratie **toevallig tegenkwam**
op weg naar het optimum, en `ranges_of` geeft per maatregel een coördinaatsgewijs
interval waarvan de eigen docstring zegt dat het een ondergrens is. Dat is eerlijk, maar
het is niet het bereik. De vraag van een bestuurder is de actieve vorm: *"laat mij de
volle breedte zien van wat verdedigbaar is, ook de hoeken waar de goedkoopste route
nooit langskwam."*

Die actieve vorm is een gevestigde methode — **MGA met maximaal bereik**, uit de
literatuur die `switch_price_of` al citeert: Brill e.a. (1982) formuleerden het
Hop-Skip-Jump-schema (minimaliseer telkens de inzet van maatregelen uit de vorige
antwoorden, binnen de kostenmarge), DeCarolis (2011) bracht het naar
energiesysteemmodellen, en Neumann & Brown (2021) brachten de **near-optimale ruimte
zelf** in kaart — niet één alternatief maar de vorm van het hele gebied. Dat laatste is
precies "de echte romp" die `ranges_of` in zijn docstring als volgende stap aankondigt.

Op deze rekenkern is het geen nieuwe machinerie maar een ander doel op dezelfde SLSQP:

1. **De randen van de romp.** Per maatregel: maximaliseer én minimaliseer zijn inzet,
   onder de eisen en binnen het budget (het bestaande, model-eigen
   `best.cost × (1 + cost_epsilon)`). Twee runs per maatregel per near-optimale mix —
   en anders dan bij `ranges_of` mogen de andere maatregelen meebewegen, dus dit ís de
   projectie, geen ondergrens.
2. **De maximaal verschillende pakketten (HSJ).** Herhaald: zoek het goedkoopste pakket
   dat de tot nu toe gebruikte maatregelen zo min mogelijk inzet; stop wanneer er niets
   wezenlijk nieuws meer verschijnt. Dat levert de hoeken van het gebied — het pakket
   zonder gemaal, het pakket zonder grondverwerving — die de kostengedreven enumeratie
   nooit als antwoord aanwijst maar die voor draagvlak, grondposities en meekoppeling
   (§4c) juist de interessante kandidaten zijn.

En bij vijf continue dimensies is dit géén benadering zoals in de energiemodellen, waar
de romp bij honderden dimensies geschetst moet worden: hier kan hij vrijwel uitputtend.
De kleine dimensie van de vuistregelwereld is hier een kracht, geen beperking.

### 5.2 Waarom dit dragend is en geen extraatje

Drie redenen om dit prominent te bouwen en niet uit te stellen:

* **Het maakt de no-regret-uitspraak hard.** FORCED uit §4b betekent nu "zat in elk
  pakket dat de enumeratie vond". Na de actieve verkenning betekent het "zat in elk
  pakket in de uitputtend verkende romp" — en pas dán draagt de uitspraak "hier is geen
  keuze" het gewicht dat een bestuurder eraan zal hangen.
* **Het is de eerlijke vorm van "het beste pakket".** §0 stelt dat het model de weging
  tussen de assen niet invult; dan moet het wel de volle keuzeruimte laten zien waarin
  die weging gemaakt wordt. Eén optimum plus toevallige buren is een verkapte keuze —
  de route die het optimum vond bepaalt dan stilzwijgend welke alternatieven zichtbaar
  zijn.
* **De prijs is bekend en draaglijk.** Orde tien extra SLSQP-runs per near-optimale mix
  plus een handvol HSJ-iteraties: een verveelvoudiging van de 4–10 s van één cel. Voor
  de puntvraag is dat een detail-aflezing ("verken de alternatieven"); op het vlak
  alleen in de budgetcellen, niet in alle 48.

De uitvoer verandert niet van vorm — samenstelling, band en rol per pakket, zoals
hierboven — alleen de verzameling waarover die uitspraken gaan wordt volledig in plaats
van toevallig.

---

## 6. De overschrijdingsfrequentielijn: één pakket, uitgelegd over de herhaaltijden

Mattijns vraag onder issue #37 — *"uitleg van de maatregelen in voorgestelde
maatregelenpakketten via overschrijdingsfrequentielijnen, zodat je de bijdrage van de
verschillende maatregelen gekwantificeerd over de terugkeertijden inzichtelijk krijgt"* —
is de transponering van het kostenvlak, en hij is goedkoper dan alles hierboven.

Het vlak van §2 veegt per beschermingsniveau over de **pakketten** (elke cel een
optimalisatie). De frequentielijn veegt per pakket over de **herhaaltijden**: houd het
pakket vast, laat T lopen, en teken wat er gebeurt —

    nat:   dh_max(T)      tegen de inundatienorm
    droog: shortfall(T)   tegen de tekortnorm

Elke punt is één `simulate`-aanroep van 0,06 ms; een hele lijn is millisecondenwerk —
hier geldt de extrapolatie wél, want er zit geen zoeker omheen. Het
**beschermingsniveau van het pakket is het snijpunt van de lijn met de norm** — daarmee
zijn §2 en §6 elkaars transponering: het vlak zegt wat elk niveau kost, de lijn zegt welk
niveau dít pakket haalt, en beide komen uit dezelfde veegmachinerie (`explore.py`).

**De bijdrage per maatregel vraagt één eerlijke conventie.** Maatregelen zijn niet
additief — `DEFAULT_ACTIONS` waarschuwt zelf dat bergen het landoppervlak verandert waar
vasthouden zijn fractie tegen rekent — dus "de bijdrage van bergen" bestaat alleen ten
opzichte van een volgorde. Het voorstel: teken de lijnen **incrementeel in de vaste
actievolgorde** (de trits, met de peil- en aanvoerkant erachter, zoals `_apply_all` al
rekent), en meld die conventie in de uitvoer. Dan is per maatregel zichtbaar over welke
herhaaltijden hij werkt — vasthouden helpt bij de kleine T's en verzadigt, het gemaal
draagt door tot de staart — en dat is precies de gevraagde kwantificering. De
volgorde-onafhankelijke uitspraak bestaat óók al en heet §4a: de synergiewinst.

Dit wordt géén derde tool. De lijn is de uitleg van een antwoord dat er al is: de
detail-uitvoer van de puntvraag levert hem voor het gekozen pakket, de vlakvraag per
budgetcel. En hij maakt §3 zichtbaar: het knikpunt in de stapkosten valt samen met de
plek waar de lijn van de ene maatregel verzadigt en de volgende het overneemt.

---

## 7. De tijdas: het zaagtandverloop en het investeringspad

Tons antwoord onder issue #37 zet de vraag waar hij thuishoort: niet "welk pakket bij
deze bui" maar **een verloop van het risico over de beleidshorizon, waarbij de norm op
geen enkel moment overschreden wordt**. Condities verschuiven geleidelijk (klimaat,
onderhoud, bodemdaling), een maatregel zet het risico instantaan terug: een zaagtand. En
met discontovoet, jaarlijkse verwachte schade en maatregelkosten wordt het zetten van
maatregelen in de tijd een contant-gemaakte optimalisatie van het investeringspad.

Dat is geen nieuw vlak — het is **dezelfde film waarvan §2 één beeld is**, en de frames
bestaan aan de droge kant al: de droogtestatistiek draagt de klimaatscenario-as
(`Referentie`, `Hd_2050`, `Hd_2100`, ...) als eersteklas invoer. Het kostenvlak per
scenario is het kostenvlak van dat tijdvak. De natte as heeft die laag nog niet (STOWA
2019 is huidig klimaat) en vraagt een klimaatfactor — dat is een databehoefte, geen
modelverbouwing.

Het zaagtandverloop volgt dan zonder schadefunctie, in de **normvariant**: per frame
zakt het haalbare beschermingsniveau van een vast pakket (het snijpunt uit §6 schuift
naar links), en een maatregel op tijdstip t springt het terug. De eis "norm nooit
overschreden over de horizon" plus geminimaliseerde contante kosten is het klassieke
Nederlandse investeringsprobleem — Van Dantzig (1956) voor de dijkhoogte, Eijgenraam
e.a. (2014, INFORMS Edelman Award) voor de normstelling — hier met een pakketzoeker per
frame in plaats van één dijkmaatregel. Bij een handvol maatregelmomenten en een handvol
frames is dat dynamisch programmeren over de vlak-frames: enumerabel, navolgbaar, geen
RL — de conclusie van issue #37 §7.1 ("eerder SDDP dan deep RL"), hier nog een slag
eenvoudiger zolang de scenario's deterministische frames zijn.

**En de eurovariant is precies waar §6 en Tons vraag elkaar completeren.** Jaarlijkse
verwachte schade is de frequentielijn geïntegreerd tegen een schadecurve:

    risico(pakket, frame) = ∫ schade(h) dP(h)   met P uit de frequentielijn van §6

Het model draagt de kanszijde — dat is de lijn, en die is er. De **schadezijde blijft
externe invoer**: een schadecurve per gebied, aangeleverd en met bron, nooit verzonnen.
Dat is dezelfde discipline als §0 (geen stille weging) en als issue #37 §5 (geen
verzonnen beloning; `switch_price_of` leest grenzen af in plaats van prijzen aan te
nemen). Wie de curve levert, krijgt het contant gemaakte investeringspad; wie hem niet
levert, krijgt de normvariant — en beide zijn eerlijk.

### 7.1 De discontovoet: één invoer, twee vormen, en een omslagwaarde als antwoord

Bij een horizon van vijftig tot honderd jaar is de discontovoet niet een parameter maar
dé knop: hij bepaalt of uitstellen loont, en daarmee de hele vorm van het pad. HKV heeft
hier huiswerk liggen dat dit ontwerp moet erven: OptimaliseRing (Matthijs Duits, later
gemoderniseerd door Bob Maaskant) implementeerde het Eijgenraam-model met **twee vormen
van de discontovoet**, en dat onderscheid is wezenlijk:

* de **kostenkant** wordt contant gemaakt tegen de reële discontovoet δ;
* de **schadekant** groeit ondertussen mee met de economie (het schadepotentieel achter
  de kering wordt elk jaar meer waard), zodat de verwachte schade effectief tegen δ − γ
  wordt gedisconteerd — een lagere voet, en juist die asymmetrie drijft het klassieke
  resultaat dat veiligheidsinvesteringen naar voren schuiven.

(De rijksbrede Werkgroep Discontovoet kent daarnaast het onderscheid risicovrij versus
met risico-opslag; welk van de twee onderscheiden Matthijs bedoelde is na te vragen,
maar beide pleiten voor dezelfde ontwerpregel hieronder.)

Drie ontwerpregels volgen, en ze zijn alle drie de bestaande huisdiscipline:

1. **De discontovoet is invoer met bron en peiljaar**, in het `UnitCost`-patroon: een
   getal, waar het vandaan komt, en van welk jaar. Nooit een stil default in de code.
   Dat dit geen theoretische zorg is bewijst het jaar zelf: de Werkgroep discontovoet
   heeft op 19 september 2025 een nieuw advies uitgebracht (kabinetsreactie 31 oktober
   2025, alle aanbevelingen overgenomen) met een andere opbouw — risicovrije voet 0,0 %
   plus risicopremie 2,8 %, korte termijn omhoog en lange termijn omlaag. Juist die
   **termijnstructuur** (een voet die met de horizon daalt) doet er bij vijftig tot
   honderd jaar zaagtand toe, en een model met één vaste voet als aanname had hem
   gemist.
2. **De tweede vorm wordt niet ín een voet gebakken maar uiteengelegd.** Geen δ − γ als
   invoer, maar δ als voet plus de groei van het schadepotentieel expliciet in de
   schadecurve-frames — naast de klimaatdrift die al in de kanszijde-frames zit (§7).
   Dan is de effectieve schadediscontering een **gevolg dat het model laat zien**, geen
   aanname die erin verstopt zit, en zijn de twee drivers (economie en klimaat) apart
   aanwijsbaar in plaats van opgeteld in één getal.
3. **De omslag-discontovoet als aflezing.** Over de hoogte van δ wordt eeuwig gestreden;
   het model hoeft die strijd niet te beslechten. Net als `switch_price_of` de prijs
   afleest waarbij het pakket kantelt, leest het pad-model de δ af waarbij het
   investeringspad kantelt: *"onder 2,1 % bouwt u de berging nu, erboven stelt u hem een
   frame uit."* Ligt het vigerende advies ver van die omslagwaarde, dan is de discussie
   over decimalen irrelevant voor het besluit — en dat is voor een bestuurder een
   waardevoller antwoord dan een NCW met vier cijfers.

**Verificatiestatus, omdat dit hoofdstuk deels op instituutsgeheugen rust:** het
Werkgroep-advies 2025 en de kabinetsreactie zijn geverifieerd (rijksoverheid.nl);
Dupuits' systeemwerking-bevinding is geverifieerd op de publicatietitel
(*Economically efficient flood protection levels: effects of system interdependencies*,
TU Delft). Dat OptimaliseRing de kosten- en schadekant met verschillende voeten
disconteerde is een **aanname op basis van de Eijgenraam-lijn die het implementeerde**,
geen gecontroleerd feit — navragen bij Matthijs of Bob, samen met de vraag waar de
gemoderniseerde code leeft (niet op de GitHub-organisatie, dat is gecontroleerd).

En het promotieonderzoek van Guy Dupuits (TU Delft, economische optimalisatie van
keringen als systeem) levert de externe bevestiging van §8: zijn bevinding dat de
**systeemwerking** de moeilijkheid is — afhankelijke keringen maken de economische
optimalisatie niet-scheidbaar per object — is exact het argument waarom het netwerk
hier gefaseerd gaat (per gebied optimaliseren en op het netwerk tóetsen, pas koppelen
als dat aantoonbaar moet). Concreet actiepunt bij dit alles: Bobs modernisering van
OptimaliseRing staat niet op de GitHub-organisatie (gecontroleerd); vraag hem ernaar,
want als die code er nog is, zijn de doorgerekende zaagtandcasussen de ankertests
waartegen het DP-pad uit dit hoofdstuk zich moet bewijzen.

Twee dingen horen er verder expliciet bij. Ten eerste de drivers: klimaat zit in de frames;
veroudering van kunstwerken is als hypothese in te voeren (een lagere capaciteit is een
gewone toestandswijziging); bodemdaling en faalkansen zitten níet in de kern en horen
per studie als aanname op tafel. Ten tweede Tons herformulering die het ontwerp
vereenvoudigt: *"een wijziging van het netwerk of een andere operationele besturing zijn
in onze tool hetzelfde — een maatregel."* Dat betekent dat de tijdas geen nieuwe
actiesoorten vraagt maar een uitbreidbare **maatregelcatalogus**: de vijf acties van nu,
en morgen een verbinding of een regelregel als zesde en zevende, elk met `apply`, een
bereik en een prijs(band). De volgorde-vraag van issue #37 §7.2/§7.3 wordt daarmee een
catalogusvraag, geen algoritmevraag.

---

## 8. Het netwerk: waarom de pakketzoeker één gebied ziet, en de weg erheen

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

## 9. Tools en namen

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
   budget is, stapkosten en knikpunten, synergiewinst, no-regret-lijst, en in de
   budgetcellen de actief verkende alternatieven van §5 — de randen van de romp en de
   maximaal verschillende pakketten, niet alleen de toevallig gevondene). Voorstel: **`explore_protection_given_budget`**, waarbij het budget
   weglaatbaar is — zonder budget is het antwoord het vlak zelf.

De naamgeving is uitdrukkelijk een open punt (zo is hij ook in het gesprek gemarkeerd);
het besluit hoort te vallen wanneer de `read_me`-module wordt geschreven, want de naam en
de handleiding zijn samen de interface. Wat wél vastligt: het worden er **twee en niet
vijf** — de aflezingen van §3 t/m §6 zijn uitvoer van de punt- of de vlakvraag, geen eigen tools —
en de budgetvraag krijgt geen eigen "beste pakket"-knop die de ontbrekende weging stil
zou invullen.

Voor de agent is de taakverdeling dan uit te leggen in één zin per tool: *weet u wat u
wilt halen → de puntvraag; wilt u weten wat halen kost of wat uw geld koopt → de
vlakvraag.* De openingsvraag van dit document is vlakvraag met budget, en het antwoord
is: de iso-lijn, de knikpunten eromheen, de no-regret-lijst, en de wezenlijk
verschillende pakketten binnen de €10 mln — mét de melding welke daarvan binnen de
prijsband niet te onderscheiden zijn.

---

## 10. Volgorde

0. **Het productbesluit uit issue #37 valt eerst.** Mattijns vraag aan Ton — bedient
   het screening-product de regio-trede die er al is, of duwt de brainstorm naar
   stroomgebied- en landschaal — staat nog open, en het antwoord bepaalt hoeveel van
   deze ladder er ooit gebouwd wordt. Deze verkenning is de ladder; zij is geen
   argument om hem te beklimmen. Tons zaagtand-antwoord geeft de richting (§7), maar
   de trede is niet gekozen.
1. **Fase 1 zoals gepland** (`PLAN_PAKKETZOEKER_ALS_TOOL.md`), met de hernoeming uit §9.
2. **De veeg als bibliotheekfunctie** (`explore.py` naast `optimize.py`): het vlak, de
   frequentielijnen (§6), de stapkosten, de synergiewinst, de rol-aggregatie én de
   actieve MGA-verkenning van §5.1 — de randen van de romp en het HSJ-schema — met de
   consistentietoets uit §4a in de tests, plus de toets dat elk MGA-alternatief zelf
   aan de eisen en het budget voldoet. Nog geen tool — eerst laten zien dat de
   aflezingen kloppen op de referentiecasus.
3. **De vlakvraag als tool**, met de uitvoerdiscipline uit §2 (banden, onderscheidbaarheid)
   en §5 (samenstelling is model, duiding is tekst).
4. **Prijsscenario's en de gegeneraliseerde omslagprijs** (§4c).
5. **De tijdas in de normvariant** (§7): de vlak-frames per klimaatscenario en het
   DP-pad erover, met de natte klimaatfactor als databehoefte ernaast; de eurovariant
   pas wanneer een gebied een schadecurve mét bron levert.
6. **Netwerk fase A**, en pas daarna B — elk met de toetsvraag vooraf of de vorige fase
   koppelingsfouten liet zien die het antwoord veranderen.

---

## 11. Wat deze verkenning niet is

Geen maatschappelijke kosten-batenanalyse uit eigen koker: schadefuncties en de
waardering van droog tegen nat blijven buiten het model, om dezelfde reden als bij de
verdringingsreeks — wij kennen ze niet, en een verzonnen weging is erger dan een gemelde
afruil. Het model levert wel de kanszijde (de frequentielijn van §6); een aangeleverde
schadecurve mét bron maakt daar risico van (§7), maar het model verzint er nooit zelf
een. Geen belofte van
netwerkbrede optimalisatie: fase C bestaat alleen als A en B hem nodig maken. En geen
herziening van de rekenkern: elke cel van elk vlak in dit document is de bestaande
`optimize`, ongewijzigd.
