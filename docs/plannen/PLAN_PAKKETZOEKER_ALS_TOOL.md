# Plan van aanpak — de pakketzoeker als tool

`optimize.py` is af en wordt nergens aangeroepen behalve door zijn tests. Dit plan maakt
hem opvraagbaar via MCP en FastAPI, als **één tool in de bestaande toolset**, en legt vast
waarom de andere vormen — een aparte toolset, opsplitsen in sub-tools, of niet ontsluiten —
het niet zijn geworden.

De aanleiding is huishoudelijk (de opschoning van augustus 2026 vond een module van 1148
regels die alleen door tests wordt geïmporteerd), maar de vraag is inhoudelijk: de tien
rekentools beantwoorden *"wat levert deze ene maatregel op?"*, terwijl de vraag van de
waterbeheerder is *"welk pakket moet ik nemen, en wat kost het?"*. Die vraag kan de agent
nu alleen benaderen door zelf tools te orkestreren — zonder de omslagprijzen, de
bijna-optimale alternatieven en de bandbreedtes die de pakketzoeker wél geeft, en mét het
risico dat elke agent het nét anders doet.

---

## 0. Wat er wordt gebouwd, in één tabel

| deel | wat het doet | raakt de rekenkern |
|---|---|---|
| 1 | `OptimizeInput`/`OptimizeOutput` in `modelset_rules_of_thumb` | nee |
| 2 | de tool `find_package_given_protection` in de router (naam: zie §5.1) | nee |
| 3 | een vijfde `read_me`-module: `pakketzoeker` | nee |
| 4 | een voorbeeldnotebook in `docs/` plus de bijbehorende toetsen | nee |

De rekenkern (`optimize`, `optimise_mix`, `sweep_measure`, `switch_price_of`) verandert
niet. Dit plan is een ontsluiting, geen verbouwing.

Dit plan is fase 1 van een groter geheel: de budgetvraag, prijs-kwaliteit en
meekoppelkansen — de vlakvraag boven deze puntvraag — staan in
`VERKENNING_BUDGETVRAAG.md`.

---

## 1. Premisse — de tool bestaat al, alleen de deur ontbreekt

`optimize` doet precies wat een tool voor een agent moet doen, en dat is geen toeval maar
het ontwerp uit issue #28 en #30:

* hij is **workflow-vormig**: één aanroep beantwoordt de hele vraag, in plaats van tien
  aanroepen die de agent zelf moet componeren;
* hij is **uitlegbaar by design**: enumeratie buiten, SLSQP binnen, en het antwoord komt
  met `binding` (welke eis de prijs bepaalt), `priceless` plus omslagprijzen (wat er geen
  prijs heeft en wanneer dat het antwoord verandert), `near_optimal` (wat niet te
  onderscheiden is) en `ranges` (welke maatvoering binnen het budget vrij is);
* hij is **snel genoeg voor een synchrone tool, maar niet subseconde**: gemeten
  (2026-08-29, via de testsuite) kost één aanroep 4 tot 10 seconden, afhankelijk van de
  eisen. Dat past binnen gangbare tool-timeouts en vraagt geen asynchrone
  taakafhandeling, maar de description hoort te zeggen dat het antwoord seconden kan
  duren — een eerdere versie van dit plan zei "ruim onder de seconde", en dat was een
  extrapolatie uit de 0,06 ms per doorrekening die de zoekkosten eromheen negeerde;
* hij weigert al netjes: "geef minstens een eis" en "max_shortfall_mm vraagt om een
  deficit" zijn foutmeldingen die een agent direct kan verwerken.

Wat ontbreekt is uitsluitend de laag die de andere tien tools wél hebben: een
Pydantic-invoermodel, een registratie in de router, en een plek in de handleiding.

---

## 2. Het externe ijkpunt — waar het veld in augustus 2026 staat

