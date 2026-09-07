# Bevindingenrapport rekenkern — de code naast het world model van de presentatie

**Datum:** 7 september 2026
**Scope:** de rekenkern in `src/talk_with_the_engineer/` op `main` (commit 5a7ac08), gelegd
naast `talk/mdp-presentatie/inhoud.js` — de negen stappen langs
`⟳ ⇒ M = ⟨S, A, E, T, R⟩ + γ ⇒ x* ⇒ π`.
**Methode:** niet adversarieel. Geen enkele bevinding hieronder is een rekenfout. De vraag
is uitsluitend **of elk lid van de tuple in de code een plek heeft die bij zijn rol op het
scherm past** — en waar de code een concept draagt dat op het scherm geen naam heeft, of
omgekeerd.

Twee vooraf gemaakte keuzes bepalen de rest van dit rapport:

1. **De kern *is* het world model; MCP is een interface op één component ervan.** Dat is
   geen herformulering maar een toetssteen: bij elk concept valt te vragen of de kern het
   definieert of de toolgrens. De repo heeft dat principe al opgeschreven —
   `models/.../read_me.py:14`, "zodat de tool van het model afhangt en niet andersom -
   dezelfde richting als de rest van de codebase". Bevinding W1 is de ene plek waar die
   richting is omgedraaid.
2. **E wordt een familie en geen tweetal.** Neerslag en droogte zijn de eerste twee
   exogene processen, niet de enige twee. Zout, rivierafvoer, bodemdaling en
   zeespiegelstijging staan al voor de deur. W2 werkt uit welke soorten dat zijn, want ze
   hebben *niet* dezelfde vorm, en één `Storm`-achtige dataclass voor alles zou de
   vergissing zijn die je één keer maakt.

---

## 1. Samenvatting

| # | Ernst | Waar | Bevinding |
|---|---|---|---|
| W1 | Hoog | kern + toolgrens | E is het enige lid van de tuple zonder type: `storm` en `deficit` zijn duck-typed door de hele kern, en `RainfallInput` — een toolinvoermodel mét `language` — vult die rol. De afhankelijkheidsrichting is hier omgedraaid |
| W2 | Hoog | ontwerp | E is een familie met **drie** soorten (gebeurtenis, randvoorwaarde, trend), en de code mengt de eerste twee nu ongemerkt in één object. De randvoorwaarde-plek bestaat al en staat op een constante: `OUTSIDE` |
| W3 | Middel | A + R | Peilmarge en peilopzet staan als zes-van-zes op het A-slide, maar zijn volgens issue #68 één maatregel: investeren in sturing. Het zwijgen van de code is correcter dan het scherm — en `UnitCost` kan die maatregel niet prijzen, want hij heeft geen vast deel |
| W4 | Middel | kern → uitvoer | De T⁻¹-beat klopt (solve i.p.v. sweep), maar de kern levert het bewijs niet mee: `SolveStatus.EXACT` reist zonder de tolerantie die het woord verdedigt |
| W5 | Middel | S vs E | De grens tussen toestand en weer loopt op twee plekken verkeerd: `days_to_discharge` zit op de bui, en de bodem zit náást de toestand in plaats van erin |
| W6 | Middel | R | R is in de code geen beloning maar kosten-onder-harde-eisen, en heeft geen vorm voor de dingen die hij nodig heeft: vermeden schade, trapkosten, en een tweede as |
| W7 | Laag | γ | γ heeft nul regels code, en dat is nu structureel: de trend-familie uit W2 is precies wat γ voedt, en de bodemdalingcasus staat al in `docs/plannen/` |
| W8 | Middel | x* | De laag waar het deck op uitkomt staat half buiten `src/`: referentiepolder 8×, referentiebui 8× in `scripts/`, en nul keer in de kern |
| W9 | Laag | indeling | De mappenstructuur is nog die van de tool-server-template; `base_rule_of_thumb.py` is 2281 regels met drie ongerelateerde lagen, waarvan de meest onderscheidende geen naam heeft |

