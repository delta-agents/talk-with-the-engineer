# Plan van aanpak, deel 2 — uitwisseling en netwerk

Versie 1 · 22 augustus 2026 · WP8 t/m WP11

`PLAN_TOOLS_REFACTOR.md` blijft de referentie voor WP0 t/m WP7 en voor §1 t/m §12 daarin.
Dit document begint waar dat plan ophoudt en beantwoordt twee vragen die daar als
"voorbereid, niet gebouwd" staan:

1. **Is aanvoeren dezelfde actie als afvoeren?** Deels — en het deel waar het níet zo is,
   is precies aan te wijzen. Zie §2 en §3.
2. **Hoe komt de ruimtelijke koppeling in het world model in plaats van eroverheen?** Door
   de verbinding waarmee een polder water uitwisselt tot een object in de toestand te
   maken. Dan is de cascade geen nieuwe abstractie maar dezelfde verbinding met een andere
   bestemming. Zie §5 en §6.

Aanleiding is de discussie in [issue #28](https://github.com/HKV-products-services/talk-with-the-engineer/issues/28).
Die discussie is hier verwerkt, met op drie punten een andere uitkomst; die staan als
zodanig gemarkeerd.

---

## 1. Wat hier de eis is

De keuze die in `PLAN_TOOLS_REFACTOR.md` is gemaakt — één toestand, één transitie,
maatregelen als toestandsmutatie — is gemaakt omdat hij op elke schaal geldig blijft. Dat
is een belofte, en die belofte wordt hier ingelost of hij wordt hier vals. Concreet:
"zoek een oplossing voor heel Nederland" moet dezelfde rekenkern kunnen gebruiken als
"zoek een oplossing voor deze polder van 4000 ha", en het verschil moet in de vorm van de
invoer zitten en niet in een tweede implementatie.

Drie eisen volgen daaruit, en ze zijn allemaal toetsbaar:

| eis | toets |
|---|---|
| Eén rekenkern voor nat en droog | de droogtekant gebruikt geen eigen recursie |
| Eén object voor uitwisseling en koppeling | de eenpolder-casus is het netwerk met één knoop |
| De kern schaalt over knopen en is differentieerbaar | 8500 knopen binnen een tiende seconde, gradiënt inbegrepen |

De derde eis is niet cosmetisch. Als er per knoop een aparte doorrekening nodig is om het
marginale effect van een maatregel te weten, dan kost een zoektocht over heel Nederland
het aantal knopen keer het aantal maatregelen keer het aantal scenario's aan
doorrekeningen. Met een gradiënt kost hij er één. Dat is het verschil tussen een demo en
een instrument, en het is ook precies het punt waarop de discussie in issue #28 uitkwam.

**Buiten scope**, expliciet:

| onderwerp | reden |
|---|---|
| Klimaatdrift op de statistiek | ongewijzigd buiten scope, zie deel 1 |
| Grondwater, verzilting en waterkwaliteit als toestandsvariabelen | §10 laat zien dat verzilting de aanvoercapaciteit bepaalt; dat is een randvoorwaarde en nog geen modeluitbreiding |
| Geleerde componenten (neural anything) | de dynamiek is opschrijfbaar; zie de talk §6 |
| Echte netwerkdata van een waterschap | WP10 werkt op een synthetische keten, WP11 pas op echte topologie |

---

## 2. Wat er werkelijk anders is aan aanvoeren

De vraag uit issue #28 was of aanvoeren en afvoeren dezelfde actie zijn. Het antwoord daar
was "ja, één `WaterExchangeAction` met een signed delta". Dat is voor de **transitie**
juist en voor de **rest van de tool** onjuist, en het loont om precies te zijn over welke
laag waar zit.

| | afvoeren | aanvoeren |
|---|---|---|
| **aandrijving** | een bui: neerslagoverschot in uren tot dagen | een neerslagtekort: verdamping boven neerslag, in weken tot maanden |
| **exogene reeks** | STOWA-2019 neerslagstatistiek, 48 tot 192 uur | neerslagtekort­reeks; KNMI monitort sinds 2026 jaarrond, referentielijnen mediaan en 5 % droogste jaren |
| **ordegrootte** | gemaal 1 tot 5 l/s/ha | aanvoernorm 0,3 tot 0,4 l/s/ha — een orde kleiner |
| **kunstwerk** | gemaal: energie erin, capaciteit vrijwel peil­onafhankelijk | inlaat of hevel: zwaartekracht, capaciteit hangt aan het verval en aan de boezemstand |
| **beperking** | de benedenstroomse berging (afwenteling) | de landelijke verdeling: bij tekort rantsoeneert de verdringingsreeks, en die staat buiten de polder |
| **doelfunctie** | maximale stijging onder een norm houden | het peil boven een ondergrens houden, of het benodigde volume kennen |
| **kosten** | investering in vermogen, plus energie | grotendeels de aanvoer zelf, en die is in een tekort niet te koop |

Vijf van de zeven rijen verschillen wezenlijk. Wat níet verschilt is de vierde regel van
de massabalans: er gaat water over de systeemgrens, in of uit. En dat is precies de regel
die in de rekenkern staat.

**Conclusie, en die is scherper dan "het is dezelfde actie":**

> Verenig de **transitie**. Verenig de **toestand**. Verenig de **tool niet**.

De transitie is één operator met een teken (§4). De toestand is één verbinding met twee
richtingen (§5). Maar de bui, het doel, de kostenstructuur en de randvoorwaarde zijn vier
verschillende dingen, en een tool die ze door één signed getal perst vraagt van de agent
dat hij vijf dingen tegelijk goed kiest. Dat is de omgekeerde beweging van wat WP1 t/m WP7
hebben gedaan: die hebben juist elke impliciete keuze expliciet en meldbaar gemaakt.

Praktisch: intern heet het `WaterExchange`, aan de toolgrens blijven `afvoeren` en
`aanvoeren` twee namen met elk hun eigen invoermodel — net zoals de zes bestaande tools
allemaal op dezelfde `simulate` staan en toch zes namen hebben. Het punt van de zes tools
is nooit geweest dat er zes berekeningen zijn.

### Een naad die er al ligt

`DischargeInputGivenDischarge.delta_discharge_capacity_l_s_ha` heeft als veldbeschrijving
*"Negatief mag: dat is de vraag wat er gebeurt als er capaciteit wegvalt"*, terwijl
`calculate_discharge_given_discharge` een negatieve delta met een `ModelRetry` afwijst.
De beschrijving belooft dus iets wat de tool weigert. Dat is een losse fout, en tegelijk
precies de plek waar de vraag "en wat als het de andere kant op gaat" al aan de deur
klopt. WP8 zet daar de tekening recht: capaciteit die *wegvalt* is een kleinere
`capacity_out`, en dat is iets anders dan aanvoer.

---

## 3. Wat de kern nu niet kan

Nagerekend, referentiecasus, `water_level_series` met een netto tekort van 0,5 l/s/ha en
een gemaal dat niets hoeft te doen:

```
h.min = 0,000000   h.max = 0,000000
```

De droogte is **onzichtbaar**. Dat is geen bug maar de bewuste vorm van de recursie:

```
h[0] = 0,  h[t] = max(h[t-1] + d[t], 0)
```

De afkap op nul *is* het streefpeil, en hij is eenzijdig. Alles onder het streefpeil wordt
op nul gezet, dus een tekort laat geen spoor achter. Dat verklaart ook waarom de
droogte-uitlezing in deel 1 §8.2 op `retained_volume_mm` uitkwam — een grootheid die uit
de *toestand* wordt berekend en niet uit de *reeks*. Dat was de enige uitlezing die kon,
niet de beste die er is.

Diezelfde eenzijdigheid kost aan de natte kant ook iets. Voorbemaling — het peil vóór de
bui laten uitzakken binnen de peilmarge — is niet representeerbaar, want de recursie kan
niet onder nul.

---

## 4. De kern: de tweezijdig geklemde waterbalans

### 4.1 De recursie

```
h[t] = clamp(h[t-1] + d[t], lo, hi)
```

met `lo` de laagste stand die het peilbeheer toestaat (nul in het huidige model) en `hi`
de hoogste (oneindig in het huidige model). Drie standen van één operator:

| regime | `lo` | `hi` | betekenis |
|---|---|---|---|
| wateroverlast, huidig gedrag | `0` | `+∞` | het gemaal pompt tot streefpeil en niet verder |
| watertekort | `−∞` | `0` | de inlaat vult tot streefpeil en niet verder |
| peilbeheer met marge | `−m` | `+∞` | het gemaal mag `m` meter voormalen |
| dynamisch peilbeheer | `−m` | `+p` | een bandbreedte rond het streefpeil |

Aanvoeren is dus **dezelfde functie met een gespiegelde klem**. Nagerekend, netto tekort
0,5 l/s/ha over zeven dagen op de referentiepolder:

| aanvoer | laagste stand onder streefpeil |
|---|---|
| geen | −83,4 cm |
| 0,4 l/s/ha (de aanvoernorm) | −14,3 cm |

De aanvoernorm dekt dit tekort dus niet — hij houdt het peil niet, hij vertraagt de daling.
Dat is een uitspraak die het huidige model niet kán doen, en hij volgt uit dezelfde drie
regels.

### 4.2 Waarom dit gevectoriseerd blijft: geklemde translaties vormen een monoïde

De cumsum-truc uit deel 1 §3.3 werkt alleen eenzijdig. Een tweezijdige klem heeft geen
`cumsum`-vorm, en de verleiding is dan om terug te vallen op een python-lus over de tijd.
Dat is niet nodig, en dit is het technische hart van dit document.

Beschouw de familie `f(x) = clamp(x + a, l, u)`. Die is gesloten onder compositie:

```
f₂ ∘ f₁  =  clamp( x + (a₁+a₂),  clamp(l₁+a₂, l₂, u₂),  clamp(u₁+a₂, l₂, u₂) )
```

Het element `(a, l, u)` met die compositieregel is een **associatieve** operator. Daarmee
is de recursie een *associative scan*: log-diepte in de tijd, volledig gevectoriseerd, en
differentieerbaar omdat `clamp`, `min` en `max` dat zijn. Dit is dezelfde structuur die
lineaire RNN's en state-space-modellen paralleliseerbaar maakt; de literatuur noemt het
prefix-scan over affiene recurrenties, en het geldt hier omdat een geklemde translatie een
affiene afbeelding met een begrensd bereik is.

Nagerekend tegen de bestaande kern:

| vergelijking | grootste afwijking |
|---|---|
| scan met `lo=0, hi=+∞` versus `water_level_series`, over 216 buicombinaties | 6,7·10⁻¹⁵ m |
| tweezijdige scan versus de sequentiële lus, vijf `(lo, hi)`-paren | 3,3·10⁻¹⁵ m |
| `jax.lax.associative_scan` versus de sequentiële lus | 1·10⁻⁷ m (float32) |

En er komt één afgeleide grootheid uit in plaats van twee. Definieer
`slack[t] = h[t] − (h[t−1] + d[t])`: dat is wat de klem heeft toegevoegd of weggenomen.
Daaruit volgen de weggepompte reeks, de onbenutte capaciteit, de aangevoerde reeks én de
onvervulde vraag, elk met alleen een teken en de factor `c`. Nagerekend reproduceert
`capaciteit − slack/c` de bestaande `pumped`-reeks op **1,7·10⁻¹³ m³/s**, en de massabalans
sluit op 5,6·10⁻⁹ m³ van 5,17 miljoen. De aparte `unused_capacity`-boekhouding in
`water_level_series` kan daarmee weg: één primitief, alle uitlezingen.

De bestaande truc is dus het bijzondere geval, niet een aparte methode. De gouden
regressietest tegen `TttE_v03.xlsx` op 1·10⁻¹² blijft gelden zonder één getal te
veranderen — dat is de belangrijkste eigenschap van deze stap.

> **Verschil met issue #28.** Daar staat dat de sterkste toevoeging
> "differentiability + gradients door de spatial cascade" is. Dat is waar, maar het is een
> conclusie zonder mechanisme. Het mechanisme is dit: de enige niet-lineariteit in de
> waterbalans is de klem, en een klem is een monoïde-element. Daarom is het geheel
> differentieerbaar én parallel, en niet ondanks maar dankzij de niet-lineariteit die het
> interessant maakt.

### 4.3 Wat er gratis bijkomt: voorbemaling is een verzadigende maatregel

Met de tweezijdige vorm is de peilmarge een actie. Nagerekend op de referentiebui,
uitgangspunt 180,6 cm stijging:

| peilmarge | piek boven streefpeil | winst | verzilverd deel van de marge |
|---|---|---|---|
| 0 cm | 180,6 cm | — | — |
| 5 cm | 175,6 cm | 5,0 cm | 100 % |
| 10 cm | 170,6 cm | 10,0 cm | 100 % |
| 20 cm | 170,1 cm | 10,5 cm | 53 % |
| 30 cm | 170,1 cm | 10,5 cm | 35 % |
| 100 cm | 170,1 cm | 10,5 cm | 10,5 % |

De eerste tien centimeter marge is volledig effectief; daarna is het op. De reden staat in
één getal: het gemaal van 5 m³/s op 140 ha open water maalt 0,309 m per dag leeg, en de
droge uren vóór de piek volstaan voor ongeveer tien centimeter. Meer marge afspreken
levert niets meer op.

Dat is een **vierde responsvorm** naast de drie die deel 1 §3.5 kent — monotoon,
plateau, binnenoptimum — namelijk monotoon met een harde verzadiging. `solve` kan hem al
aan (de gulden snede vindt op een plateau de linkerrand), maar `OptimumKind` heeft er nog
geen naam voor die het onderscheid met `PLATEAU` maakt: bij afvoeren betekent plateau
"meer capaciteit is verspilling", hier betekent het "meer *afspraak* is verspilling, de
capaciteit is de klem". Dat is voor een lezer een ander advies.

En het legt een onderscheid bloot dat makkelijk te missen is. Peilopzet en voorbemaling zijn
**niet** hetzelfde veld met een teken; ze zijn de twee randen van één band rond het
oorspronkelijke peil, en ze gedragen zich verschillend:

| | wat het is | vorm | wat het kost |
|---|---|---|---|
| `target_level_rise_m` | het streefpeil staat hoger | lineair en onbegrensd: elke cm opzet is een cm minder marge | drooglegging, permanent |
| `level_margin_m` | het peil mág onder het streefpeil zakken | verzadigend: 10 cm geeft 10 cm, 30 cm geeft nog steeds 10,5 cm | voorraad, en alleen tijdens de inzet |

Peilverlaging koop je; voorbemaling voer je uit. Dat de tweede verzadigt en de eerste niet,
is het soort onderscheid dat een model moet uitrekenen in plaats van aannemen — en het is
het argument waarom ze twee velden blijven en niet één.

---

## 5. De toestand: één verbinding, twee richtingen

### 5.1 Waarom niet één signed capaciteit

Issue #28 komt uit op `WaterExchangeAction(delta_m3_per_sec)` met een tekenconventie, en
signaleert daarbij zelf het probleem: *"een negatieve capaciteit is geen capaciteit"*. Dat
probleem is niet weg te definiëren, want het is fysiek:

- een gemaal en een inlaat zijn **twee kunstwerken**, met twee prijzen en twee
  levensduren;
- ze kunnen **beide bestaan** — de meeste polders hebben een gemaal én een inlaat, en dan
  is er geen enkel getal dat de verbinding beschrijft;
- de gerealiseerde flux `exchange[t]` wisselt binnen één seizoen van teken, terwijl de
  capaciteiten dat niet doen.

Dus: **de actie is signed, de toestand niet.**

```python
class Connection(BaseModel):
    """Een verbinding waarover een gebied water uitwisselt met zijn omgeving."""
    to: str                                   # knoopnaam, of OUTSIDE
    capacity_out_m3_per_sec: float = 0.0      # gemaal: dit gebied -> to
    capacity_in_m3_per_sec: float  = 0.0      # inlaat: to -> dit gebied
    head_max_m: float | None = None           # derating; None = peil-onafhankelijk
```

```python
class WaterExchangeAction(Action):
    """Vergroot de capaciteit van een verbinding in één richting.

    direction=OUT  -> gemaalcapaciteit erbij  (afvoeren)
    direction=IN   -> inlaatcapaciteit erbij  (aanvoeren)
    """
    connection: str
    direction: Direction
    delta_m3_per_sec: float = Field(..., ge=0)
```

De actie draagt de richting als eigen veld en de maatvoering blijft niet-negatief. Dat is
het beste van beide voorstellen uit issue #28: één actietype, geen dubbeling, en toch geen
enkel getal dat twee kunstwerken moet dragen. In de uitvoer komt `direction: "inflow"` of
`"outflow"` mee, zoals daar voorgesteld — dat blijft een goed idee.

`pump_capacity_m3_per_sec` verhuist daarmee van veld naar
`connections[0].capacity_out_m3_per_sec`. Issue #28 waarschuwt terecht dat je niet moet
hernoemen voor functionaliteit die er nog niet is; het punt is dat die functionaliteit hier
wél komt, en dat de verhuizing anders twee keer moet gebeuren.

### 5.2 En hier zit de hele ruimtelijke koppeling in

Dit is de kern van dit document, en het is één regel:

> **`to = OUTSIDE` is de huidige polder. `to = "polder B"` is de cascade.**

`OUTSIDE` is een knoop met oneindige berging en een vast peil: wat je erin pompt verdwijnt,
wat je eruit haalt is er altijd. Dat is exact het huidige model. Vervang die knoop door een
gewone polder en je hebt de kralenketting uit deel 1 §8.3 — zonder één nieuw begrip, want
de aanvoer die polder B ontvangt is de `exchange[t]` van polder A, en die reeks levert
`water_level_series` al (de `pumped`-reeks uit WP3).

Daarmee is de spatial coupling **in** het world model in plaats van eromheen: er is geen
"cascademodus" en geen tweede rekenpad. Er is een graaf, en de eenpolder-casus is die graaf
met één knoop en een randvoorwaardeknoop. De regressietest tegen het rekenblad is
daarmee geen speciaal geval dat gespaard moet worden, maar de kleinste instantie van het
algemene geval — en dat is een veel steviger basis dan een vlag.

Dezelfde regel verklaart ook meteen waarom aanvoeren en afwenteling hetzelfde probleem
zijn. Wat polder A inlaat komt uit de boezem, en dat is de voorraad van polder B. In de
graaf is dat automatisch waar; in een model per polder moet je het als beleidsregel
opleggen. Dat is dezelfde diagnose als deel 1 §8.3 stelt voor de trits, nu voor de
droogtekant.

---

## 6. Het netwerk: hoe dit tot heel Nederland schaalt

### 6.1 Hoe groot is "heel Nederland"

| grootheid | aantal | bron |
|---|---|---|
| poldergemalen | 7.792, waarvan 2.663 groter dan 50 m³/min | Unie van Waterschappen, handreiking poldergemalen 2023 |
| afwateringseenheden in het LHM (MOZART) | ± 8.500 | STOWA, inzetbaarheid bestaande modellen |
| regionale districten daarboven | ± 250 | idem |
| landelijk verdeelnetwerk | 1 (Distributiemodel) | idem |

De orde is dus 10⁴ knopen, en er bestaat al een gevestigde driedeling —
afwateringseenheid, district, landelijk net — die precies de hiërarchie is die issue #28
onder "hierarchical / multilevel optimization" voorstelt. Die hoeft niet verzonnen te
worden; hij is de bestaande schematisatie van het Nationaal Water Model.

Ter kalibratie van wat 10⁴ knopen kost: een differentieerbaar routeringsmodel voor
lineaire, tijdinvariante routing haalt op één A100 **6,8 miljoen kanalen, 85 jaar
dagelijkse afvoer op uurresolutie, in 1 minuut 42 seconden**. Ons nationale net is drie
ordes kleiner dan wat daar al in twee minuten past. De schaalvraag is hier dus geen
rekenvraag maar een architectuurvraag.

### 6.2 Datalayout: arrays over knopen, niet objecten per knoop

```
PolderState        blijft bestaan als de leesbare vorm aan de toolgrens
SystemState        de rekenvorm: struct-of-arrays

  area_ha                (n,)
  pct_open_water         (n,)
  retention_fraction     (n,)
  target_level_rise_m    (n,)
  edge_from, edge_to     (m,) int
  cap_out, cap_in        (m,)
  head_max              (m,)

reeksen                  (n, T)   drainage, waterstand, uitwisseling
```

Dit is dezelfde beweging als WP3 al maakte met de tijdas — de fysica neemt losse getallen
aan en geen pydantic-model — nu ook over de knopen. `PolderState` blijft de vorm waarin
een toolantwoord leesbaar is; `SystemState` is de vorm waarin de kern rekent. De conversie
zit op één plek, net als `to_state()` nu.

Gemeten, numpy, eenzijdige klem, één iteratie:

| knopen | tijdstappen | tijd |
|---|---|---|
| 100 | 168 uur | 0,15 ms |
| 1.000 | 168 uur | 1,47 ms |
| 8.500 | 168 uur | 11,6 ms |

Ongeveer 1,4 µs per knoop, vlak over drie ordes. Dat is het bewijs dat de vectorisatie over
knopen werkt en niet alleen in theorie de goede kant op wijst.

### 6.3 Oplosschema: één pass als het kan, iteratie als het moet

Twee gevallen, en het onderscheid is precies of er terugkoppeling is:

**Zonder terugkoppeling** — een gemaal dat draait ongeacht de benedenstroomse stand — is
één pass in topologische orde **exact**. Geen iteratie, geen tolerantie, geen
convergentievraag. Bovendien is het geheel dan lineair in de aanvoer, en dat is de
structuur waar de block-sparse-convolutieformulering uit §6.1 op rust: de hele graaf is
één sparse operator.

**Met terugkoppeling** — kopafhankelijke capaciteit, zoals deel 1 §8.3 kiest — is het een
vast-puntiteratie. Elke iteratie is een volledig gevectoriseerde pass over knopen én tijd,
en het argument voor convergentie staat in deel 1: begin met vrije afstroming (de maximale
uitstroom overal), en elke correctie kan alleen verlagen, dus de rij is monotoon dalend en
begrensd.

Nagerekend op een prototype: keten van vijf polders, elk pompend in de volgende, lineaire
derating `Q(h) = Q_max·(1 − h_ben/1,5)`.

| grootheid | uitkomst |
|---|---|
| passes tot convergentie op 10⁻¹⁰ | 2 |
| rekentijd van de hele keten | 0,057 ms |
| pieken in de keten | 307 / 345 / 356 / 356 / 217 cm |
| dezelfde polders los gerekend | 181 cm |

Over die laatste twee regels: de schematisatie is een speeltje — vijf identieke polders,
geen boezemberging, allemaal dezelfde bui op hetzelfde moment — dus de getallen zijn geen
uitspraak over Nederland. Wat ze wél laten zien is de richting en de orde: koppeling
**verdubbelt** hier de pieken. Dat is de discontinuïteit waar deel 1 §8.3 op wijst, en het
is de reden dat de cascade de *beslissing* verandert en niet alleen het getal. Twee passes
van 0,06 ms is de prijs.

### 6.4 De droogtekant heeft een verdeling nodig, en dat is een LP

Bij wateroverlast is de koppeling lokaal: mijn uitstroom is jouw aanvoer. Bij watertekort
is hij **globaal**: er is één schaarse voorraad en meer vragers dan water, en de
verdringingsreeks bepaalt wie krijgt. Dat is geen randvoorwaarde per knoop maar een
toewijzing over het net — precies wat het Distributiemodel in het LHM doet.

Een prioriteitstoewijzing over een netwerk is een lineair programma. Dat is goed nieuws
voor de architectuur: een LP is via impliciete differentiatie van de KKT-voorwaarden
differentieerbaar naar zijn parameters, en daar is gereedschap voor (cvxpylayers, jaxopt,
en in 2025/26 eerste-orde varianten zoals FFOLayer). Een LP-laag in de rollout breekt de
gradiëntketen dus niet.

Dat is de plek waar de verdringingsreeks in het model komt zonder hem als vuistregel op te
leggen — dezelfde beweging als deel 1 met de trits maakt. **Niet in WP8 t/m WP10.** Het
staat hier omdat het de reden is waarom de graaf en de differentieerbaarheid samen moeten
worden ontworpen en niet na elkaar.

---

### 6.5 Wat het gebouwde netwerk meteen laat zien

Alles hieronder is gemeten op een kralenketting van vijf identieke polders van 4000 ha met
3,5 % open water en een gemaal van 5 m³/s, op de referentiebui. **Speelgoedtopologie** —
geen boezemberging, geen expliciete routing, en `head_max` is het verzonnen getal uit V6.
De richtingen zijn robuust, de exacte waarden niet.

#### Vrije afstroming *is* het afwentelen

| | n0 (boven) | n1 | n2 | n3 | n4 (onder) |
|---|---|---|---|---|---|
| vrije afstroming | 181 cm | 359 | 369 | 369 | 369 |
| met derating vanaf 1,5 m | 318 cm | 363 | 369 | 369 | 227 |

Belangrijk om de term goed te houden: **afwentelen is de eerste rij.** De bovenste polder
pompt onvoorwaardelijk op capaciteit en houdt daardoor 1,81 m over terwijl de onderste
3,69 m krijgt — hij exporteert zijn probleem. Derating is het omgekeerde: de volle
benedenstroomse boezem duwt terug en dan houdt bovenstrooms het water zelf vast. Dat is
niet afwenteling maar het fysieke mechanisme waarvan het niet-afwentelen-principe de
beleidsregel is.

Het totaal blijft daarbij gelijk. Het benedenstroomse gemaal is de bottleneck en draait in
beide gevallen voluit, dus er verlaat evenveel water het systeem: derating **verplaatst** de
last en verergert hem niet. Wat de bovenste polder exporteerde is 1,38 m peilstijging, en
wat de onderste eraan overhield 1,42 m. Dat is de externaliteit gemeten in plaats van per
decreet geïnternaliseerd.

#### En daarmee draait de rangorde om

Het mechanisme in één zin: **de beperking bijt het hardst precies wanneer je het gemaal
nodig hebt, want dezelfde bui vult jouw polder én de boezem.** Op het piekuur verplaatst het
bovenste gemaal 0,00 van zijn 5,00 m³/s; gemiddeld over de gebeurtenis 0,92. Je betaalt voor
geïnstalleerde capaciteit en je krijgt effectieve capaciteit, en die twee lopen juist bij de
maatgevende gebeurtenis maximaal uiteen.

Kosten per centimeter, met de prijslijst uit deel 1 §8.1:

| | afvoeren (+2 m³/s) | bergen (+100 ha) | goedkoopst |
|---|---|---|---|
| los gerekend | € 66 k/cm | € 178 k/cm | afvoeren |
| gekoppeld | € 502 k/cm | € 101 k/cm | **bergen** |

Dit is de eerste keer dat de trits in dit project *uit* het model komt in plaats van eroverheen
te worden gelegd. En de omslag hangt niet aan de gekozen `head_max`; hij treedt op tussen 6
en 4 meter en wordt daaronder alleen sterker:

| `head_max` | afvoeren | bergen | goedkoopst |
|---|---|---|---|
| geen koppeling | € 66 k/cm | € 178 k/cm | afvoeren |
| 6,0 m | € 119 k/cm | € 140 k/cm | afvoeren |
| 4,0 m | € 274 k/cm | € 122 k/cm | bergen |
| 2,0 m | € 382 k/cm | € 105 k/cm | bergen |
| 1,0 m | € 746 k/cm | € 98 k/cm | bergen |

Een poldergemaal heeft een opvoerhoogte van 1 tot 5 meter, dus het enige geval waarin
afvoeren wint is "praktisch geen koppeling".

**Wat het model hiermee niet afdwingt.** Er zitten twee redenen onder niet-afwentelen. De
doelmatigheid — afwentelen werkt op systeemschaal niet — staat nu in het model. De
rechtvaardigheid — ook binnen wat fysiek kan zou je je water niet bij je buur moeten dumpen
— is geen fysica, en die blijft een politieke keuze. Voor een zaal met beleidsmakers is dat
het eerlijke onderscheid.

#### De terugkoppeling overleeft een reistijd

De zorg dat bovenstrooms vroeg afvoert, ontsnapt, en dat de ellende pas later benedenstrooms
verschijnt, blijkt in dit systeem niet op te gaan. Het bovenste gemaal wordt vanaf uur 72
geblokkeerd terwijl zijn eigen piek op uur 167 valt, en met een expliciete reistijd op de
koppeling blijft dat zo:

| reistijd | 0 u | 24 u | 48 u | 96 u |
|---|---|---|---|---|
| piek n0 | 318 cm | 312 | 302 | 296 |
| geblokkeerd vanaf | 72 u | 73 u | 80 u | 90 u |

De reden is de verblijftijd: de boezempiek doet er 11,6 dagen over om leeg te lopen. De
beperking is geen korte puls waar je langs kunt glippen maar een plateau van dagen.

#### Maar vasthouden helpt benedenstrooms vrijwel niet — en dat is een echte bevinding

70 % van het land vasthouden, effect op de piek van elke knoop:

| wie houdt vast | n0 | n1 | n2 | n3 | n4 |
|---|---|---|---|---|---|
| n0 | **+24 cm** | +8 | 0 | 0 | 0 |
| n1 | 0 | 0 | 0 | 0 | 0 |
| n2 | 0 | 0 | 0 | 0 | 0 |

Vasthouden werkt lokaal en dooft binnen één knoop uit. De oorzaak is structureel:
vasthouden is massaconserverende **vertraging** en geen berging, en een langzame integrator
ziet vertraging niet. De maat die telt is vertraging tegen verblijftijd, en dat is te meten —
vier polders op één boezem van 20 m³/s, boezempiek 359 cm, verblijftijd 11,6 dagen:

| vertraging | 0 d | 2 d *(de ontwerpconstante)* | 10 d | 20 d | 80 d |
|---|---|---|---|---|---|
| winst op de boezempiek | 0 cm | **+8 cm** | +17 | +34 | +61 |

Twee dagen op elf is een fractie, dus levert het een fractie. **Het model reproduceert dus
bergen vóór afvoeren krachtig, en vasthouden vóór bergen op systeemniveau niet.** Dat
spreekt beleidsdoctrine tegen en het is met deze speelgoedtopologie niet uit te maken of het
een vondst is of een artefact — zie V10. Narekenen met Ton voordat het op een slide komt.

De toerekening zelf is geen probleem: leave-one-out geeft per knoop de bijdrage, en met de
gradiënten uit WP11 is het `∂(benedenstroomse piek) / ∂(bovenstroomse maatregel)` in één
backward pass. Wat die afgeleide hier zegt is bijna nul voor vasthouden en groot voor
capaciteit. Dat is geen onzichtbaarheid maar een echte bijna-nul.

#### De aanvoerkant heeft dezelfde koppeling niet, en dat is asymmetrisch

Twee koppelingen per richting, en er ontbreken er twee:

| | langs de stroom | tegen de stroom |
|---|---|---|
| **afvoeren** | A's uitstroom is B's aanvoer (volume) — ✅ | B's peil derateert A's gemaal (opvoerhoogte) — ✅ |
| **aanvoeren** | de bron raakt leeg door elke afnemer (volume) — ❌ | het eigen peil sluit de eigen inlaat (verval) — ✅ als de `hi=0` klem |

De `hi=0` klem is de terugwerking aan de aanvoerkant en die zit erin: is de polder vol, dan
knijpt de inlaat af, en bij overcapaciteit levert hij de vraag en niet zijn capaciteit. Wat
ontbreekt is de bron-afhankelijkheid van de inlaatcapaciteit — `head_max_m` wordt alleen
gebruikt om `capacity_out` te derateren, en een zakkend bronpeil dat de inlaat knijpt is
dezelfde formule, ongebruikt in de andere richting.

**En het structurele verschil is groter dan de richting.** Afvoeren is een ketting: jouw
water gaat door je buur heen, een pass in topologische orde lost het op, en de beperking zit
lokaal op elke kant — dat is routing. Aanvoeren is een gedeelde pot: alle afnemers trekken
uit dezelfde eindige bron en die staan niet achter elkaar maar naast elkaar. Er bestaat geen
doorloopvolgorde die dat oplost; je moet verdelen. Dat is toewijzing, en het is precies
waarom de verdringingsreeks een prioriteitenlijst is en geen routeringsregel — en waarom
§6.4 daar een LP neerzet en niet een tweede `simulate_network`.

---

## 7. Backend: numpy nu, JAX als tweede backend

Niet nu JAX toevoegen. Wel nu zorgen dat het later een schakelaar is en geen herbouw.

**Wat de kern daarvoor moet zijn** — en dit is een codereview-criterium, niet een intentie:

| regel | reden |
|---|---|
| geen python-lus over de tijdas, en geen over de knopen | de scan en de vectorisatie zijn het hele punt |
| geen `.item()`, geen `float(...)` binnen de kern | dat forceert synchronisatie en breekt tracing |
| geen `if` op een array­waarde; gebruik `where`/`clip` | een tracer heeft geen waarheidswaarde |
| in-place mutatie alleen op de bouwkant, niet in de recursie | JAX-arrays zijn onveranderlijk |
| de kern neemt arrays en getallen aan, geen pydantic-modellen | staat er al zo in WP3; hier alleen vasthouden |

Dat is een deelverzameling van numpy die JAX één-op-één ondersteunt. Eén moduleniveau-
constante `xp = numpy` en de kern is backend-onafhankelijk; een test die de kern met beide
doorrekent houdt het zo.

**Wat de gradiënt oplevert.** Gemeten met `jax.lax.associative_scan` op de geklemde
monoïde, tweezijdig, 240 tijdstappen, CPU van een laptop:

| knopen | voorwaarts | gradiënt |
|---|---|---|
| 1.000 | 1,2 ms | 3,6 ms |
| 8.500 | 6,2 ms | 39 ms |
| 50.000 | 36 ms | 254 ms |

Op nationale schaal is dat **één gradiënt van de doelfunctie naar elke knoop in 39
milliseconden**, op een CPU. Dat is het antwoord op de schaalvraag, en het is een ander
antwoord dan "we enumereren de maatregelmixen". Enumeratie kost het aantal knopen keer het
aantal maatregelen aan doorrekeningen om te weten waar een euro het meeste oplevert; de
adjoint kost er één.

**Wat dat niet wegneemt.** Het gemengd-discrete deel blijft — een gemaal bouw je wel of
niet, en een trapkost is niet differentieerbaar. Daarom blijft de vorm die issue #28
voorstelt de goede: enumeratie of branch-and-bound over de discrete keuzes, en per keuze
een continue oplossing. Wat verandert is dat die continue oplossing gradiënten heeft, en
dat SLSQP daar dan ook echt goed in is in plaats van eindige differenties te draaien.
De aanbeveling uit issue #28 — SLSQP boven op expliciete enumeratie, geen genetisch
algoritme en geen Bayesiaanse optimalisatie — blijft dus staan; ze wordt alleen goedkoper.

**Waar MPC wel en niet past.** Ook dat is in issue #28 al uitgezocht en de conclusie was
juist: een gemaal bouwen is geen regelactie op een horizon van 24 uur. Twee horizonnen,
twee problemen: de investeringskeuze is een lange-horizonontwerpprobleem, en het
peilbeheer binnen een seizoen — hoeveel marge, wanneer voormalen — is regeling. §4.3 laat
zien dat die tweede laag nu voor het eerst representeerbaar wordt. Dat is de plek waar MPC
later thuishoort, en niet in de investeringsloop.

---

## 8. Wat dit betekent voor het praten met de tools

Dit is de laag waar het meeste kan misgaan, want de verleiding is groot om het netwerk aan
de agent te geven.

**Niet doen: het netwerk als toolargument of als tooluitvoer.** 8500 knopen passen niet in
een toolaanroep, en als ze passen zijn ze niet leesbaar. Bovendien is een graaf als
argument precies wat een LLM slecht kan produceren en goed kan verzinnen.

**Drie lagen, en de MCP-primitieven bestaan er al voor:**

| laag | primitief | wat erin zit |
|---|---|---|
| polderschaal | **tools**, de zes bestaande plus de aanvoer-tegenhangers | één vraag, één gebied, één getal, plus `assumptions` en `state_after` |
| het systeem | **resource**, alleen-lezen en adresseerbaar | topologie en toestand; de agent verwijst ernaar in plaats van hem te dragen |
| systeemvraag | **tool met een selectie** | in: een gebied of een lijst knoopnamen; uit: aggregaten plus de bindende beperking en de knoop waar hij zit — niet 8500 rijen |

Dat sluit aan op waar MCP in 2026 heen gaat: tools voor acties, resources voor
alleen-lezen context, en expliciet *scoped* tools boven brede tools — geen
`search_all_nodes`, wel `evaluate_region(selection)`. Voor lange doorrekeningen is er
inmiddels ook het tasks-mechanisme, wat het alternatief "de agent laat 8500 aanroepen doen"
overbodig maakt.

**Wat de derde laag moet teruggeven is niet het antwoord maar de reden.** Dat is dezelfde
les als `SolveStatus` en `LimitReason` uit WP5: een agent kan niets met een geklemd getal,
en wel met "dit is de bindende beperking en daar zit hij". Op netwerkschaal betekent dat:
welke knoop bindt, welke maatregel daar het meeste oplevert per euro, en — dankzij §7 — hoe
groot dat marginale effect is. De gradiënt is niet alleen een optimalisatietruc, hij is de
uitleg.

**Twee namen, één actie.** `calculate_supply_given_h` en `calculate_discharge_given_h`
staan naast elkaar op dezelfde `WaterExchangeAction`, met elk hun eigen exogene reeks en
hun eigen doelveld. Het is dezelfde keuze als bij `given_h` versus `given_area`: dezelfde
`solve`, twee vragen, twee namen.

**En het onderscheid dat issue #28 punt 7 terecht maakt**, wordt hier pas echt nodig:
`ACTION_INFEASIBLE` ("deze maatregel kan het niet") tegenover `PROBLEM_INFEASIBLE` ("geen
enkel pakket kan het"). Op één polder met één maatregel is dat een verfijning; op een
netwerk met vier actietypen op tien knopen is het het verschil tussen een agent die
doorzoekt en een agent die ten onrechte opgeeft. Meenemen in WP9.

---

## 9. Werkpakketten

De uitvoering staat in [`BOUW_WP8_WP10.md`](BOUW_WP8_WP10.md): bestand voor bestand, met de
geverifieerde ankergetallen, de invarianten en de faalscenario's. Dit is de samenvatting;
dat is het werkdocument.

Elk pakket laat de suite groen achter, en elk pakket laat de gouden regressie tegen
`TttE_v03.xlsx` op 1·10⁻¹² staan. Dat is bij WP8 en WP9 geen bijzaak maar de belangrijkste
test: beide zijn generalisaties die het bestaande geval exact moeten bevatten.

### WP8 — de tweezijdige kern

- `clamped_scan(delta, lo, hi)` als de nieuwe primitief; `water_level_series` wordt de
  aanroep met `lo=0, hi=+∞`.
- `slack_of(levels, delta)` als de enige afgeleide grootheid; de weggepompte reeks, de
  onbenutte capaciteit, de aangevoerde reeks en de onvervulde vraag zijn er alle vier een
  teken en een factor `c` van verwijderd.
- `PolderState.level_margin_m` als toestandsveld, en `PeilmargeAction` als actie. Twee
  velden en niet één: zie de tabel aan het eind van §4.3 voor waarom opzet en marge
  verschillend gedrag hebben.
- `OptimumKind.SATURATED` naast `PLATEAU`, met het onderscheid uit §4.3 in de beschrijving.

**Klaar als:** de scan de bestaande kern reproduceert binnen 1·10⁻¹² m; de tweezijdige tak
de sequentiële lus reproduceert binnen 1·10⁻¹² m; het peilmarge-anker klopt (10 cm geeft
10,0 cm winst, 30 cm geeft 10,5 cm); een doorrekening blijft onder 1 ms.

### WP9 — verbinding en uitwisseling

- `Connection` en `WaterExchangeAction` (§5.1); `pump_capacity_m3_per_sec` verhuist, met
  `AliasChoices` zodat de toolgrens niet wijzigt.
- `OUTSIDE` als expliciete randvoorwaardeknoop met oneindige berging en vast peil.
- Aanvoer als tweede regime: een tekortreeks als exogene invoer, en een doelfunctie op de
  laagste stand of op het benodigde volume.
- `ACTION_INFEASIBLE` tegenover `PROBLEM_INFEASIBLE` (§8).
- De naad uit §2 rechtzetten: de veldbeschrijving en het gedrag bij een negatieve delta
  gelijktrekken.

**Klaar als:** één knoop plus `OUTSIDE` reproduceert alle huidige uitkomsten exact; de
aanvoerankers uit §4.1 kloppen (geen aanvoer −83,4 cm, 0,4 l/s/ha −14,3 cm); `direction`
staat in elke uitwisselingsuitvoer; `grep -r pump_capacity src/` levert alleen aliassen.

### WP10 — het netwerk

- `SystemState` als struct-of-arrays (§6.2), met `PolderState` als de leesbare projectie.
- Topologische pass zonder terugkoppeling, exact en zonder iteratie.
- Vast-puntiteratie met kopafhankelijke capaciteit, met een assertie op monotone daling en
  een harde iteratielimiet.
- Prestatietest op 8500 knopen.

**Klaar als:** het netwerk met één knoop identiek is aan WP9; de keten van vijf reproduceert
het prototype; zonder terugkoppeling is het antwoord identiek aan los rekenen plus
doorgegeven aanvoer, tot machineprecisie; 8500 knopen × 240 uur onder 100 ms; de
massabalans sluit over het hele netwerk.

### WP11 — gradiënten en de zoekopgave

- Backendtest volgens §7; JAX als optionele extra, niet als harde afhankelijkheid.
- `optimize(state, storm, constraints, actions)` naast `solve(action, target)` — de
  scheiding die issue #28 punt 6 voorstelt, en die hier onveranderd wordt overgenomen.
- SLSQP per actiemix, met analytische gradiënten waar de backend die levert.
- De MCP-laag uit §8: resource voor de topologie, `evaluate_region` voor systeemvragen.

**Klaar als:** de robuustheidscurve uit deel 1 §8 draait op het netwerk met één knoop en
geeft dezelfde curve; de gradiënt is numeriek gecontroleerd tegen eindige differenties op
alle vier de actietypen; een systeemvraag over 8500 knopen levert een antwoord van minder
dan honderd regels.

#### Wat er gebouwd is, en het resultaat waar de demo op rust

`PeilopzetAction` is de vierde actie — de laatste ontbrekende bouwsteen uit deel 1 §8.2. Er
hangt geen prijs aan, en dat is geen omissie: peilopzet kost drooglegging en dus
landbouwschade, wat een verdringingsvraagstuk is en geen investeringspost. Gratis is hij
niet, want `target_level_rise_m` telt op in `dh_total_above_original_datum_m`. De inundatie-eis
rekent hem dus af in centimeters in plaats van in euro's, en dat is precies de spanning uit
§8.0 zonder dat er een getal verzonnen hoefde te worden.

`optimize` is de pakketzoeker: enumeratie over de vijftien niet-lege actiemixen buiten,
SLSQP per mix binnen. Referentiebui, polder van 4000 ha, inundatienorm 100 cm:

| eisen | goedkoopste pakket | prijs |
|---|---|---|
| alleen inundatie | **afvoeren** 2,91 m³/s | € 5,59 mln |
| plus 20 mm voorraad | **afvoeren** 5,71 m³/s + **peilopzet** 57 cm | € 10,97 mln¹ |

¹ Alleen de maatregelen die een prijs hébben. Peilopzet heeft er geen, en dat staat in
`Package.priceless`.

De tweede eis verandert het pakket: afvoeren alleen koopt geen voorraad, en peilopzet is de
enige maatregel die voorraad direct koopt. Maar **welk** pakket het wordt, hangt aan een
prijs die er niet is — en dat is de eerlijke versie van wat hier eerder stond.

Er stond namelijk `bergen 190 ha + peilopzet 24 cm` voor € 25,67 mln, met de conclusie dat
afvoeren volledig uit het optimale pakket verdwijnt. Dat was het niet-geconvergeerde antwoord
van vóór de `COST_SCALE`-fix (8040f8a). Met een zoeker die wél convergeert wint
afvoeren-plus-opzet, omdat peilopzet in euro's gratis was: elke centimeter opzet snoept
inundatiemarge op, en een groter gemaal koopt die goedkoper terug dan 190 hectare open water.

De schaduwprijs maakt dat een getal in plaats van een artefact. Varieer de prijs van
peilopzet en lees af waar het antwoord kantelt (`switch_price_of`):

| prijs peilopzet | goedkoopste pakket |
|---|---|
| geen prijs | afvoeren 5,71 m³/s + opzet 57 cm |
| tot € 0,14 mln/cm | idem |
| vanaf **€ 0,145 mln/cm** | afvoeren 5,60 + **bergen 2,8 ha** + opzet 56 cm |
| **€ 1,5 mln/cm** | **bergen 190 ha + opzet 24 cm** — het oude antwoord, exact terug |

De substitutie is continu: bergen komt er met een paar hectare in en groeit. Bij € 1,5 mln
per centimeter is afvoeren helemaal weg, en dat is € 36 mln over 4000 ha, oftewel ruim
€ 9.000 per hectare — ongeveer een tiende van de agrarische grondwaarde die `COST_OPEN_WATER`
zelf als bron noemt. Een bespreekbare orde van grootte, dus.

**Daarmee wordt de uitspraak sterker in plaats van zwakker.** Niet "de trits ontstaat uit het
model", maar: *afvoeren verdwijnt uit het pakket zodra een centimeter drooglegging meer dan
anderhalve ton per hectare waard is — en of dat zo is, is een vraag voor het waterschap en
niet voor ons.* De politieke variabele staat expliciet in plaats van weggestopt in een
ontbrekende prijs. Zie issue #30 en `BOUW_WP13_WP15.md` WP13.0.

De gradiënt is centrale differentie en expliciet meegegeven aan SLSQP in plaats van door
scipy zelf te laten schatten, zodat hij van ons is en getest kan worden — tegen de gesloten
vorm waar die bestaat: `∂voorraad/∂peilopzet` is het aandeel open water maal 1000, dus
35 mm per meter. Dat is O(variabelen) simulaties en op polderschaal gratis. Op nationale
schaal is het precies de reden dat de adjoint uit §7 nodig is, en dat blijft een
afhankelijkheidsbesluit: **JAX staat niet in `pixi.toml`** en de kern is alleen geschikt
gemaakt, niet omgezet.

`calculate_region_given_storm` is de negende tool en de enige die meer dan één gebied
aanneemt. Hij geeft geen rij per gebied terug maar de bindende knoop en twee getallen die een
model per polder niet kan produceren: het **koppelingseffect** (hoeveel van de piek van
bovenstrooms komt) en de **geblokkeerde capaciteitsfractie** (welk deel van het geïnstalleerde
gemaalvermogen op het eigen piekuur wegviel). Op een ketting van drie is dat 178 cm
respectievelijk 100 %. De selectie is begrensd op 50 knopen — niet de grens van de rekenkern
maar van wat leesbaar is.

### WP12 — de onzekerheid in de uitvoer

Onafhankelijk van WP8 t/m WP11 en naar voren te halen. De massabalans is exact, de
maatregelen zijn vuistregels, en de uitvoer geeft die twee dezelfde status: vier
significante cijfers op alles.

**Hoe groot dat probleem is, gemeten.** Bergen, doel 1,0 m, referentiepolder, T=100,
basisantwoord 68,18 ha:

| onzekerheid | effect op het antwoord |
|---|---|
| `percentage_open_water` 3,0 → 4,0 | 48,2 – 88,2 ha, dus 59 % spreiding op één veld |
| regime LL → H | 0,6 – 98,5 ha |
| duur 48 / 96 / 192 u | 3,1 – 78,8 ha |
| alle aangenomen velden samen (162 combinaties) | 64 % slaat om naar `no_measure_needed`; waar wél nodig 0,8 – 114,4 ha, interkwartiel 17,6 – 60,9 |
| **rangorde bergen versus afvoeren** | **0 van 162 combinaties draait om** |

Dat laatste is de vondst: het model is **niet uniform betrouwbaar**. Het is sterk over
haalbaarheid en rangorde, en zwak over maatvoering. Vier cijfers geven aan alles dezelfde
status, en dát is de fout — niet de precisie zelf.

**Wat er komt, in volgorde van opbrengst.**

1. `sensitivity` in de uitvoer: per weggelaten veld het antwoord aan de uiteinden van zijn
   plausibele bereik. Maakt `ASSUMPTION_NOTES` van algemeen proza een uitspraak over dít
   antwoord. Zes extra solves, ongeveer 10 ms.
2. Afgeleide precisie in de `description`, vier cijfers in `data`. Boven 30 % spreiding één
   significant cijfer en het woord "ordegrootte"; boven 3 % twee. De agent herhaalt de zin,
   niet het veld — daar moet de eerlijkheid dus zitten.
3. `model_caveats`, opgebouwd als `assumptions`: allowlist, conditioneel, met waarom het
   uitmaakt. Zomer triggert V3 (het verlies wordt mogelijk dubbel geteld — tot een derde
   lager antwoord), 48 en 192 uur triggeren V4, `return_period ≥ 200` triggert de
   extrapolatie, een prijs in de uitvoer triggert de lineair-versus-trapkost-keuze. Zo staan
   de openstaande vragen in het antwoord in plaats van alleen in dit document.

   **De belangrijkste is de aanvoerbeschikbaarheid**, en die verdient een eigen alinea.
   Vraagt een tool om inlaatcapaciteit, dan is het antwoord — "0,45 l/s/ha en je tekort is
   gedekt" — correct voor de vraag die gesteld is: één gebied, geen netwerk. Er is dus geen
   foutief antwoord. Wat er wél mis is, is dat er een **dragende aanname** onder zit die niet
   in `assumptions` staat: dat het water bij de inlaat beschikbaar is. Dat is een eigenschap
   van het regionale systeem en niet van dit gebied, en voor hoog Nederland is het
   doorgaans onwaar. Twente, 4000 ha met 1 % open water bij 4 mm/dag over 30 dagen:

   | | |
   |---|---|
   | status | `exact` |
   | gevraagde inlaat | 0,45 l/s/ha = 1,81 m³/s |
   | benodigd volume | **4,68 miljoen m³ in een maand** |
   | eigen buffer | 3,0 mm, oftewel de bodem na 0,7 dag |

   De natte kant heeft dezelfde aanname en daar is hij onschadelijk: de zee neemt je water
   aan. Op de droge kant is hij dragend, en dat is precies het onderscheid dat `assumptions`
   hoort te maken. Het **volume** erbij zetten is de goedkoopste echte verbetering: een
   debiet klinkt haalbaar, 4,68 miljoen m³ nodigt uit tot narekenen. Zie V11 voor de
   modeluitbreiding die er daarna van moet komen.
4. De tekst op robuustheid ordenen: haalbaarheid, dan welke maatregel aan de beurt is, dan
   de ordegrootte, dan de spreiding met zijn oorzaak.

**Eén discipline.** Geen verzonnen foutbalk. Parametrische onzekerheid is berekenbaar en
wordt als berekend bereik gemeld; structurele modelfout is dat niet en wordt als benoemde
lijst van ontbrekende termen gemeld, nooit als percentage. Een gefabriceerd `± 15 %` is
erger dan een gefabriceerd puntgetal, want het ziet uit als kennis.

Wat er wél eerlijk over structurele fout te zeggen is: de laatste ontbrekende term die we
vonden — directe neerslag op open water — was 10,3 cm op 170 cm waard, dus 6 % op de stand
en 26 % op de maatvoering. Geen foutbalk, maar een gemeten kalibratie van wat één omissie
kost.

**Twee dingen om nu al te weten.** De y-as van de robuustheidscurve, in miljoenen euro's, is
het onbetrouwbaarste getal in het hele systeem en tegelijk de kop van de demo. En de
rangorde die zo robuust is tegen invoeronzekerheid (0 van 162) is dat *niet* tegen de
kostenvorm: met trapkost draait hij om rond 100 cm. Die twee mogen in de tekst niet dezelfde
zekerheid uitstralen.

**Klaar als:** elk antwoord met een aangenomen veld draagt een berekende spreiding; geen
`description` noemt meer cijfers dan de spreiding toestaat; elke openstaande vraag uit §10
verschijnt als caveat zodra hij van toepassing is; en er staat nergens een foutbalk die niet
uit een berekening komt.

---

## 10. Openstaande vragen

**Aan Ton en intern bij HKV** — geen ervan blokkeert een werkpakket.

| # | vraag | interim |
|---|---|---|
| V6 | Modelleren waterschappen een poldergemaal met een pompkarakteristiek of met een uitschakelpeil, en met welke waarden? Staat al open in deel 1 §8.3. | lineaire derating, `head_max` per verbinding, default peil­onafhankelijk zodat WP9 niets verandert |
| V7 | Welke exogene reeks voor droogte? Kandidaten: de KNMI-neerslagtekortreeks met zijn referentielijnen (mediaan en 5 % droogste), een jaar als 1976 / 2018 / 2022, of de Deltascenario's 2024 als scenario-as. | de KNMI-referentielijnen, want die hebben een frequentie-interpretatie en passen daarmee op dezelfde as als de terugkeertijd van de bui |
| V8 | Is de aanvoercapaciteit van een polder bepaald door de watervraag of door de doorspoelbehoefte? Dit lijkt de belangrijkste van de drie, zie hieronder. | de aanvoernorm 0,3 tot 0,4 l/s/ha als default, en verzilting expliciet buiten het model |
| V9 | Heeft de boezem eigen berging nodig als knoop, of is hij een verbinding met een peil? | knoop met berging; een verbinding zonder berging is een bijzonder geval |
| V10 | Klopt het dat vasthouden benedenstrooms vrijwel niets doet (§6.5), of is dat een gevolg van onze schematisatie? De verhouding vertraging tegen verblijftijd is de maat; met `days_to_retain = 2` tegen een boezemverblijftijd van 11,6 dagen komt er 8 cm uit. Echte *berging* bovenstrooms is iets anders dan vertraging en zou wél moeten doorwerken. | vastgelegd als bevinding met de speelgoedtopologie er expliciet bij; niet op een slide voordat Ton het heeft nagerekend |
| V11 | De twee ontbrekende aanvoerkoppelingen uit §6.5: hoe modelleren we dat een bron eindig is en door meer afnemers wordt gedeeld, en hangt de inlaatcapaciteit in de praktijk aan het bronpeil? Voor hoog Nederland — Twente, de Achterhoek, de zandgronden — is beschikbaarheid en niet capaciteit de bindende beperking. | de tool meldt de aanname en het benodigde volume (WP12); de eindige bron en de toewijzing komen na WP11 |

Over V8, want dat is geen detail. De STOWA-deltafact over waterinlaat zegt dat
doorspoeling tegen verzilting een efficiëntie van 3 tot 5 procent heeft — er is twintig tot
dertig keer zoveel water nodig als voor beregening — en dat bij een chloridebelasting boven
2000 mg/l een doorspoelintensiteit van meer dan 0,5 l/s/ha nodig zou zijn, wat in bepaalde
perioden niet haalbaar was. De aanvoercapaciteit van een verziltende polder wordt dus
gedimensioneerd op **waterkwaliteit** en niet op waterkwantiteit, en dan is de vuistregel
van 0,3 tot 0,4 l/s/ha voor die polders het verkeerde getal.

Dat is precies dezelfde soort ontbrekende term als de directe neerslag op open water in
deel 1 §7 V1: geen kwestie van resolutie maar van een grootheid die er hoort te staan. De
eerlijke uitkomst voor nu is dat de tool de aanvoervraag rekent en niet de doorspoelvraag,
en dat dat in `assumptions` komt te staan — niet dat er een chloridebalans wordt ingebouwd.

**Risico's**

| risico | kans | mitigatie |
|---|---|---|
| De tweezijdige scan blijkt in float32 te onnauwkeurig voor de gouden test | midden | de kern rekent in float64; float32 alleen op de netwerkschaal, en daar met een eigen tolerantie |
| De vast-puntiteratie convergeert niet op een echte topologie met lussen | midden | assertie op monotone daling, harde limiet, en rapporteren als de limiet wordt geraakt; een klem in twee passes geeft altijd een bruikbare bovengrens |
| `Connection` maakt de toolgrens ingewikkelder in plaats van eenvoudiger | reëel | `PolderState` blijft de projectie die de tools teruggeven; het netwerk komt de toolgrens niet over behalve via een selectie |
| De droogtekant vraagt om grondwater en daarmee om een heel ander model | reëel | expliciet buiten scope; de uitlezing blijft oppervlaktewater, en dat wordt in de uitvoer gezegd |
| Scope kruipt naar het netwerk voordat de uitwisseling klopt | reëel | WP8 en WP9 eerst, en WP9 moet de eenknoopcasus exact reproduceren voordat WP10 begint |

---

## 11. Gevolgen voor de talk

Twee dingen worden hier sterker, en één ding moet worden bijgesteld.

**Sterker.** Slide 11 en 12 draaien om "structuur in plaats van resolutie". §5.2 is daarvan
de scherpste vorm die er is: de cascade is geen uitbreiding van het model maar dezelfde
verbinding met een andere bestemming, en de gevalideerde eenpolder-casus is de kleinste
instantie van het algemene geval. Dat is een uitspraak over architectuur die een zaal vol
modelbouwers meteen begrijpt, en het is aantoonbaar in plaats van beweerd.

En §4.2 geeft de talk het getal dat §11 van het presentatiedocument nog mist. Daar staat
dat er een vergelijkingsgetal nodig is voor "orders of magnitude". Dat getal is er nu voor
de andere as: één gradiënt van een nationale doelfunctie naar 8500 knopen in 39
milliseconden op een laptop, tegen 6,8 miljoen kanalen in 102 seconden op één A100 als
kalibratie van wat de literatuur al haalt. De claim wordt daarmee niet "wij zijn sneller
dan een hydrodynamisch model" — dat is een oneerlijke vergelijking — maar "een
world-modelvorm laat een zoekopgave op nationale schaal toe, en dat is een andere as dan
fidelity". Dat is precies de tweedeling uit §1b van de talk.

**Bijstellen.** De demo in §9 heeft nu drie maatregelen met drie vormen. Na WP8 zijn het
vijf maatregelen met vier vormen, waarvan er twee — peilopzet en voorbemaling — hetzelfde
veld met een teken zijn, en twee andere — aanvoer en afvoer — dezelfde verbinding met een
richting. Dat is een beter verhaal dan "vijf maatregelen", want het is een uitspraak over
de toestandsruimte en niet over een boodschappenlijstje. De regel om op te schrijven:

> Er zijn niet vijf maatregelen. Er zijn vier toestandsgrootheden — berging, vertraging,
> verbinding en peilband — en de laatste twee hebben elk twee kanten.

---

## 12. Bronnen

**Rekenkern en schaalbaarheid**

- [Hascoët e.a., *Differentiable River Routing for End-to-End Learning of Hydrological Processes*, JGR-MLC 2026](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2025JH000760) — LTI-routing als block-sparse convolutie; 6,8 mln kanalen, 85 jaar, uurresolutie in 1 min 42 s op één A100; en de expliciete beperking dat de LTI-aanname niet-lineariteiten zoals kunstwerkbediening uitsluit
- [Song e.a., *High-Resolution National-Scale Water Modeling Is Enhanced by Multiscale Differentiable Physics-Informed Machine Learning*, WRR 2025](https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2024WR038928) — differentieerbaar op nationale schaal, mediane NSE van 4997 bekkens van 0,48 naar 0,68
- [*Sequential-Parallel Duality in Prefix Scannable Models* (2025)](https://arxiv.org/pdf/2506.10918) en [*ScanWeaver: Compiler-Driven Parallelization of Affine Recurrences via Associative Scan Lowering* (2026)](https://arxiv.org/pdf/2606.00601) — de theorie achter §4.2: affiene recurrenties zijn prefix-scans
- [jaxopt, *Efficient and Modular Implicit Differentiation*](https://arxiv.org/pdf/2105.15183), [cvxpylayers](https://github.com/cvxpy/cvxpylayers) en [*A Fully First-Order Layer for Differentiable Optimization* (2025)](https://arxiv.org/pdf/2512.02494) — differentiëren door een LP heen, nodig voor §6.4

**Nederlandse schaal en schematisatie**

- [Unie van Waterschappen, KCAO-handreiking poldergemalen (okt 2023)](https://unievanwaterschappen.nl/wp-content/uploads/2023/10/KCAO-handreiking-Poldergemalen-oktober-2023-1.pdf) — 7.792 poldergemalen, 2.663 boven 50 m³/min
- [STOWA, inzetbaarheid van bestaande hydrologische modellen voor waterkwantiteit](https://www.stowa.nl/deltafacts/zoetwatervoorziening/aanpassen-aan-klimaatverandering/inzetbaarheid-van-bestaande-hydrologische-modellen-voor-waterkwantiteit) — ± 8.500 afwateringseenheden in MOZART, ± 250 districten, gekoppeld aan het landelijke Distributiemodel
- [Deltares, LHM in het Nationaal Water Model](https://publicwiki.deltares.nl/display/NW/LHM) — MODFLOW, MetaSWAP, MOZART en DM; dag- respectievelijk decadetijdstap
- [Deltares, RTC-Tools](https://www.deltares.nl/en/software-and-data/products/rtc-tools-control-and-optimisation) en [RTC-Tools 2 (Baayen e.a.)](https://publicwiki.deltares.nl/download/attachments/119050785/RTC-Tools2_AnOpenSourceToolboxForControlAndMulti-objectiveConvexOptimizationOfEnvironmentalSystemsUnderForecastUncertainty_BaayenEtAl.pdf) — CasADi voor algoritmische differentiatie, lexicografisch goal programming, meertraps stochastische optimalisatie. Dit is de bestaande Deltares-vorm van "world model plus constrained optimization", en het is geen concurrent maar een referentiepunt voor de talk

**Aanvoer, droogte en peilbeheer**

- [STOWA, effectiviteit van waterinlaat](https://www.stowa.nl/deltafacts/zoetwatervoorziening/droogte/effectiviteit-van-waterinlaat) — doorspoelefficiëntie 3 tot 5 %, en meer dan 0,5 l/s/ha nodig boven 2000 mg/l chloride
- [STOWA, dynamisch peilbeheer](https://www.stowa.nl/deltafacts/zoetwatervoorziening/droogte/dynamisch-peilbeheer) — peilmarges in de praktijk: 35 cm bleek te groot om uit te voeren, 25 cm in de Waterhouderij Walcheren, 10 cm bij onderwaterdrains
- [Beleidskader omvang onderhoud watersysteem](https://repository.officiele-overheidspublicaties.nl/externebijlagen/exb-2017-14558/1/bijlage/exb-2017-14558.pdf) — aanvoercoëfficiënt 0,4 l/s/ha uit het Cultuurtechnisch Vademecum
- [KNMI, vernieuwde berekening neerslagtekort — vanaf 2026 jaarrond](https://www.knmi.nl/over-het-knmi/nieuws/vernieuwde-berekening-neerslagtekort-nu-hele-jaar-droogte-monitoring) en [achtergrondinformatie neerslagtekort](https://www.knmi.nl/kennis-en-datacentrum/achtergrond/achtergrondinformatie-neerslagtekort) — de referentielijnen mediaan en 5 % droogste jaren
- [Deltaprogramma, Deltascenario's 2024](https://www.deltaprogramma.nl/deltaprogramma/kennisontwikkeling-en-signalering/deltascenarios) — Ruim, Vlug, Warm, Stoom
- [IPLO, verdringingsreeks](https://iplo.nl/thema/water/beheer-watersysteem/verdringingsreeks/) — de vier categorieën, met veiligheid en onomkeerbare schade bovenaan

**Beslissen onder onzekerheid**

- [Haasnoot e.a., *Dynamic adaptive policy pathways* (2013)](https://www.sciencedirect.com/science/article/pii/S095937801200146X) en [Deltares, DAPP](https://www.deltares.nl/en/expertise/areas-of-expertise/sea-level-rise/dynamic-adaptive-policy-pathways) — de Nederlandse vorm van adaptief plannen, verweven in Adaptief Deltamanagement
- [Kwakkel, *The Exploratory Modeling Workbench*](https://www.researchgate.net/publication/318370885_The_Exploratory_Modeling_Workbench_An_open_source_toolkit_for_exploratory_modeling_scenario_discovery_and_multi-objective_robust_decision_making) — scenario discovery en many-objective robust decision making; de omgeving waarin een snel model als het onze thuishoort

**Agent- en toollaag**

- [MCP-roadmap 2026](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/) — de drie primitieven, stateless transport, tasks voor langlopend werk
- [Issue #28 in deze repo](https://github.com/HKV-products-services/talk-with-the-engineer/issues/28) — de discussie waaruit dit document volgt