Dit plan is getoetst aan de actuele ontwerppraktijk, en die wijst alle vier de keuzes
hieronder dezelfde kant op.

**Consolideren, niet versnipperen.** Anthropics richtlijnen voor tool-ontwerp
([Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents))
zeggen: bouw weinig workflow-vormige tools in plaats van veel API-wrappers — het canonieke
voorbeeld is `schedule_event` in plaats van `list_users` + `list_events` + `create_event`.
De pakketzoeker ís dat patroon. Dezelfde bron adviseert een keuze tussen beknopte en
volledige uitvoer per aanroep, en alleen hoog-signaal informatie terugsturen; §5.3 volgt
dat letterlijk.

**Contextkosten zijn de schaarse grootheid.** De tien huidige tooldefinities kosten al
~35.000 tokens vóór de eerste vraag (zie de kop van `read_me.py`). Het veldbrede antwoord
is progressive disclosure — definities klein houden en uitleg opvraagbaar maken
([code execution with MCP](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/1780)
rapporteert reducties tot 98,7 %). Deze toolset heeft dat patroon al: de `read_me`-tool met
modules (issue #9). De nieuwe tool krijgt dus een kórte beschrijving en een éigen
`read_me`-module, niet een lange beschrijving.

**De spec biedt niets dat we missen.** De MCP-specificatie
[2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28) verplaatst
langlopend werk naar een Tasks-extensie en introduceert MCP Apps (interactieve HTML bij een
toolresultaat). Tasks is voor ons irrelevant — de pakketzoeker is subseconde. MCP Apps is
een kans voor later (een pakketvergelijking mét bandbreedtes als beeld), maar geen
voorwaarde: het resultaat moet eerst als tekst en getallen kloppen.

**Het generieke alternatief is bewust niet de richting.** Er bestaan MCP-servers die de
LLM zelf constraint-modellen laten schrijven
([MCP-Solver](https://github.com/szeider/mcp-solver)). Dat verplaatst het domeinmodel naar
de prompt, en daarmee de auditeerbaarheid naar de agent. De kop van `optimize.py` zegt
waarom wij dat niet doen: *"het antwoord moet uit te leggen zijn; een black box niet."*
Het domeinmodel blijft in code; de agent stelt alleen de vraag.

---

## 3. Het besluit, in vijf punten

1. **Eén tool, in de bestaande toolset `RulesOfThumb`.** Geen aparte toolset: de
   pakketzoeker rekent op dezelfde polder, dezelfde bui en dezelfde droogtestatistiek als
   de tien bestaande tools, en een agent die beide werelden ziet kan het antwoord van de
   een met de ander controleren. FastMCP 3 kan toolsets per tag filteren
   ([What's New in FastMCP 3.0](https://jlowin.dev/blog/fastmcp-3-whats-new)); dat wordt
   pas interessant als er ooit een "licht" en een "volledig" profiel nodig is, en dat is
   nu niet zo.
2. **`sweep_measure` en `switch_price_of` worden géén eigen tools.** Het zijn
   uitvoerdetails van hetzelfde antwoord, geen eigen vragen. Omslagprijzen zitten al in
   het resultaat (`Package.priceless` plus `switch_price_of` wordt in de uitvoer
   ingevouwen); wie de sweep wil, vraagt om de volledige uitvoer.
3. **De uitvoer is standaard beknopt.** Níet de eenendertig pakketten, wél: het beste
   pakket, de niet te onderscheiden alternatieven, de bandbreedtes, de bindende eisen, de
   prijsloze maatregelen met hun omslagprijs, en welke mixen niet onderzocht zijn. De
   volledige lijst zit achter een vlag (§5.3).
4. **De lange uitleg gaat naar `read_me`, module `pakketzoeker`.** De tooldescription
   blijft in de orde van de bestaande beschrijvingen en verwijst ernaar.
5. **De validatie verhuist mee naar het invoermodel.** De twee `ValueError`s uit
   `optimize()` worden model-validators, zodat een verkeerde vraag als nette toolfout
   terugkomt (`as_tool_error`) mét de zin die uitlegt wat er ontbreekt.

---

## 4. In scope / buiten scope

**In scope**

* invoer- en uitvoermodellen, toolregistratie (MCP én FastAPI-route), `read_me`-module,
  voorbeeldnotebook, toetsen.

**Buiten scope, met reden**

* *Wijzigingen aan de rekenkern.* De kern is getest en gedocumenteerd; dit plan voegt een
  deur toe, geen kamer.
* *Een aparte toolset of server.* Zie besluit 1; heroverwegen zodra het aantal tools of
  de doelgroepen daar aanleiding toe geven.
* *De Tasks-extensie van MCP.* Gemeten 4–10 s per aanroep: binnen de timeouts, dus een
  taak-handshake is hier overhead. Voor de vlakvraag (minutenwerk) ligt dat anders — zie
  `VERKENNING_BUDGETVRAAG.md` §2.
* *MCP Apps / visuele uitvoer.* Kansrijk voor demo's, maar een tweede stap: eerst moet het
  tekstuele antwoord door de `terugkoppelen`-toets.
* *Exposen van `solve` als eigen tool.* `solve` is al ontsloten — hij zit ín de
  `*_given_*`-inversen. Een losse `solve`-tool zou hetzelfde antwoord met minder context
  geven.

---

## 5. Technische uitwerking

### 5.1 De naam

`find_package_given_protection`. Het werkwoord wijkt bewust af van `calculate_*`: de tien
bestaande tools rekenen een gegeven maatregel door, deze zóekt een pakket. Het
`*_given_*`-achtervoegsel blijft, want dat is de conventie die de richting van de vraag
draagt: gegeven het gewenste beschermingsniveau, vind het pakket.

Een eerdere versie van dit plan zei `find_cheapest_package_given_constraints`; de
herbezinning staat in `VERKENNING_BUDGETVRAAG.md` §9. Kort: *cheapest* verdween omdat het
antwoord uitdrukkelijk meer is dan het goedkoopste punt (near-optimaal, rollen,
omslagprijzen), en *constraints* omdat de agent-zijde in beschermingsniveaus praat —
herhaaltijden op beide assen plus de normen. De naam ligt definitief vast zodra de
`read_me`-module wordt geschreven, want naam en handleiding zijn samen de interface.

### 5.2 Het invoermodel

`OptimizeInput` in `models/modelset_rules_of_thumb/optimize.py`, samengesteld uit de
mixins die de bestaande tools al gebruiken (bui, peilband, systeem), plus:

* de drie eisen, elk optioneel: `max_dh_total_m`, `min_storage_mm`, `max_shortfall_mm`
  — dezelfde namen en semantiek als `Constraints`, inclusief de peil-as/waterstand-as
  scheiding uit de docstring;
* het droogtetripel voor het deficit, verplicht zodra `max_shortfall_mm` is gezet
  (dezelfde drie-of-geen-regel als bij de bestaande droogte-invoer);
* `max_mix_size: int | None` — met in de uitvoer de niet-onderzochte mixen, want stil
  begrenzen leest als "alles gedekt";
* `detail: bool = False` — zie §5.3.

Model-validators: minstens één eis gezet; `max_shortfall_mm` ⇒ droogtetripel aanwezig.
De teksten van de validators zijn de bestaande foutzinnen uit `optimize()`.

### 5.3 Het uitvoermodel

`OptimizeOutput`, standaard beknopt:

* `best`: maatvoering (afgerond via `round_significant`), `cost` met `cost_range`,
  `binding`, `priceless` met per prijsloze maatregel de omslagprijs;
* `near_optimal`: de niet te onderscheiden alternatieven, elk in dezelfde vorm, met de
  epsilon-verantwoording (het criterium komt uit `cost_epsilon`, niet uit een afgesproken
  percentage — dat verschil moet in de uitvoer benoemd blijven);
* `ranges`: per maatregel de vrije maatvoering binnen het budget;
* `unexplored_mixes`: alleen gevuld als `max_mix_size` is gezet;
* `problem_infeasible` plus, indien onhaalbaar, per eis de kleinste overschrijding —
  het antwoord "het kan niet" moet net zo uitlegbaar zijn als "het kan";
* `status` en taalvelden volgens het bestaande `MeasureOutput`-patroon, zodat de
  `terugkoppelen`-discipline (en `test_uitlegbaarheid`) onverkort geldt.

Met `detail=True` komen daar de overige pakketten bij, inclusief de onhaalbare, elk met de
reden. Dat is de sweep-informatie zonder een tweede tool.

### 5.4 De registratie

Zelfde stapel decorators als de bestaande tools: `@mcp.tool()`, `@router.post`,
`@auto_docstring(...)`, `@as_tool_error`. De description in één alinea: wat de tool zoekt,
welke drie eisen hij kent, en dat `read_me(modules=["pakketzoeker"])` de handleiding is.

### 5.5 De handleiding

`MODULES` in `models/modelset_rules_of_thumb/read_me.py` krijgt `pakketzoeker` erbij; de
tekst in `tools/toolset_rules_of_thumb/read_me.py` behandelt: wanneer deze tool en wanneer
de losse rekentools, de twee droogte-assen, wat `near_optimal` betekent en waarom er vaak
geen uniek antwoord is, wat prijsloos betekent en hoe de omslagprijs te lezen, en hoe je
een pakket terugkoppelt zonder er een besluit van te maken.

---

## 6. Toetsen

* **Schema**: de nieuwe tool draait mee in `test_mcp_schema` en `test_tools_router`.
* **Toegankelijkheid**: `test_toegankelijkheid.py` begrenst wat een agent te zien
  krijgt — totaalbudget van de definities, budget per tool en per beschrijving, en
  diepte en veldental van het invoerschema. De budgetten zijn gekalibreerd op de meting
  van 2026-08-29 met de marge van één ruime tool; deze tool moet erbinnen passen, en
  zijn lange uitleg hoort dus in `read_me` (§5.5), niet in de definitie.
* **Anker**: de uitkomsten uit `test_optimize` (het referentiepakket, de omslagprijzen,
  de infeasible-gevallen) als golden tests door de tool-laag heen — de deur mag het
  antwoord niet veranderen.
* **Uitlegbaarheid**: `test_uitlegbaarheid` dekt de nieuwe uitvoerteksten; geen verwijzing
  naar interne bestandsnamen of issues in wat de agent te zien krijgt.
* **Documentatie**: het voorbeeldnotebook valt onder de bestaande notebooktoets
  (`test_notebooks.py` leest elke cel tegen de invoermodellen van vandaag).
* **Evaluatie**: naast de unit-laag een kleine set agent-evaluaties (vraag → verwacht
  pakket), conform het advies uit de tool-ontwerprichtlijnen. Klein beginnen: de drie
  demoscenario's uit de kop van `optimize.py` zijn de eerste drie gevallen.

---

## 7. Volgorde

1. modellen plus validators, met de ankertests ernaast;
2. de toolfunctie en registratie;
3. de `read_me`-module;
4. het notebook en de evaluaties;
5. daarna pas — en alleen bij gebleken behoefte — MCP Apps of een toolsetprofiel.

---

## 8. Wat dit plan niet is

Geen refactor van `optimize.py`, geen herziening van de prijzen of de epsilon, en geen
uitspraak over de vraag of de pakketzoeker het *juiste* pakket vindt — dat is het domein
van de bestaande tests en de bevindingenrapporten. Dit plan gaat alleen over de deur:
dezelfde rekenkern, opvraagbaar, met een antwoord dat zich laat navertellen.