De rode draad: **S, A en T zijn goed neergezet; E is het echte gat; R en γ staan op het
scherm en niet in de code; en x\* staat buiten de kern.**

En één ding dat niet in de tabel past maar er wel uit volgt: de epistemische laag —
`Assumption`, `Sensitivity`, de 25 caveats, `priceless_posts`, `supported_digits` — is het
meest onderscheidende dat dit model heeft, draagt op het scherm twee hele beats (de band in
plaats van het punt, en de grenzenplaat), en komt in geen enkel lid van de tuple voor. Zie
W9.

---

## 2. Wat is nagekeken en goed staat

Voordat de bevindingen: de drie leden die geen werk nodig hebben.

**S staat goed.** `PolderState` is een frozen pydantic-model met een expliciete
onderbouwing van wat er níet in hoort (`state.py:7`: "Bewust geen `EngineerBaseModel`: dat
voegt een `language`-veld toe, en dat hoort bij een toolaanroep en niet bij een toestand").
De peilband is bewust twee velden met een gedragsverschil erbij; `SystemState` is dezelfde
informatie als struct-of-arrays voor de breedte. Dat is precies de scheiding die een world
model nodig heeft.

**A staat goed als abstractie.** `Action` met `at()`, `apply()`, `current_magnitude()`,
`upper_bound()` en zijn eigen prijs is de juiste vorm, en de twee richtingen van het
A-slide vallen samen met de twee methoden. De maatregelcatalogus is uitbreidbaar zonder de
kern te raken. Wat er aan A schort staat in W3 en is een taxonomievraag, geen codevraag.

**T staat goed, en tweezijdig.** `simulate` is de heenrichting, `solve`/`evaluate` de
omkering met hetzelfde resultaatmodel voor beide, zodat de twee richtingen hetzelfde
haalbare bereik rapporteren. De vier gevectoriseerde stappen van `simulate.py` met
`clamped_scan` als enig primitief, en de backendschakelaar die door een AST-test wordt
afgedwongen — dat is een kern die je later kunt differentiëren zonder herbouw. Hier is
niets te herzien.

---

## 3. Bevindingen

### W1 — E is het enige lid van de tuple zonder type — Hoog

`storm` en `deficit` zijn duck-typed door de héle kern:

| plek | signatuur |
|---|---|
| `tools/.../simulate.py:613` | `simulate(state: PolderState, storm, ...)` |
| `tools/.../simulate.py:814` | `simulate_deficit(state: PolderState, deficit, soil=NO_SOIL)` |
| `tools/.../solve.py:155` | `solve(state: PolderState, storm, action: Action, target_dh_m)` |
| `tools/.../optimize.py:326` | `outcome_of(state: PolderState, storm, actions, quantities, deficit=None)` |
| `tools/.../network.py:89` | `node_forcing(system: SystemState, storm)` |

Overal `state` getypeerd en `storm` niet. De attributen worden los uitgelezen, deels met
`getattr(storm, "rain_volume_mm", None)` (`simulate.py:637`) en
`getattr(deficit, "available_source_volume_m3", np.inf)` (`simulate.py:900`) — dus een
ontbrekend veld is stil een default en geen fout.

Het dichtstbijzijnde dat E aan structuur heeft is `RainfallInput`
(`models/.../base_rule_of_thumb.py:138`), met een docstring die letterlijk zegt: *"De bui:
het exogene deel van de invoer."* Het is dus wél bedoeld als E. Maar het is een
**toolinvoermodel**: het erft van `AssumedDefaults` → `EngineerBaseModel` en draagt daarmee
een `language`-veld — precies wat `state.py:7` voor S expliciet weigert. En
`find_package.py:327` geeft dat invoermodel *zelf* als storm de kern in:

```python
result = optimize(state, input, constraints, deficit=deficit)
```

Dat is de omgedraaide afhankelijkheidsrichting uit de inleiding: de kern consumeert de vorm
van de MCP-interface in plaats van omgekeerd.

**Wat het kost, zichtbaar op het scherm.** De beat die het deck als de clou brengt — *"Leg
die eis langs alles wat de statistiek kan trekken en er komt een voorkeur uit"*, 312
bedreigingen — kón niet in de kern, want er is geen object dat een bedreiging is. In
`scripts/gen_voorkeursvolgorde.py:60` staat daarom een eigen `class Bui` met
`setattr`-mutatie. Diezelfde ad-hoc bui staat **acht keer** in `scripts/` (zeven `class Bui`
plus een geneste `class B` in `gen_frequentielijn.py:41`). Het woord dat op het scherm het
scharnier is, heeft in de code geen naam en acht definities.

### W2 — E is een familie met drie soorten, en twee ervan zitten nu ongemerkt in één object — Hoog

Dit is het ontwerpantwoord op W1, en het is bewust niet "`Storm` en `Deficit` als frozen
dataclasses". Zodra zout, rivierafvoer en bodemdaling meedoen, blijkt dat exogene processen
niet één vorm hebben maar drie:

| soort | wat het is | duur | wat het raakt | vandaag | straks |
|---|---|---|---|---|---|
| **gebeurtenis** | een trekking uit een statistiek waar de transitie *binnen* loopt | uren tot weken | de forcering | bui, neerslagtekort | hittegolf, stormopzet |
| **randvoorwaarde** | de stand van de buitenwereld waarmee het gebied uitwisselt, tijdens die gebeurtenis | een waarde of reeks, geen gebeurtenis | de uitwisseling aan de rand | *een constante* | chloride bij de inlaat, rivierafvoer, boezempeil, buitenwaterstand |
| **trend** | een langzame driver die S tussen twee beslissingen verschuift | jaren tot decennia | de toestand zelf | *niets* | zeespiegel, bodemdaling, landgebruik, klimaatscenario |

Drie observaties maken dit concreet in plaats van theoretisch.

**(a) De randvoorwaarde-plek bestaat al, en staat op een constante.** `connection.py:17`
schrijft het zelf op: `OUTSIDE` is "oneindige berging, vast peil — wat je erin pompt
verdwijnt, wat je eruit haalt is er altijd. Dat is precies de aanname die een model van een
losse polder stilzwijgend maakt, en hier staat hij opgeschreven." Zoutindringing landt
exact daar: het is geen gebeurtenis maar een eigenschap van `OUTSIDE` bij het inlaatpunt.
De tweede familie heeft dus al een gereserveerde stoel; hij is gevuld met een aanname die
netjes is opgeschreven en nooit is opengezet.

**(b) De code mengt gebeurtenis en randvoorwaarde nu al in één object, ongedeclareerd.**
`DroughtStatisticInput`/`SourceVolumeInput` (`models/.../drought.py:80,155`) draagt
`deficit_mm_per_day` en `length_days` — de gebeurtenis — én
`available_source_volume_m3` — de randvoorwaarde. `simulate_deficit` leest die tweede met
`getattr(..., np.inf)`, oftewel: dezelfde `OUTSIDE`-aanname, een tweede keer, op een andere
plek, met een andere default. En op het scherm staan die twee al netjes uit elkaar: het
droogte-slide heeft twee rijen, *"hoeveel er tekortkomt, en hoeveel de rivier dan nog
levert"*. Het deck maakt het onderscheid dat de code niet maakt.

**(c) De trend-familie is waarom γ leeg is.** Zie W7.

**En riviernatuur hoort hier niet in zijn geheel.** Dat is de ene waar ik tegen zou duwen:
de fysische dynamiek (afvoerregime, temperatuur, dynamiek van de oever) is E — deels
randvoorwaarde, deels trend — maar de *biodiversiteit* is geen forcering. Dat is een
waardering van de toestand, en dus een tweede as in **R** naast euro's en vermeden schade.
Als riviernatuur als exogeen proces wordt ingericht, ontstaat een doel dat als
randvoorwaarde vermomd is, en dan kan de pakketzoeker er niet mee wegen. Splits hem: de
forcering naar E, de waardering naar R (zie W6).

**Wat dit vraagt van de code.** Niet twee dataclasses maar een kleine module met een
protocol per soort naast `state.py`, en een `simulate` die een *bundel* forcering aanneemt
in plaats van één object — omdat zout en droogte samen optreden, en omdat de droogte
hierboven al twee soorten in één object bleek te zijn. De toolinvoermodellen blijven waar
ze zijn en krijgen een omzetting naar de kernvorm; dan staat de afhankelijkheidsrichting
weer goed en zijn de MCP-schema's wat ze horen te zijn: een interface op één component.

### W3 — peilmarge en peilopzet: het zwijgen van de code is correcter dan het scherm — Middel

Een eerdere versie van deze analyse adviseerde `PeilmargeAction` in `DEFAULT_ACTIONS` te
zetten "of van het A-slide af". Dat advies laat ik vallen: issue #68 komt met een derde en
betere lezing.

De feitelijke stand:

| maatregel | `Action` | toolpaar (→/←) | in `DEFAULT_ACTIONS` |
|---|---|---|---|
| vasthouden, bergen, afvoeren, aanvoeren | ✓ | ✓ | ✓ |
| peilopzet | ✓ | — | ✓ |
| peilmarge | ✓ | — | **—** |

`PeilmargeAction` is gemodelleerd en getest maar alleen bereikbaar vanuit `tests/`. Onder
de oude lezing was dat een gat. Onder de lezing van issue #68 is het een **symptoom**:
peilmarge en peilopzet zijn geen twee knoppen maar één maatregel — *investeren in optimale
operationele sturing* (telemetrie, MPC-achtige regeling, en de organisatie eromheen) —
waarbij statische peilopzet als losse maatregel overblijft. Zolang die maatregel niet als
investeringsbeslissing bestaat, is een bereikbare `PeilmargeAction` een gratis hefboom in
de zoekruimte. De kern doet dus het juiste door hem niet aan te bieden; het **A-slide is
wat niet klopt**, want dat presenteert zes gelijkwaardige knoppen met elk twee ingangen, en
dat zijn er vandaag vier.

**Wat de goede versie blokkeert, is de kostenvorm.** `UnitCost`
(`models/.../actions.py:39`) is lineair per eenheid met een band. Een sturingsmaatregel is
`vast (telemetrie + software + implementatie) + variabel (beheer)` — een trapkost. Zolang
`UnitCost` de enige vorm is, kan A deze maatregel niet dragen. Twee dingen daarbij:

* die trapkost bestaat al aan de andere kant: `replacement_cost`/`replacement_quantity` op
  `Action` (`actions.py:378,391`) is dezelfde tweede lezing, maar aan de uitvoerkant. Wat
  ontbreekt is de invoerkant;
* de zoekvorm hoeft *niet* verbouwd te worden. De pakketzoeker enumereert de mixen buiten
  en lost de continue maatvoering binnen op (`optimize.py:33`) — en dat is exact
  "wel/geen sturingssysteem × hoeveel marge je afspreekt". De discrete/continue splitsing
  die deze maatregel nodig heeft, ligt er al.

En de rapportageplicht blijft: `OptimumKind.SATURATED` (`results.py:163`) bestaat al precies
voor dit geval — voorbemalen verzadigt niet omdat de waterstand niet lager kan maar omdat
het gemaal niet sneller leegmaalt. Dat onderscheid moet ook mét een geprijsde
sturingsmaatregel blijven staan.

### W4 — de T⁻¹-beat klopt; de kern levert het bewijs niet mee — Middel

Een eerdere versie van deze analyse noemde *"uitgerekend, niet gezocht"* een te sterke
claim, omdat `solve()` een raster van 33 punten, gulden snede en bisectie tot `1e-4` m
gebruikt. Dat was te letterlijk gelezen, en de terechte tegenwerping is dat het het paard
achter de wagen spant.

Het contrast op het scherm is niet *gesloten vorm versus numeriek* maar **solve versus
sweep**, en de code documenteert precies die overgang. `solve.py:7`:

> "Voorheen werd hiervoor een sweep van 101 punten uitgerekend en daarin geinterpoleerd met
> `np.interp`. Dat klemt stil buiten het haalbare bereik en kost 101 doorrekeningen, ook als
> er maar een antwoord nodig is. Hier wordt in plaats daarvan gezocht: eerst het optimum van
> de maatregel, dan bisectie op de dalende tak."

Dat is de vorm waar lang naar is gezocht, en die vorm is precies wat inverse design
mogelijk maakt: één onbekende, één vergelijking, en een T die deterministisch is met een E
die eraan vastligt. De naburige beat zegt dat ook — *"Bij ons ligt de bui vast en beweegt de
polder"*. De beat blijft dus staan zoals hij staat.

**Wat er wél te repareren valt, is de andere kant.** `SolveResult` draagt
`status=SolveStatus.EXACT`, maar het getal dat dat woord verdedigt reist niet mee:
`DH_TOLERANCE_M = 1e-4` is een modulelokale constante in `solve.py:55` en `results.py` heeft
geen veld ervoor. Dat is opvallend in juist deze codebase, want alles daar reist mét het
antwoord: de aannames in `assumptions`, de spreiding in `Sensitivity`, de grenzen in
`caveats`, de prijzen als band. De exactheid — de enige claim die op het scherm met het
woord "precies" wordt gemaakt — is het enige dat op zijn woord geloofd moet worden.

**Advies:** een residu- of tolerantieveld op `SolveResult`, zodat de sterkste claim van het
deck auditeerbaar is met dezelfde middelen als alle andere.

### W5 — de grens tussen S en E loopt op twee plekken verkeerd — Middel

**`days_to_discharge`** is de neerslag-afvoerrelatie (Tabel 39,
Waterveiligheidsperspectief IJsselmeer): een eigenschap van bodem en drainage, dus van het
gebied. In de code staat hij op de bui (`base_rule_of_thumb.py:213`) en niet in
`PolderState`. Twee gevolgen:

* op het scherm moeten drie beats van de frequentielijn een voetnoot dragen — *"afvoer over
  twee dagen; met vier dagen schuift elke terugkeertijd mee"* — waarmee een
  gebiedseigenschap als onzekerheid over het weer verschijnt;
* in `gen_voorkeursvolgorde.py:69` staat `days_to_discharge = 2` op `class Bui`. In de
  312-doorrekening varieert het weer dus wél en de afvoerreactie van de polder niet. Dat is
  de gewenste uitkomst, maar hij komt tot stand doordat de eigenschap aan de verkeerde kant
  is vastgeschroefd — verplaats hem naar S en het is een keuze in plaats van een
  bijkomstigheid.

**De bodem.** Het S-slide toont tien getallen, waarvan `bodemvoorraad` en `bodemplafond`
twee. In de code zijn dat acht velden in `PolderState` plus twee ernaast, als
`SoilRelease`-argument van *alleen* `simulate_deficit`; `simulate` kent ze niet. De toestand
op het scherm en de toestand in de code zijn dus niet hetzelfde object, en het verschil is
precies de nieuwste aanwinst. Onder de world-model-lezing is dat een echte fout: een
voorraad is toestand, en een toestand die maar in één van de twee transities bestaat is geen
toestand.

### W6 — R is geen beloning, en mist drie vormen — Middel

Op het scherm is R een lid van de tuple: *"wat een pad beter maakt dan een ander."* In de
code is er geen beloning. Er is `UnitCost` per actie, er is `Constraints`
(`optimize.py:154`) met harde eisen, en de pakketzoeker minimaliseert kosten daaronder. Dat
is een ander object: een beloning weegt af, een constraint verbiedt. Er is geen `reward.py`,
geen `AvoidedDamage`, en geen plek waar een som van twee termen zou landen.

Drie dingen die R nodig heeft en niet heeft:

1. **de vermeden jaarschade.** Bekend en op het scherm als "nog invullen" gemarkeerd; de
   kostencurve-figuur is er expliciet om te laten zien dat de tweede helft van de som van
   Van Dantzig ontbreekt (`scripts/gen_kostencurve.py:6`). Het punt hier is niet dat het
   getal mist, maar dat er geen *vorm* voor is — de invulling wordt daarmee geen invulling
   maar een nieuw concept;
2. **de trapkost**, uit W3. Zonder vast deel in de kostenvorm kan de catalogus geen
   investeringsbeslissing dragen;
3. **een tweede as naast euro's**, uit W2. Zodra riviernatuur meedoet, is "beter" niet meer
   één grootheid. `priceless_posts` is vandaag het enige mechanisme daarvoor, en dat is een
   *melding* dat iets niet in euro's zit — geen as waarop je kunt wegen.

### W7 — γ is leeg, en dat is nu structureel — Laag

γ heeft nul regels code: geen discontovoet, geen tijdas, geen pad, nergens in `src/`. De
zaagtandfiguur komt niet uit de kern. Zolang γ alleen een ontbrekend getal was, was dat een
voetnoot.

Met W2 is het een gat geworden. De trend-familie — zeespiegelstijging, bodemdaling,
landgebruik, klimaatscenario — is precies wat γ voedt: exogene processen die S tussen twee
beslissingen verschuiven, en die daarom het verschil maken tussen "wat bouw je" en "wanneer
bouw je het". Dat is ook wat de π-stap als de enige noodzaak van een policy noemt: *"nodig
om te zeggen wat u doet met wat u volgend jaar weet."* En de eerste trend klopt al aan:
`docs/plannen/` bevat drie bodemdalings- en droogtecasussen die nog niet in git staan.

Advies zolang er niets gebouwd wordt: geef R en γ minstens een lege stoel in de code — een
module met de signatuur van de som en een expliciete `NotImplementedError` plus caveat. Nu
leest de kern alsof de tuple vijf leden heeft en zegt het scherm zeven.

### W8 — x* staat half buiten `src/` — Middel

Frequentielijn, kostencurve, maatregelcurven, pakkettabel, voorkeursvolgorde: dat is wat het
model *zégt*, en het is allemaal script. Concreet:

* de referentiepolder (`area_ha=1000, pct_open_water=5.0, single_pump_connection(1.5)`)
  staat **8×** in `scripts/`, nog eens in `tests/conftest.py:28` en nog eens in
  `scripts/verify_wp8_anchors.py:37`. In de kern staat hij **nul** keer;
* de referentiebui staat **8×** in `scripts/`, plus `REFERENCE_STORM` in `tests/conftest.py`.

De polder waarmee het hele deck rekent bestaat dus als tekst en niet als object. Eén
`reference.py` in de kern, met `scripts/`, `tests/` en `conftest` erop leunend, maakt "de
referentiepolder van duizend hectare" op het scherm tot één import. Dat is ook de voorwaarde
om de voorkeursvolgorde uit W1 ooit als kernfunctie te hebben in plaats van als script.

### W9 — de indeling is nog die van de template — Laag

`README.md` beschrijft `agents/models/routers/tools/utils` en noemt het project "a set of
water-management rules of thumb exposed as tools for LLM agents". Nergens in de
zelfbeschrijving van de code staat dat hier een world model in zit met een toestand, een
actieruimte en een transitie. Concreet:

* `models/modelset_rules_of_thumb/` mengt het domeinmodel (`state`, `actions`, `connection`,
  `system`, `soil`) met dertien bestanden toolschema's;
* `base_rule_of_thumb.py` is 2281 regels met drie ongerelateerde lagen: E (`RainfallInput`),
  de aannamelaag (`AssumedDefaults`, `Assumption`, `assumed_defaults`) en de epistemische
  laag (25 `_*_caveat`-functies, `Sensitivity`, `ModelCaveat`, `priceless_posts`,
  `supported_digits`);
* `agents/rule_of_thumb.py` registreert 2 van de 12 tools en heeft nog "answer questions
  about ..." als docstring. De π-beat zegt "de tools staan als gereedschap voor een
  taalmodel klaar" — dat pad is MCP via `main.py`, niet dit bestand.

De opvallendste is die derde laag in `base_rule_of_thumb.py`. Hij draagt op het scherm twee
hele beats — *"de bodem van die som is vlak, dus het antwoord is een band en geen punt"* en
de grenzenplaat — hij is vermoedelijk het meest onderscheidende dat dit model tegenover een
Ribasim heeft, en hij komt in geen enkel lid van ⟨S, A, E, T, R⟩ voor. Onder de
world-model-lezing verdient hij een eigen naam en een eigen module, niet een bestand dat
`base_` heet.

Dit is de enige bevinding die ik **niet** zou opvolgen op grond van het deck alleen:
hernoemen kost een dag en levert geen antwoord op. De twee splitsingen die wél lonen zijn
klein en staan hieronder.

---

## 4. Prioritering

**Nu, en samen ruwweg een dag — verplaatsingen, geen herzieningen. Geen enkele raakt een
rekenuitkomst.**

1. **W1 + W2 — E de kern in.** Een `exogeen/`-module naast `state.py` met een protocol per
   soort (gebeurtenis, randvoorwaarde, trend), `Bui` en `Tekort` als eerste twee
   gebeurtenissen, en de randvoorwaarde expliciet in plaats van als `getattr`-default. De
   toolinvoermodellen krijgen een omzetting; de kern gaat niet meer aan invoermodellen
   hangen. Dit is de bevinding waar de andere aan hangen.
2. **W8 — `reference.py` in de kern.** Referentiepolder en referentiebui één keer, en
   `scripts/`, `tests/` en `conftest` erop laten leunen.
3. **W5 — `days_to_discharge` en de bodem naar `PolderState`.** Dan is S in de code de tien
   getallen van het scherm.
4. **W4 — de tolerantie mee laten reizen op `SolveResult`.** Klein, en het maakt de sterkste
   claim van het deck auditeerbaar met dezelfde middelen als alle andere.

**Daarna, en dit is ontwerpwerk en geen opruimen.**

5. **W3 + W6 — de kostenvorm.** `UnitCost` met een vast deel, zodat "investeren in sturing"
   als maatregel kan bestaan, en de posten voor strategie en protocollen ernaast in plaats
   van stil erin. Pas daarna peilmarge de zoekruimte in. En het A-slide meebewegen: vier
   maatregelen met twee ingangen, statische peilopzet in de zoeker, en sturing als
   investeringsbeslissing — geen zes gelijkwaardige knoppen.
6. **W6 + W7 — de lege stoel voor R en γ**, met de som van Van Dantzig als signatuur en de
   caveat erbij.

**Niet doen op grond van dit rapport.**

* W9's grote herindeling. Wachten tot er iets bovenop moet.
* De T⁻¹-beat aanpassen. Die klopt; zie W4.
* `PeilmargeAction` bereikbaar maken zonder eerst de kostenvorm. Dat zou de gratis hefboom
  uit issue #68 terugbrengen.

---

## 5. Wat dit rapport niet heeft gedaan

Geen enkele uitkomst is nagerekend, en geen enkele bevinding is een rekenfout. De kern
rekent en is gevalideerd tegen `scripts/scripts_Ton/TttE_v03.xlsx`. Dit rapport kijkt
uitsluitend naar de vraag of de code de dingen waar hij over praat ook als dingen heeft — en
het antwoord is: voor de toestand, de maatregel en de transitie wel, voor het weer nog niet,
en voor de beloning en de tijd nog niet.
