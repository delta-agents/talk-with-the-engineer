# Plan van aanpak — de bergingscoëfficiënt en het grondwater aan de aanvoerkant

Versie 1 · 27 augustus 2026 · **voorstel, nog niet gebouwd**

Dit document sluit aan op `PLAN_DROOGTE_EIS_ALS_WATERSTAND.md` (de droogte-eis als
waterstand) en hoort bij
[issue #55](https://github.com/HKV-products-services/talk-with-the-engineer/issues/55).
Het beantwoordt de vraag uit de terugkoppeling van augustus 2026:

> Aanvoeren is o.a. gebaseerd op de buffer, maar op welke manier kunnen we dit uitbreiden
> met wat we tot de beschikking hebben qua grondwater? Grondwater heeft een vertraging van
> dagen tot weken.

Er staat in dit document **geen** code die al gebouwd is. Wat er wel staat is de
uitwerking, met de getallen die de keuze dragen, zodat de bouwbeslissing genomen kan worden
op iets anders dan een intuïtie.

---

## 0. Eerst het misverstand uit de weg: dit staat los van de 20 mm

De bergingscoëfficiënt en het zomerse neerslagverlies van 20 mm zijn twee verschillende
dingen, en ze zijn eerder door elkaar gelopen.

| | het neerslagverlies | de bergingscoëfficiënt |
|---|---|---|
| wat het is | neerslag die vanaf het OPPERVLAK niet tot afvoer komt | hoeveel voorraad een meter GRONDWATERstandsdaling vrijmaakt |
| grootheid | een hoeveelheid [mm] per bui | een dimensieloze fractie [-] |
| kant van het model | de natte kant, wateroverlast | de droge kant, watertekort |
| zit vandaag in het model | ja, als vaste 20 mm | nee, helemaal niet |

Beide zijn een **eigenschap van het gebied** en niet van de bui, en dat is het enige wat ze
delen. Een eerdere versie van `utils_rainfall.py` leidde de 20 mm af uit "300 mm freatische
berging maal een bergingscoëfficiënt van 0,04 plus 8 mm verdamping". Die afleiding is
vervallen: ze suggereerde dat het verlies een grondwatergrootheid is, en daarmee dat het
tweemaal geteld zou worden zodra het grondwater er echt in komt. Bevestigd in de
terugkoppeling van augustus 2026.

Wat er in die terugkoppeling over het neerslagverlies zelf is besloten, is al doorgevoerd:
de caveat heet nu `neerslagverlies van dit gebied`, zegt dat het een eigenschap van het
gebied is en niet van de bui, en zegt er expliciet bij dat het niet de bergingscoëfficiënt
is. Zie `SUMMER_LOSS_MM` in `utils_rainfall.py`.

**Voor dit plan betekent dat: het grondwater komt er als een nieuwe term bij, niet als een
herinterpretatie van een bestaande.** Er is niets dat dubbel geteld kan worden.

---

## 1. Wat de buffer vandaag is, en hoe klein hij is

`simulate_deficit` kent één voorraad: de berging onder het streefpeil in het **open water**.
De bufferdiepte is `level_margin_m + target_level_rise_m`, aan de toolgrens
`drawdown_available_m`, en de voorraad die daarbij hoort is

    buffer_mm = drawdown_available_m × (open water / totaal oppervlak) × 1000

Op de referentiepolder — 4000 ha, 3,5 % open water, 30 cm bruikbare uitzakking — is dat
**10,5 mm** over de polder. Dat is het volledige antwoord op de vraag "wat heeft dit gebied
zelf".

Tien millimeter is bij een tekort van 1,5 mm/dag zeven dagen, en bij 4 mm/dag nog geen drie.
Op een droogte die 183 dagen duurt is dat een rondingsfout. De tool zegt dat ook eerlijk —
`_no_groundwater_caveat` meldt dat bodemvocht en grondwater er niet in zitten en dat het
antwoord "voor gebieden met weinig open water een ondergrens is" — maar een caveat is een
mededeling en geen getal, en de pakketzoeker kan er niets mee.

---

## 2. Wat het grondwater eraan toevoegt

### 2.1 De voorraad

De bergingscoëfficiënt μ (freatische bergingscoëfficiënt, `bergingscoëfficiënt` in
NL-vaktaal) zegt hoeveel water er vrijkomt per meter grondwaterstandsdaling per m² land.
Zand ligt rond 0,10–0,20, klei rond 0,03–0,08, veen rond 0,02–0,10 met grote spreiding.

    grondwatervoorraad_mm = μ × zakking_m × (land / totaal oppervlak) × 1000

Voor dezelfde referentiepolder, in mm over de polder:

| μ | 0,15 m zakking | 0,30 m | 0,50 m |
|---|---|---|---|
| 0,02 | 2,9 mm | 5,8 mm | 9,7 mm |
| 0,05 | 7,2 mm | 14,5 mm | 24,1 mm |
| 0,10 | 14,5 mm | 28,9 mm | 48,2 mm |
| 0,15 | 21,7 mm | 43,4 mm | 72,4 mm |

Ter vergelijking: de open-waterbuffer is 10,5 mm. **Het grondwater is bij realistische
waarden een factor 1 tot 7 groter dan de hele voorraad die het model vandaag kent.** Dat is
de reden dat deze uitbreiding de moeite waard is, en tegelijk de reden dat hij niet
lichtvaardig moet: hij verandert het antwoord van deze tools substantieel.

### 2.2 De vertraging — en waarom die de kant op werkt die je niet verwacht

De vertraging zit **niet** tussen het gewas en de bodem. Een gewas dat verdampt trekt
onmiddellijk aan het bodemvocht; daar zit geen weerstand tussen. De vertraging zit tussen
**de sloot en de bodem**: water dat je inlaat staat in de watergang en moet van daaruit de
bodem in sijpelen, tegen de drainageweerstand γ [dagen] in.

    q [m/d] = (h_slootpeil − h_grondwater) / γ

Dat is de drainagerelatie in de gebruikelijke vorm, met het teken omgedraaid: in de zomer
loopt hij van de sloot naar het land in plaats van andersom (subinfiltratie). De
responstijd van de bak is τ = μ · γ, en dat is het getal dat "dagen tot weken" oplevert:
bij μ = 0,05 en γ = 250 d is τ = 12 dagen, bij μ = 0,15 en γ = 100 d is τ = 15 dagen.

**De consequentie is scherper dan een vertraging.** Zet die relatie om in een debiet, dan
is er een BOVENGRENS aan wat de sloot per dag de bodem in kan krijgen, en die hangt alleen
af van de opbolling en de weerstand:

| opbolling | γ = 50 d | γ = 100 d | γ = 250 d | γ = 500 d |
|---|---|---|---|---|
| 0,15 m | 3,00 mm/d | 1,50 mm/d | 0,60 mm/d | 0,30 mm/d |
| 0,30 m | 6,00 mm/d | 3,00 mm/d | 1,20 mm/d | 0,60 mm/d |
| 0,50 m | 10,00 mm/d | 5,00 mm/d | 2,00 mm/d | 1,00 mm/d |

En het tekort dat gedekt moet worden ligt op:

* 1,47 mm/d — Rijn en IJssel, Referentie, T10, over het groeiseizoen;
* 2,98 mm/d — hetzelfde volume geconcentreerd over 90 dagen;
* 4,00 mm/d — een warme maand die de beller zelf opgeeft.

**Die twee reeksen overlappen.** Bij γ = 250 d haalt de sloot 1,2 mm/d de bodem in en is
het tekort 1,5 mm/d: dan is de drainageweerstand de bindende beperking en niet de inlaat.
Een grotere inlaat helpt daar niets — precies hetzelfde onderscheid dat
`calculate_allocation_given_shortage` maakt tussen "de bron is de klem" en "de inlaten zijn
de klem", maar dan een schaal lager en binnen één gebied.

Dat is het inhoudelijke antwoord op de vraag uit de terugkoppeling: het grondwater
meenemen voegt niet alleen een grotere buffer toe, het voegt ook een **derde klem** toe die
er nu helemaal niet is en die in een deel van Nederland de maatgevende is.

---

## 3. Het voorstel: twee gekoppelde bakken

### 3.1 De vergelijkingen

Twee toestandsvariabelen in plaats van één. Alles per m² van het betreffende oppervlak,
met `f_ow` en `f_land` de oppervlaktefracties:

    uitwisseling      q = (h_ow − h_gw) / γ                    [m/d], positief = sloot → bodem

    grondwater        μ · dh_gw/dt = −D + q                    geklemd op [−z_gw, 0]
    open water        dh_ow/dt = Q_in/A_ow − D − (f_land/f_ow)·q   geklemd op [−z_ow, 0]

waarin `D` het neerslagtekort is, `z_ow` de toegestane uitzakking in de sloot
(`drawdown_available_m`, zoals nu) en `z_gw` de toegestane grondwaterstandsdaling.

Loopt het grondwater tegen zijn ondergrens aan, dan slaat de resterende gewasvraag door
naar het open water: het gewas trekt dan aan de sloot in plaats van aan de bodem. Dat is de
huidige situatie, en daarmee is de bestaande formulering het **limietgeval** van deze.

### 3.2 De twee limieten, en waarom die de acceptatietoets zijn

Deze vorm is te vertrouwen omdat hij aan beide uiteinden overgaat in iets wat we al kennen:

* **γ → ∞** (geen enkele uitwisseling): het grondwater doet niets, en het antwoord is exact
  het antwoord van vandaag. Regressie op alle bestaande toetsen moet bit voor bit kloppen.
* **γ → 0** (oneindig snelle uitwisseling): de twee bakken staan altijd gelijk en gedragen
  zich als één bak met een bergend oppervlak `A_ow + μ·A_land`. Dat is analytisch
  uitrekenbaar en dus een exacte toets, geen "ziet er plausibel uit".

Beide limieten zijn goedkoop te testen en samen leggen ze de implementatie vast. Dat is de
reden dat dit voorstel de twee bakken kiest boven de simpelere variant hieronder.

### 3.3 De variant die is afgevallen

De verleidelijke één-regel-implementatie is: vervang in `simulate_deficit` het
open-wateroppervlak door `A_ow + μ·A_land` en klaar. Dat is precies de γ → 0 limiet, en het
is **fout op de manier die de terugkoppeling benoemde**: het maakt het grondwater
onmiddellijk beschikbaar, terwijl de vertraging van dagen tot weken juist het punt is. Op
een tekort van 30 dagen zou die variant een voorraad meetellen die er in die 30 dagen
helemaal niet uit te halen is.

Hij blijft wel nuttig, maar als toets (§3.2) en niet als model.

---

## 4. Wat er aan de toolgrens verandert

### 4.1 Drie velden, samen of geen van drie

Dezelfde vorm als het droogtetripel in `DroughtStatisticInput.require_the_whole_triple`:
half een grondwatersysteem beschrijven bestaat niet.

| veld | eenheid | bandbreedte | wat het is |
|---|---|---|---|
| `storage_coefficient` | – | 0,02–0,20 | de bergingscoëfficiënt μ van dit gebied |
| `drainage_resistance_days` | dagen | 50–500 | de drainageweerstand γ |
| `groundwater_drawdown_available_m` | m | 0,1–0,8 | hoe ver de grondwaterstand mag zakken |

Alle drie **zonder standaardwaarde**, om dezelfde reden als bij `percentage_open_water` en
`delta_h_available`: het zijn gebiedseigenschappen die de uitkomst hard sturen, en een
landelijk gemiddelde is voor de meeste gebieden het verkeerde getal. Laat de beller ze weg,
dan blijft het model exact wat het vandaag is en blijft `_no_groundwater_caveat` staan.
**De uitbreiding is dus opt-in en breekt niets.**

Waarom γ als invoer en τ als uitvoer: de drainageweerstand is de grootheid die een
waterschap in zijn modellen heeft staan, de responstijd is de grootheid die het gedrag
uitlegt. Invoer in wat je hebt, terugkoppeling in wat het betekent — dezelfde splitsing als
bij de buiduur in uren en de terugkoppeling in dagen.

`groundwater_drawdown_available_m` is een **andere** grens dan `drawdown_available_m`, en
dat verschil is de moeite van een apart veld waard: de sloot mag zakken tot er
scheepvaart-, oever- of kadeschade optreedt, het grondwater tot er gewasschade of
maaivelddaling optreedt. In veenweide is de tweede veel strenger dan de eerste, en op
zandgrond andersom.

### 4.2 Wat er uit komt

Naast de bestaande velden:

| veld | wat het zegt |
|---|---|
| `groundwater_buffer_mm` | de hele voorraad die de toegestane zakking vrijmaakt |
| `groundwater_buffer_used_mm` | wat daarvan in DEZE periode werkelijk is aangesproken |
| `groundwater_response_days` | τ = μ·γ, de responstijd die het gedrag verklaart |
| `max_infiltration_mm_per_day` | de bovengrens uit §2.2, bij de opgegeven opbolling |
| `binding_is_resistance_not_capacity` | true als de weerstand knelt en niet de inlaat |

Het verschil tussen de eerste twee **is** de vertraging, uitgedrukt in het getal waar het om
gaat. Het laatste veld is de derde klem uit §2.2, in dezelfde vorm als
`binding_is_capacity_not_availability` op de verdelingstool — één vocabulaire voor hetzelfde
soort uitspraak.

### 4.3 Wat er aan bestaande velden verandert

* `buffer_mm` blijft **exact wat het is**: de open-waterbuffer. Er komt een veld naast, er
  wordt er geen herdefinieerd. Een veld dat stil van betekenis verandert is erger dan een
  veld erbij.
* `days_until_buffer_empty` idem, met `days_until_groundwater_empty` ernaast.
* `_no_groundwater_caveat` wordt **conditioneel**: hij gaat alleen nog af zolang de drie
  velden ontbreken. Staan ze er, dan komt er een andere caveat voor in de plaats, over wat
  er dan nog steeds niet in zit (§7).

---

## 5. Waar de getallen vandaan moeten komen

Dit is het punt waarop dit plan het minst hard is, en dat hoort er te staan.

* **μ** — de bodemkaart geeft een textuurklasse, en daar hangt een bandbreedte aan die
  breder is dan de waarde zelf. Een gebied met "klei" kan van 0,03 tot 0,08 lopen, dus
  ruwweg een factor drie. Dat hoort in `sensitivity` en niet in een puntwaarde.
* **γ** — komt uit een bestaand grondwatermodel of uit de drainageformules van de
  ontwerpnorm. Waterschappen hebben dit, maar niet in dezelfde vorm en niet altijd voor de
  infiltratierichting; de weerstand is in de zomer aantoonbaar hóger dan in de winter,
  omdat de slootbodem dichtslibt. Voorstel: γ als invoer accepteren zoals hij is en in een
  caveat benoemen dat de infiltratierichting een andere weerstand heeft dan de
  drainagerichting, met de richting erbij (te gunstig).
* **z_gw** — geen meetwaarde maar een beleidskeuze, net als `drawdown_available_m`. Hoort
  dus als vraag aan de beheerder gesteld te worden en niet uit een tabel te komen.

**Voorstel voor de eerste versie:** geen van deze drie krijgt een standaardwaarde, en de
gevoeligheid over μ komt in `sensitivity` op de manier die er nu al is
(`FIELD_RANGES["storage_coefficient"] = (0.02, 0.20)`). Dan is de bandbreedte een getal in
het antwoord in plaats van een gat in de onderbouwing.

---

## 6. Toetsen

Wat er groen moet staan voordat dit gebouwd heet te zijn:

1. **regressie** — zonder de drie velden is elk bestaand antwoord bit voor bit gelijk;
2. **limiet γ → ∞** — met een absurd hoge weerstand idem;
3. **limiet γ → 0** — het antwoord is exact dat van één bak met oppervlak
   `A_ow + μ·A_land`, analytisch uitgerekend;
4. **massabalans** — `demand_mm = supplied_mm + buffer_mm + groundwater_buffer_used_mm +
   shortfall_mm`, tot 1e-9, zoals de balans op de droge kant nu al sluit;
5. **de vertraging is er echt** — bij een tekort van 30 dagen en τ = 30 dagen is
   `groundwater_buffer_used_mm` aantoonbaar kleiner dan `groundwater_buffer_mm`, en bij 183
   dagen ligt hij er dicht tegenaan;
6. **de derde klem werkt** — een geval met γ = 250 d en een tekort van 1,5 mm/d geeft
   `binding_is_resistance_not_capacity: true`, en een grotere inlaat verandert het antwoord
   dan aantoonbaar niet;
7. **half opgeven wordt geweigerd** — twee van de drie velden geeft een `ModelRetry` die
   zegt welke ontbreekt, zoals het droogtetripel dat doet;
8. **de gevoeligheidsrij over μ is nagerekend** — met dezelfde toets als
   `test_every_sensitivity_row_matches_a_real_recalculation`, want een override die de
   toestand niet bereikt is precies de klasse fouten die B3 was.

---

## 7. In scope, buiten scope

**In scope:** de twee bakken, de drie invoervelden, de vijf uitvoervelden, de caveats, en
`calculate_supply_given_h` en `_given_supply`.

**Buiten scope, en het hoort gezegd te worden dat het eruit blijft:**

* **de onverzadigde zone.** Tussen de grondwaterstand en de wortelzone zit een profiel met
  eigen vochtberging en capillaire opstijging. Dit model heeft één grondwaterstand en geen
  profiel, dus het zegt niets over of het water op de goede diepte terechtkomt;
* **maaivelddaling.** Grondwaterstandsdaling in veen is onomkeerbaar en kost bodem. Dat is
  in veenweide de belangrijkste consequentie van `groundwater_drawdown_available_m`, en het
  hoort een `priceless`-post te worden en geen getal — dezelfde behandeling als peilopzet;
* **kwel en wegzijging.** Een vaste term die per gebied verschilt en die de balans zichtbaar
  verschuift; hij hoort erbij, maar als vierde veld en niet in deze stap;
* **de winter.** De voorraad waarmee een gebied het groeiseizoen in gaat is de uitkomst van
  de voorgaande winter. Dit model start elke doorrekening op nul, dus overdracht van winter
  naar zomer zit er niet in — en dat is precies waar "sponswerking" over gaat;
* **de natte kant.** De bergingscoëfficiënt heeft ook een rol bij wateroverlast: een droge
  bodem bergt de eerste millimeters van een bui. Dat is niet dit plan, en het is niet de 20
  mm neerslagverlies (§0) — het is een derde ding, en het is de logische opvolger.

---

## 8. Volgorde

1. §3.1 in `simulate_deficit`, achter een schakelaar die uit staat zolang de drie velden
   ontbreken. Toetsen 1 tot en met 4 groen;
2. de drie invoervelden met hun weigering, en de vijf uitvoervelden. Toetsen 5 tot en met 8;
3. de caveats: `_no_groundwater_caveat` conditioneel maken, en de drie nieuwe erbij
   (infiltratierichting, onverzadigde zone, maaivelddaling als `priceless`-post);
4. `read_me` bijwerken — `bronnen` (waar μ en γ vandaan komen), `vuistregels` (de derde
   klem), `terugkoppelen` (het verschil tussen de twee buffervelden doorgeven);
5. pas daarna eventueel de pakketzoeker: zolang stap 1 tot en met 4 niet staan, is een
   grondwatermaatregel in `optimize` een maatregel zonder mechanisme.

Stap 5 is bewust laatst. De verleiding is om er meteen een maatregel van te maken
("verhoog de bergingscoëfficiënt", "verlaag de drainageweerstand"), en dat kan pas zodra
de doorrekening klopt.

---

## 9. Wat dit plan niet is

Het is geen grondwatermodel. Twee bakken met een lineaire weerstand is de kleinste vorm
waarin de vraag uit de terugkoppeling — hoeveel voorraad, en hoe snel beschikbaar —
beantwoord kan worden, en hij is met opzet zo klein dat de twee limieten uit §3.2 hem
vastpinnen. Wie een verdeling over de diepte, een onverzadigde zone of een echte
grondwaterstroming nodig heeft, heeft een ander instrument nodig en niet een vijfde veld op
dit instrument.

De winst zit niet in de precisie maar in het onderscheid: vandaag zegt de tool "je hebt
10,5 mm buffer" waar het werkelijke antwoord "10,5 mm nu en 43 mm over een paar weken" is,
en die twee leiden tot verschillende beslissingen.
