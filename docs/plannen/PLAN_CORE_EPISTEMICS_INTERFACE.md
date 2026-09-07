# Plan van aanpak — de repo als world model: core, epistemics, interface

**Datum:** 7 september 2026
**Volgt op:** `bevindingenrapport-rekenkern-als-world-model.md`. Dit plan werkt **W9** uit —
de indeling — en neemt W1–W8 mee als de inhoud die in die indeling landt.
**Verhouding tot `PLAN_TOOLS_REFACTOR.md`:** dat plan zette §3.2 als bestandsindeling neer
en noemde daarin `Storm` als te bouwen type. De `to_state()`-kant is er gekomen, de
`Storm`-kant niet. Dit plan maakt die regel af en trekt de indeling door naar de drie lagen
die er sindsdien in zijn gegroeid.

---

## 0. Naamgeving

**Bestands-, module-, klasse-, functie- en veldnamen zijn Engels. Commentaar en docstrings
zijn Nederlands.** Dat is de bestaande conventie en niet een nieuwe: `PolderState`,
`retention_fraction`, `clamped_scan` en `simulate_deficit` staan er al zo, met Nederlands
eromheen. Alle namen in dit plan volgen die regel.

Twee uitzonderingen die bewust blijven:

* **`name_nl` en `share_of_nl` zijn Nederlandse wáárden en geen namen.** "bergen",
  "vasthouden" en "het landoppervlak" gaan letterlijk naar de terugkoppeling; die blijven
  staan zoals ze staan;
* **`PolderState` houdt zijn `Polder`.** Een polder is een Nederlands begrip zonder Engelse
  tegenhanger die hetzelfde zegt, en de naam is al ingeburgerd in de hele codebase.

Wat de regel wél raakt zijn de zes actieklassen; zie §5 — dat is de enige plek waar de
conventie tegen bestaande code botst, en het is een aparte beslissing.

---

## 1. Doel

Eén regel invoeren, hem in de mappenstructuur zichtbaar maken, en hem afdwingen:

> **`core/` is het world model. `epistemics/` zegt wat je van een antwoord mag geloven.
> `interface/` — vandaag MCP en FastAPI — is een view op één component van de core. De
> afhankelijkheid loopt één kant op: interface → epistemics → core.**

