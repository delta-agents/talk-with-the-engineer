# Een experiment op onze MCP-toolset, in drie polders

Een tweede deck naast `talk/mdp-presentatie`. Drie gebieden met een gepubliceerd rapport,
elk met dezelfde vraag door de MCP-endpoint van de rekenkern gelegd — en daarna het
experiment zelf: welke tools de agent aanriep, in welke volgorde, en wat dat over de opbouw
van die tools zegt.

De casussen, de bronnen en de open punten staan in
[issue #83](https://github.com/HKV-products-services/talk-with-the-engineer/issues/83).

## Draaien

    python3 -m http.server 8020 --directory talk/mdp-usecases

Dan http://localhost:8020/. Dubbelklikken op `index.html` werkt ook: geen ES-modules, geen
build step, geen netwerk. De drie kaarten zijn gewone `<img>`-verwijzingen naar SVG's in deze
map.

## Bediening

| toets | wat |
|---|---|
| → spatie Enter | volgende beat |
| ← Backspace | vorige beat |
| ↓ ↑ | volgende of vorige stap |
| 1 … 9 | rechtstreeks naar een stap |
| Esc | terug naar de titel |
| f | volledig scherm |
| ? | de hulp |

`#4.2` in de URL opent stap 4 op beat 2, ook als de pagina al open staat.

## De negen stappen

De deck is opgebouwd als een experiment, en **het onderzoeksobject is de toolset** — niet de
polder, en ook niet de vraag of het antwoord goed was. De drie gebieden zijn de experimentele
situaties, met opzettelijk **dezelfde twee beats**: gebied en vraag, en dan één grootheid met
de rapportconclusie ernaast.

| stap | beats | wat er staat |
|---|---|---|
| onderzoek | 1 | de vraag, de twee uitkomsten, en de hypothese als keten van drie schakels |
| opzet | 2 | een Claude-agent gekoppeld aan de toolbox van twaalf tools, en de procedure |
| Gnephoek | 2 | het gebied en de vraag · 45 ha tegenover +2 ha open water |
| Zuidplaspolder | 2 | het gebied en de vraag · 84 tegenover 152 cm stijging |
| Kockengen | 2 | het gebied en de vraag · 13 tegenover 29 mm/dag gemaalcapaciteit |
| resultaten | 1 | zes criteria × drie situaties |
| limitaties | 1 | tien limitaties, elk met de situatie waar hij zich liet zien |
| analyse | 5 | de volgorde, gebruikt tegenover ongebruikt, en dan de aanroepen per situatie |
| conclusie | 2 | de onderzoeksvraag beantwoord, en zeven aanbevelingen |

**De keten komt twee keer voor, en dat is de opzet van het verhaal.** Bij de vraag staat hij
kaal — `vindbaar → kiesbaar → gebruikt`, met die derde gesplitst in *waarvoor de tool is
ontwikkeld* of *om de vraag te beantwoorden*. Bij de conclusie staat dezelfde keten met een
oordeel erop: twee vinkjes en een tilde. Eén functie in `motor.js` tekent ze beide, zodat de
vorm niet uit elkaar kan lopen.

**De rangorde van de uitkomsten zit in de opbouw:** inzicht in het gebruik van de toolset is
primair, het antwoord op de gebiedsvraag secundair. Een geslaagd antwoord kan een slecht
ontworpen tool verbergen, en een gekraakt gebruik kan een goed antwoord opleveren.

**De drie aanroepplaten zijn één verhaal en niet drie tabellen.** Links de knopen zoals ze
de tool in gingen, rechts wat eruit kwam en de reden dat er een volgende aanroep kwam. Die
reden is de bewering: bij Gnephoek meet de eerste poging nul doorwerking, dus worden de knopen
anders verbonden en levert de tweede het getal waarvoor de tool bestaat. Bij de Zuidplaspolder
komen op zeven gebieden twee waarden terug, dus gaan er twee knopen in — en die zijn geen
gebied meer maar een variant. Bij Kockengen gaat de tool alleen nog in variantvorm de deur uit,
twee keer, want de bui staat één keer per aanroep. De getallen staan erbij als bewijs; de
beweging is het punt.

De analyse loopt van buiten naar binnen: eerst in welke volgorde er is aangeroepen, dan wat er
wel en niet is aangeraakt — met het netwerk uitgelicht, want dat is met zes van de vijftien de
meest aangeroepen tool terwijl de vraag drie keer over één gebied ging — en pas daarna wat er
precies in die aanroepen stond. De vier kleuren van de toolgroepen uit stap 2 komen daar terug.

Het detail dat niet op een slide past — de payloads letterlijk, de uitvoervelden met hun
schemabeschrijving, en waarom een aanroep met zeven knopen met twee getallen af kon — staat in
de comments van [issue #83](https://github.com/HKV-products-services/talk-with-the-engineer/issues/83).

## De bestanden

| bestand | wat |
|---|---|
| `index.html` | het omhulsel en de voordeur |
| `transcript.js` | **de opname** — de MCP-uitvoer, de rapportconclusies en de sessielog; hier staat elk getal |
| `inhoud.js` | de stappen en de beats; leest `transcript.js` |
| `motor.js` | de machinerie: beats, kop, toneel, toetsen, hash |
| `stijl.css` | de tokens uit de familie, en het idioom van elke plaat |
| `kaart-gnephoek.svg` · `kaart-zuidplas.svg` · `kaart-detol.svg` | de peilvakken per gebied, uit de leggers van Rijnland, HHSK en HDSR |

De platen die `toon` in `inhoud.js` kan kiezen: `onderzoeksvraag`, `opzet`, `methode`,
`casus`, `tegenover`, `resultaten`, `limitaties`, `volgorde`, `tools`, `casusaanroepen`,
`beantwoord`, `aanbevelingen`, `lijst`.

Valt een plaat om, dan komt er een zichtbare melding op zijn plek in plaats van een wit
scherm — het toneel is op dat moment al leeggemaakt, en een presentatie die halverwege wit
wordt is erger dan een lelijke slide.

## Leesbaar in een zaal

Een beamer is geen monitor, en dat is een maatvoeringseis en geen smaak. De maten volgen de
talk: de basis staat op `clamp(15px, 2.1vmin, 34px)` en niet op `vw`, want op een 4:3-projector
is de hoogte de beperking. Op 1080p geeft dat 23 px voor de basis en 25 px voor de zin die je
zegt; de talk zit op 18 en 23.

Drie regels die daaruit volgen:

* **niets onder 0,80em.** Wat kleiner moet, hoort er niet te staan. Alle labels en noten zijn
  daarop opgetrokken.
* **de tekst in een knoop breekt af, en kapt niet af.** SVG-tekst doet geen van beide van
  zichzelf: wat te lang is loopt gewoon over de rand van zijn vak. Dus wordt elke naam eerst
  opgemeten in een verborgen tekening en daarna over regels verdeeld, met de tweede regel in
  balans — "De Tol 2014 plus gebiedsvreemd water" hoort in twee regels en niet ingekort, want
  die naam is wat de aanroep bedoelde. Het vak groeit mee, en alle vakken in één tekening
  worden even hoog.
* **de tekeningen schalen in `em`.** Een knopendiagram krijgt zijn breedte in em en niet in
  pixels, zodat de labels erín meegroeien met de typemaat. Anders staan er 13 px letters op een
  scherm van vier meter. Er zit een plafond op de hoogte (`K_MAX_EM`), want twee tekeningen
  moeten samen met hun koppen tussen de stapkop en de bronregel passen; de breedte krimpt dan
  mee, anders staat de tekening in een leeg vak. En een aanroep mag zijn eigen vakmaat vragen:
  `smal` als er veel losse knopen naast elkaar staan, `breed` als één naam anders over twee
  regels moet en het vak daardoor tegen dat plafond loopt. Dat is nagemeten en geen smaak: op
  1024×768 zakten de labels van de Zuidplaspolder anders naar 9 px.
* **geen monospace, nergens.** Een veldnaam uit een schema staat in de data tussen backticks;
  die leestekens horen niet op een scherm. `el()` zet ze om in een span met kleur en gewicht,
  dus de naam leest als een naam en niet als code.
* **geen proza in een plaat.** Wie leest, luistert niet. De noten in de tabellen zijn
  steekwoorden; de zin staat in de voet en wordt gezegd. De onderbouwing staat in issue #83.

Nagemeten op 1920×1080, 1600×900, 1280×720 en 1024×768: alle 18 beats passen, geen plaat is
leeg, en geen label zakt onder de 11 px. Die controle is een lus over `INHOUD.stappen` die per
beat vijf dingen nakijkt:

1. **valt de bronregel achter de voet** — meet tegen de bovenkant van `.voet` en niet tegen
   `#app`. Dat is het venijn: `.toneel` heeft `overflow: hidden`, dus een te hoge plaat duwt de
   bronregel eruit en `#app` merkt daar niets van. Drie beats kapten hun bronregel af terwijl
   de check tegen `#app` "alles past" meldde.
2. staat er een melding van een omgevallen plaat;
3. bevat de plaat überhaupt tekst of een tekening — een keer viel een plaat stil om doordat
   zijn data was weggevallen, en de andere checks zagen dat niet;
4. staat er tekst buiten haar vak in een tekening, aan alle vier de kanten;
5. is het kleinste knooplabel nog 11 px of groter.

## Waarom er een transcript tussen zit

Een statische pagina spreekt geen MCP-server, en een presentatie die op een netwerkfout kan
stukvallen is geen presentatie. Dus staan de antwoorden opgenomen in `transcript.js`, en leest
`inhoud.js` daaruit. Er staat geen enkel getal met de hand in de deck — ook de calltellingen
en de tijden in de experiment-stap komen uit de log en niet uit herinnering.

De prijs daarvan is dat de opname veroudert. `transcript.js` draagt daarom een datum, en
opnieuw opnemen gaat zo:

1. start de MCP-server (`vuistregels`) en laat een client hem aanspreken;
2. vraag per casus, met het gebied uit `TRANSCRIPT.casussen[i].context` als invoer, de tools
   die in `TRANSCRIPT.experiment.per_casus[i].volgorde` staan — dat is precies de reeks die
   in deze sessie is aangeroepen;
3. neem `status`, `assumptions`, `sensitivity` en `caveats` mee. Die horen op het scherm: de
   handleiding van de toolset (`read_me(modules=["terugkoppelen"])`) staat erop dat `after`
   nooit zonder `status` gelezen wordt, en de laatste stap van deze deck bestaat uit de
   `caveats` zoals de tool ze geeft.

De gebiedsgegevens komen uit de leggers van de drie waterschappen en niet uit de rapporten;
de query's staan in `scratchpad/gnephoek/`, `scratchpad/zuidplaspolder/` en
`scratchpad/kockengen/`, elk met een README die de valkuilen in die open data beschrijft.

## Online

Deze map staat op **/usecases/** van de GitHub Page:
[hkv-products-services.github.io/talk-with-the-engineer/usecases/](https://hkv-products-services.github.io/talk-with-the-engineer/usecases/).
De workflow kopieert hem erheen zoals hij hier staat — geen build step, en de README gaat
niet mee. De talk zelf blijft op de wortel, de Quarto-documentatie op `/docs/`.

Heen en terug lopen kan via het hulppaneel (`?`): daar staat "de talk" en "de documentatie".
Dat is met opzet niet de voordeur, want die verdwijnt zodra de motor start.

Wat hiermee openbaar wordt: onze doorrekeningen van drie gebieden waarvan de rapporten al
openbaar zijn, plus de gebiedsgegevens uit de open data van drie waterschappen. Twee van die
gebiedsprocessen lopen nog, dus de duiding erbij is die van ons en niet van het waterschap of
de gemeente.