De repo stelt die regel al (`models/.../read_me.py:14`: "zodat de tool van het model afhangt
en niet andersom - dezelfde richting als de rest van de codebase"). Wat ontbreekt is dat de
indeling hem laat zien, en dat iets hem tegenhoudt als hij wordt geschonden.

**Buiten scope:** elke wijziging die een rekenuitkomst verandert. Fase A is uitsluitend
verplaatsen; `test_reference_ton.py` en `test_characterisation.py` zijn de poortwachter.

---

## 2. Waarom deze drie lagen, en niet vijf of twee

De huidige indeling — `agents/ models/ routers/ tools/ utils/` — is die van het
projecttemplate: hij groepeert naar **rol in het framework** (een pydantic-model, een
FastAPI-router, een tool). Dat werkte toen de repo een verzameling vuistregels was. Nu zit
er een world model in, en dan groepeert die indeling twee dingen bij elkaar die niets met
elkaar te maken hebben: `models/modelset_rules_of_thumb/` bevat `PolderState` én het
invoerschema van `store_given_h`, omdat het allebei pydantic is.

De drie lagen groeperen naar **wat het is**, en de test daarvoor is de vraag *"wat overleeft
als de interface verdwijnt?"*:

| laag | overleeft zonder MCP? | kent het woord "taal"? | wat het is |
|---|---|---|---|
| `core/` | ja | nee | ⟨S, A, E, T, R⟩ + γ + x\* — het model zelf |
| `epistemics/` | ja | ja, voor de formulering | aannames, spreiding, caveats, prijsloze posten, significantie |
| `interface/` | nee | ja | schema's, wrappers, uitlegzinnen, endpoints |

`epistemics/` staat er als eigen laag en niet in de core, omdat hij over antwoorden gaat en
niet over water: hij kent `PolderState` en `SolveResult`, maar de core kent hem niet. En hij
staat er niet in `interface/`, omdat hij niet aan MCP hangt — een notebook dat de core
direct aanroept wil dezelfde caveats. Dat is precies de reden dat hij een eigen naam
verdient: hij draagt op het scherm twee hele beats (*"de bodem van die som is vlak, dus het
antwoord is een band en geen punt"* en de grenzenplaat) en hij is vermoedelijk het meest
onderscheidende dat dit model tegenover een Ribasim heeft. Vandaag heet hij
`base_rule_of_thumb.py`.

---

## 3. De doelindeling

```
src/talk_with_the_engineer/
    core/                          het world model. Geen pydantic-invoer, geen taal, geen MCP
        state.py               S   PolderState, ConnectedState
        connection.py          S   Connection, OUTSIDE — de topologie: WIE er aan de rand zit
        system.py              S   SystemState, struct-of-arrays over knopen
        soil.py                S   SOIL_TYPES en de gebiedstypen
        actions.py             A   Action + de zes maatregelen
        exogenous/             E   het exogene deel, in drie soorten
            event.py               ExogenousEvent + Storm, Deficit
            boundary.py            BoundaryCondition — WAT de rand levert
            trend.py               Trend; leeg tot bodemdaling/zeespiegel komt. Voedt γ
            forcing.py             Forcing: één event, de randvoorwaarden, de trends
        stats/                 E   de bronnen waaruit een event wordt getrokken
            rainfall.py            + rainfall_patterns.json
            drought.py             + drought_statistics.json
            demand.py              + demand_posts.json
            runoff.py              de neerslag-afvoerrelatie en de afvoerkromme
        transition.py          T   de waterbalans, nat en droog
        inverse.py             T⁻¹ gulden snede, bisectie, haalbaarheid
        network.py             T   de cascade over knopen
        allocation.py          T   de verdringingsreeks over knopen
        package.py             x*  de pakketzoeker
        preference.py          x*  de voorkeursvolgorde over een rooster bedreigingen
        cost.py                R   UnitCost, ValueCurve, StepCost
        reward.py              R   investering + vermeden schade; nog leeg, met de signatuur
        reference.py               REFERENCE_POLDER en REFERENCE_STORM, één keer
        results.py                 SimulationResult, SolveResult, OptimumKind, LimitReason

    epistemics/                    wat je van een antwoord mag geloven
        assumptions.py             AssumedDefaults, Assumption, assumed_defaults
        caveats.py                 ModelCaveat + de 25 caveatfuncties
        uncertainty.py             Sensitivity, sensitivity_of, spread_of, supported_digits
        priceless.py               priceless_posts

    interface/                     een view op één component van de core
        schemas/
            base.py                StringTolerantInput, EngineerBaseModel, EngineerOutputModel
            area.py                AreaInput, WaterSystemInput, LevelBandInput → .to_state()
            rainfall.py            RainfallInput → .to_storm()
            drought.py             DroughtStatisticInput, SourceVolumeInput → .to_deficit(), .to_boundary()
            demand.py              DemandPostsInput
            retain.py store.py discharge.py supply.py
            cascade.py allocation.py optimize.py read_me.py
        tools/                     de twaalf dunne wrappers, namen ongewijzigd
        descriptions.py            de uitlegzinnen
        mcp/
            router.py              de twaalf endpoints en routes
            errors.py connections.py

    utils/                         blijft staan: al Engels, en niets ervan gaat over water
```

Vier dingen die deze boom zegt en de huidige niet:

1. **`base_rule_of_thumb.py` bestaat niet meer.** Zijn 2281 regels vielen uiteen langs de
   naad die er al in lag: E naar `core/exogenous/`, de aanname- en caveatlaag naar
   `epistemics/`, de invoermodellen naar `interface/schemas/`.
2. **`OUTSIDE` en `BoundaryCondition` staan in twee mappen, met opzet.** `connection.py`
   zegt wie er aan de andere kant zit — topologie, en dus toestand. `exogenous/boundary.py`
   zegt wat die knoop tijdens het event levert — exogeen. Vandaag zijn ze samengevouwen in
   de constante "oneindige berging, vast peil"; die aanname staat netjes opgeschreven
   (`connection.py:17`) en is nooit opengezet. De naam is `BoundaryCondition` en niet
   `Boundary`, omdat `BOUNDARY` in `system.py` al de índex van de randknoop is.
3. **`interface/` is vervangbaar.** Komt er een tweede protocol, een notebook-API of een
   webservice bij, dan komt die naast `mcp/`. Dat is wat "MCP is een moderne interface op
   een component van het world model" in de indeling betekent.
4. **`utils/` verhuist niet.** Eerdere versie van dit plan stelde `platform/` voor; dat
   schaduwt de stdlib-module `platform` en levert niets op. `utils/` is al Engels, gaat al
   nergens over water, en blijft waar het staat.

---

## 4. De verhuiskaart

Volledig, bestand voor bestand. `→` is een verplaatsing zonder inhoudelijke wijziging;
`⇒ splitsen` betekent dat het bestand langs een bestaande naad uiteenvalt.

### 4.1 Verplaatsen zonder splitsen

| vandaag | wordt |
|---|---|
| `models/modelset_rules_of_thumb/state.py` | `core/state.py` |
| `models/modelset_rules_of_thumb/connection.py` | `core/connection.py` |
| `models/modelset_rules_of_thumb/system.py` | `core/system.py` |
| `models/modelset_rules_of_thumb/soil.py` | `core/soil.py` |
| `models/modelset_rules_of_thumb/results.py` | `core/results.py` |
| `tools/toolset_rules_of_thumb/simulate.py` | `core/transition.py` |
| `tools/toolset_rules_of_thumb/solve.py` | `core/inverse.py` |
| `tools/toolset_rules_of_thumb/network.py` | `core/network.py` |
| `tools/toolset_rules_of_thumb/allocate.py` | `core/allocation.py` |
| `tools/toolset_rules_of_thumb/optimize.py` | `core/package.py` |
| `tools/toolset_rules_of_thumb/utils_rainfall.py` + `rainfall_patterns.json` | `core/stats/rainfall.py` |
| `tools/toolset_rules_of_thumb/utils_drought.py` + `drought_statistics.json` | `core/stats/drought.py` |
| `tools/toolset_rules_of_thumb/utils_demand.py` + `demand_posts.json` | `core/stats/demand.py` |
| `tools/toolset_rules_of_thumb/utils_discharge.py` | `core/stats/runoff.py` |
| `tools/toolset_rules_of_thumb/descriptions.py` | `interface/descriptions.py` |
| `tools/toolset_rules_of_thumb/{retain,store,discharge,supply,cascade,allocation,find_package,read_me}.py` | `interface/tools/` |
| `models/base.py` | `interface/schemas/base.py` |
| `models/modelset_rules_of_thumb/{retain,store,discharge,supply,cascade,read_me}.py` | `interface/schemas/` |
| `routers/tools_router_RulesOfThumb.py` | `interface/mcp/router.py` |
| `routers/{mcp_errors,setup_connections}.py` | `interface/mcp/{errors,connections}.py` |

### 4.2 Splitsen — vier bestanden, langs een naad die er al ligt

| vandaag | ⇒ | naar |
|---|---|---|
| `base_rule_of_thumb.py` (2281 rgl) | E | `core/exogenous/event.py` — `RainfallInput` wordt `Storm` |
| | aannames | `epistemics/assumptions.py` — `AssumedDefaults`, `Assumption`, `assumed_defaults` |
| | caveats | `epistemics/caveats.py` — `ModelCaveat` + de 25 `_*_caveat` |
| | spreiding | `epistemics/uncertainty.py` — `Sensitivity`, `supported_digits` |
| | prijsloos | `epistemics/priceless.py` — `priceless_posts` |
| | schema | `interface/schemas/{area,rainfall}.py` — `AreaInput`, `WaterSystemInput`, `LevelBandInput`, `BaseInput` |
| `models/.../actions.py` | A | `core/actions.py` — `Action` + de zes maatregelen |
| | R | `core/cost.py` — `UnitCost`, `ValueCurve`, `peilopzet_unit_cost` |
| `models/.../drought.py` | vocabulaire | `core/stats/drought.py` — `DROUGHT_REGIONS`, `DROUGHT_SCENARIOS`, `SOURCE_RIVERS` |
| | schema | `interface/schemas/drought.py` — `DroughtStatisticInput`, `SourceVolumeInput` |
| `models/.../{allocation,demand}.py` | vocabulaire | `core/allocation.py` — `CATEGORIES`, `DEMAND_POSTS`, `DEMAND_POST_CATEGORY` |
| | schema | `interface/schemas/{allocation,demand}.py` — de In/Out-modellen |
| `models/.../optimize.py` | grenzen | `core/package.py` — `REQUIREMENT_FIELDS`, `DROUGHT_WINDOW_DAYS` |
| | schema | `interface/schemas/optimize.py` — `OptimizeInput`, `OptimizeOutput` |

De vier splitsingen delen één regel: **een vocabulaire is core, een schema is interface.**
`CATEGORIES = (1, 2, 3, 4)` is de verdringingsreeks uit de wet en hoort bij het model;
`AllocationInput` is hoe een aanroeper daarover praat.

### 4.3 Nieuw

| bestand | waarom |
|---|---|
| `core/exogenous/boundary.py` | W2 — `BoundaryCondition`, vandaag een `getattr(..., np.inf)` op twee plekken |
| `core/exogenous/trend.py` | W7 — het protocol dat γ gaat voeden. Leeg, met de reden erin |
| `core/exogenous/forcing.py` | W2 — `Forcing`; pas vullen zodra er een tweede randvoorwaarde is |
| `core/reference.py` | W8 — de polder die nu 8× in `scripts/` staat en 0× in de core |
| `core/preference.py` | W1/W8 — de 312-bedreigingenbeat als corefunctie |
| `core/reward.py` | W6 — de lege stoel voor R, met de som van Van Dantzig als signatuur |
| `tests/test_core_boundary.py` | §7 — de laagregel uit §1, afgedwongen |

### 4.4 Verdwijnt

| bestand | waarom |
|---|---|
| `agents/rule_of_thumb.py` + `agents/` | W9 — registreert 2 van de 12 tools, docstring is nog "answer questions about ...". Het pad dat de π-beat beschrijft is MCP via `main.py`. Weg, of vervangen door een echte demo-agent die alle twaalf tools kent |
| `models/__init__.py`, `tools/__init__.py` | de her-exporteerlagen; `interface/mcp/router.py` importeert direct uit `interface/schemas/` en `interface/tools/` |

---

## 5. Beslispunt: de zes actieklassen

Dit is de enige plek waar de Engelse conventie tegen bestaande code botst.
`BergenAction`, `AfvoerenAction`, `VasthoudenAction`, `AanvoerenAction`, `PeilopzetAction`
en `PeilmargeAction` zijn Nederlandse identifiers. De toolnamen ernaast zijn al Engels, en
ze mappen één-op-één:

| vandaag | `name_nl` (blijft) | Engelse naam | bestaande toolnaam |
|---|---|---|---|
| `VasthoudenAction` | "vasthouden" | `RetentionAction` | `calculate_retention_*` |
| `BergenAction` | "bergen" | `StorageAction` | `calculate_store_*` |
| `AfvoerenAction` | "afvoeren" | `DischargeAction` | `calculate_discharge_*` |
| `AanvoerenAction` | "aanvoeren" | `SupplyAction` | `calculate_supply_*` |
| `PeilopzetAction` | "peilopzet" | `TargetLevelAction` | — |
| `PeilmargeAction` | "voorbemalen" | `PreDrainageAction` | — |

Voor: consistent met de rest, en de Engelse namen bestaan al aan de toolkant. Tegen: het
raakt een handvol testbestanden en `DEFAULT_ACTIONS`, en de Nederlandse namen zijn in
gesprekken over dit model de gangbare woorden geworden.

Aanbeveling: **wel doen, in fase A2**, want een half-Engelse actiecatalogus is de slechtste
van de drie uitkomsten — en `name_nl` houdt het Nederlands precies daar waar het hoort, in
de uitvoer. Maar het is een keuze en geen gevolg; als jullie de Nederlandse klassenamen
willen houden, verandert er niets anders in dit plan.

---

## 6. De route, en waarom in deze volgorde

Ik draai de volgorde uit mijn eerdere advies om. Eerst verhuizen, dan vullen — want de
E-modules uit W1 en W2 komen dan meteen in `core/exogenous/` terecht in plaats van in
`models/modelset_rules_of_thumb/`, waar ze een half jaar later weer weg moeten.

### Fase A — de verhuizing. Geen enkele regel logica verandert.

| WP | Wat | Aard |
|---|---|---|
| **A0** | Karakteriseringsnet aanzetten: `test_reference_ton.py` en `test_characterisation.py` groen vastleggen als vertrekpunt | vangnet |
| **A1** | §4.1 uitvoeren met `git mv`, imports herschrijven, `pixi run pre-commit` | mechanisch |
| **A2** | §4.2 uitvoeren: de vier splitsingen, plus §5 als die doorgaat. Dit is de enige stap in fase A die denkwerk vraagt | naad volgen |
| **A3** | §4.4: `agents/` en de her-exporteerlagen eruit | opruimen |
| **A4** | `tests/test_core_boundary.py` (§7) | afdwingen |
| **A5** | `README.md` §Project structure herschrijven: drie lagen in plaats van vijf framework-rollen. Dit is het punt waarop de repo zichzelf een world model noemt | zelfbeschrijving |

Fase A verandert geen enkel MCP-oppervlak: twaalf tools, twaalf endpoints, dezelfde namen
en dezelfde schema's. Voor een aanroeper is hij onzichtbaar.

**Wat fase A wél kost, en het is geen correctheid.** Elke open branch en elke PR die
`src/` raakt, krijgt merge-conflicten over de volle breedte, en `docs/plannen/` staat vol
verwijzingen naar de oude paden. Doe A1 en A2 daarom in één keer, op een leeg bord, en niet
naast ander werk in `src/`.

### Fase B — de inhoud die W1–W8 vraagt. Nu landt hij op zijn plek.

| WP | Wat | Uit |
|---|---|---|
| **B1** | `Storm`, `Deficit`, `BoundaryCondition` als frozen dataclasses in `core/exogenous/`; `.to_storm()`/`.to_deficit()`/`.to_boundary()` aan de toolgrens; alle coresignaturen annoteren | W1, W2 |
| **B2** | `core/reference.py` vullen; de 8 scripts, `tests/conftest.py` en `verify_wp8_anchors.py` erop laten leunen | W8 |
| **B3** | `days_to_discharge` en de bodemvelden naar `PolderState`; `transition.py` leest de bodem uit de toestand | W5 |
| **B4** | `tolerance_m` op `SolveResult`, gevuld uit `DH_TOLERANCE_M`, en in de terugkoppeling mee | W4 |
| **B5** | `core/preference.py` vullen; `gen_voorkeursvolgorde.py` wordt de dunne aanroep | W1 |

B1 eerst; B2, B3 en B5 leunen erop. B4 staat los.

**Let op bij B3.** Dit is het enige werkpakket in A of B dat een uitkomst *kan* verschuiven:
`days_to_discharge` heeft fallback 3 in `RainfallInput` en staat op 2 in de scripts en in
de ad-hoc `class Bui`. Wie de fallback verhuist, kiest welke van die twee de toestandsdefault
wordt — en die keuze hoort in `assumptions` zichtbaar te zijn. Karakteriseringstest eerst.

### Fase C — de kostenvorm. Ontwerpwerk, en niet meer alleen verplaatsen.

| WP | Wat | Uit |
|---|---|---|
| **C1** | `StepCost` naast `UnitCost` in `core/cost.py`: vast deel plus variabel deel, met band en bron per deel. Sluit aan op de tweede lezing die `replacement_cost` al aan de uitvoerkant heeft | W3, W6 |
| **C2** | Sturing als maatregel volgens issue #68: één actie, discreet wel/niet in de mixenumeratie, continue marge erbinnen. Posten voor strategie en protocollen ernaast, niet stil erin. `OptimumKind.SATURATED` blijft de rapportageplicht | W3 |
| **C3** | `core/reward.py` vullen met de som investering + vermeden schade; γ als discontering erover | W6, W7 |
| **C4** | Het A-slide van de presentatie meebewegen: vier maatregelen met twee ingangen, statische peilopzet in de zoeker, sturing als investeringsbeslissing — geen zes gelijkwaardige knoppen | W3 |

---

## 7. Hoe de laagregel wordt afgedwongen

Een architectuurregel die alleen in een plan staat, is een belofte. De repo heeft hier al
een mechanisme voor dat ze vertrouwt: `test_kern_properties.py:916` en `:1105` gebruiken
`ast.parse` om `np.` in de primitieven te verbieden, zodat de backendschakelaar een
eigenschap is en geen belofte. Dezelfde vorm, nu voor de laaggrens.

**`tests/test_core_boundary.py`** — over elke module in `core/`:

1. **geen import uit `interface/` of `epistemics/`, en geen `pydantic`.** Dit is de regel
   uit §1, en hij is de enige die vandaag wordt geschonden: `find_package.py:327` geeft een
   invoermodel als storm de core in;
2. **geen `getattr(x, "...", default)` op een forceringsargument.** Een ontbrekend veld moet
   een fout zijn en geen stille default. Dit is de faalmodus die W1 en W2 beide opleverden:
   dezelfde `OUTSIDE`-aanname twee keer, op twee plekken, met twee defaults;
3. **elk argument dat `storm`, `deficit`, `boundary` of `state` heet, is geannoteerd.**

En over `epistemics/`: geen import uit `interface/`. De richting is
interface → epistemics → core, en geen enkele pijl terug.

---

## 8. Wat er bij het uitvoeren anders bleek

Fase A en B zijn uitgevoerd. Vijf dingen die dit plan aannam en de code niet steunde; ze
staan hier omdat het plan de gedeelde referentie is en niet het commitlog.

**De vier "vocabulaire versus schema"-splitsingen in §4.2 bestaan niet.**
`DROUGHT_REGIONS`, `DEMAND_POSTS`, `CATEGORIES` en `REQUIREMENT_FIELDS` worden door `core/`
nergens gelezen: `core/allocation.py` krijgt `categories` als array binnen, en de rest zijn
enum-domeinen die een schema adverteert. Ze zijn heel naar `interface/schemas/` verhuisd.
De regel "een vocabulaire is core" is dus geen regel maar een verwachting - hij wordt er
een op de dag dat `core/allocation.py` de reeks zelf afdwingt in plaats van hem te krijgen.

**Er kwamen twee splitsingen bij, en beide waren een laagschending.** `results.py`
importeerde zijn eigen epistemieklaag en sloot een cykel (results → epistemics → inverse →
results), die de testsuite meteen als `ImportError` liet zien; de tooluitvoermodellen staan
nu in `interface/schemas/output.py`. En `solve.py` droeg vijf epistemiekfuncties
(`sensitivity_of`, `spread_of`, `uncertainty_for` en de twee `answer_for`-bouwers), die
alleen vanuit `interface/tools/` worden aangeroepen; die staan nu in
`epistemics/uncertainty.py`.

**Het verbod op `pydantic` in de kern uit §7 kon niet.** `PolderState`, `Action` en
`Connection` zijn frozen pydantic-modellen, en dat is een keuze over validatie en
onveranderlijkheid en niet iets van de interface. De grenstest verbiedt daarom
afhankelijkheid van de laag erboven, en niet pydantic zelf.

**`core/exogenous/` werd meteen een pakket in plaats van één module.** Zodra de
randvoorwaarde een eigen type kreeg - hij zat als `getattr(deficit, ..., inf)` op twee
rekenpaden met twee verschillende standaardwaarden - waren er drie bestanden, en dan is een
pakket eerlijker dan één module met drie secties. `forcing.py` staat er nog niet: dat is de
bundel, en die wacht op de tweede randvoorwaarde.

**WP B3 viel in twee helften met heel verschillend risico.** De bodem was mechanisch: die
velden stonden al aan de gebiedskant, dus `PolderState` kon ze overnemen zonder één
uitkomst te verschuiven. `days_to_discharge` was dat niet - hij raakt het schema van de
cascadetool, want `CascadeNode` had geen afvoerkarakteristiek en het hele systeem deelde er
een. Besloten: per knoop, met een systeembrede waarde op `CascadeInput` voor de knopen die
hem weglaten. Het invoerveld staat daarom op `WaterSystemInput` en niet op `AreaInput`: de
aanvoertools erven die laatste, en op de droge kant doet de relatie niets.

---

## 9. Wat dit plan niet doet

* **De rekenkern raken.** Geen formule, geen primitief, geen tolerantie verandert in fase A
  of B. `test_reference_ton.py` en `test_characterisation.py` zijn de poortwachter.
* **De MCP-oppervlakken veranderen.** Twaalf tools, twaalf endpoints, dezelfde namen en
  schema's. De omzettingen uit B1 zitten aan de binnenkant van de toolfunctie.
* **`core/exogenous/forcing.py` vullen vóór er een tweede randvoorwaarde is.** Een
  abstractie op één instantie. Het bestand staat er met de reden erin; `transition.py` houdt
  twee argumenten tot chloride er echt is.
* **`PeilmargeAction` (dan `PreDrainageAction`) bereikbaar maken vóór C1.** Zonder
  kostenvorm met een vast deel is dat de gratis hefboom uit issue #68, en dan koopt de
  zoeker inundatiemarge voor nul euro.
* **De T⁻¹-beat aanpassen.** Die klopt: het contrast op het scherm is solve-versus-sweep, en
  `solve.py:7` documenteert precies die overgang. Zie W4.
