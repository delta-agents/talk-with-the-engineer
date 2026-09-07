# From robots to polders: world models in hydrology

De presentatievorm: negen stappen door één formalisme, met de tuple als vaste
kopregel. Die kop is de inhoudsopgave — hij staat er altijd, en het lid waar je
bent staat omkaderd. Het toneel eronder hoort bij dat ene lid, en de voet draagt
de ene zin die je zegt.

```
┌──────────────────────────────────────────────────────────┐
│ ⟳ ⇒ M = ⟨ S , A , E , T , R ⟩ + γ ⇒ x* ⇒ π              │  de kop = de TOC
├──────────────────────────────────────────────────────────┤
│                                                          │
│   E     het weer            de rijen of een figuur       │  het toneel
│         getrokken, niet                                  │
│         gekozen                                          │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  ●●●○○○   de zin die de presentator zegt                 │  de voet
└──────────────────────────────────────────────────────────┘
```

## Draaien

    python3 -m http.server 8019

Dan http://localhost:8019/ — of dubbelklik gewoon `index.html`. Beide werken, en
dat is met opzet: er zijn geen ES-modules, geen build step en geen netwerk. Zie
"Waarom geen React" hieronder.

## Online

Deze map ís de GitHub Page van de repo:
[hkv-products-services.github.io/talk-with-the-engineer](https://hkv-products-services.github.io/talk-with-the-engineer/).
Er zit geen build step tussen — de workflow kopieert de map naar de wortel van
de site, precies zoals hij hier staat. Dat is de reden dat het geen React is:
wat op je eigen scherm werkt, werkt daar ook, en er is niets dat kan breken
tussen die twee.

De Quarto-documentatie (API-reference, demo, contributing) staat eronder op
[/docs/](https://hkv-products-services.github.io/talk-with-the-engineer/docs/).
Die is niet verdwenen, alleen niet meer het eerste wat je ziet.

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

Klikken werkt ook: rechts vooruit, de linkerstrook terug — maar alleen op het
toneel en de voet, zodat een klik om het venster naar voren te halen niet
ongevraagd een beat opschuift. In de kop is een klik een sprong naar dat lid.

**Op de video is een klik het geluid** en niet de volgende beat; anders kun je
het geluid niet aanzetten zonder de slide kwijt te raken. De clip start mét
geluid, maar elke browser weigert dat zolang er nog geen gebruikersactie op de
pagina is geweest. In een presentatie is die er meestal wel — je drukt op een
pijltje om bij die beat te komen — en anders valt hij terug op stil in plaats van
op stilstand, met een blokje "klik voor geluid" erbij. De eerstvolgende toets of
klik haalt het geluid alsnog binnen.

Bij een stap met veel beats gaan de puntjes in de voet op **twee rijen**. Boven
veertien wordt één rij een streepjescode; het raster vult rij voor rij, dus de
volgorde blijft van links naar rechts.

`#E.4` in de URL opent stap `E` op beat 4, ook als de pagina al open staat. Zo
kun je één beat delen in een issue of naast je andere slides zetten.

## De bestanden

| bestand | wat |
|---|---|
| `index.html` | het omhulsel |
| `Microduck Sim 2 Real.mp4` | de openingsclip, 465 kB — lokaal, niet van YouTube |
| `inhoud.js` | **de inhoud** — dit is het enige bestand dat je normaal aanraakt |
| `motor.js` | de machinerie: de beats, de kop, het toneel, de toetsen, de hash |
| `figuren.js` | de registratie — welke naam uit `inhoud.js` hoort bij welke plaat |
| `teken/iso.js` | de axonometrische projectie en haar primitieven |
| `teken/polder.js` | de polder van boven, het netwerk, nat en droog, de animatie |
| `teken/curven.js` | de frequentielijn, de kostencurve, de twee statistieken |
| `teken/schema.js` | het world model, de transitie heen en terug, de vulling |
| `teken/raster.js` | `kolommen()` en `lijsten()`: dit tegenover dat |
| `style.css` | de tokens, het raster, de kop, het toneel, de voet |
| `figuren.css` | het idioom van elke plaat: `f-`, `c-`, `i-`, `p-` en `g-` |
| `gegenereerd.css` | de acht `@keyframes` uit de rekenkern |

De indeling volgt de snelheid waarmee iets verandert, niet de techniek. `motor.js`
verandert bijna nooit, de platen per talk, de gegenereerde getallen wanneer de
kern verandert, en `inhoud.js` elke repetitie.

De **volgorde van de script-tags in `index.html` is de afhankelijkheidslijst**:
de projectie kent niemand, de platen kennen de projectie, het schema kent de
polder, de registratie kent alle platen, en de motor kent de registratie en de
inhoud. Elk bestand hangt zijn platen aan het ene globale `TEKEN` en haalt boven-
aan terug wat het gebruikt, dus wat een bestand nodig heeft staat in dat bestand.
Geen ES-modules: `import` valt op `file://` om op CORS, en script-tags niet.

## ⟳ — de brug die de titel belooft

De titel is *from robots to polders*, dus de talk hoort bij de robot te beginnen.
Stap `⟳` doet dat in tien beats, en de volgorde is: eerst het gebied, dan pas
het schema erover.

0. **het titelscherm.** Alleen de kop, en de voet zegt waar we beginnen: bij een
   mini-eendrobot van vijfentwintig centimeter. Er stond een ondertitel met de
   stelling, maar op een titelscherm is dat een tweede bewering naast een titel
   die het al doet.
1. **de clip.** Een microduck loopt, links in de simulatie en rechts op een echte
   vloer. Hij kan leren wat je wilt — een bal trappen, opstaan, iets oppakken —
   en dat is de reden dat hij hier staat. Eén beat; het fragment loopt door in
   plaats van te herstarten.
2. **nat en droog.** Eén plaat, twee bewegende polders onder elkaar: te veel
   water boven, te weinig water onder. Dezelfde polder moet ze allebei doorkomen,
   dus samen zijn ze de vraag — na elkaar zijn het er twee, en dan vergelijkt de
   zaal ze niet.
3. **de kale polder.** Land, en een strook open water. Zonder deze beat staat de
   eerste ingreep er al op zodra de plaat verschijnt, en dan zie je hem niet
   bíjkomen.
4–7. **de vier maatregelen, laag voor laag.** Eerst vasthouden, dan bergen, dan
   het gemaal, dan de inlaat. De plaat blijft staan en elke beat legt er één
   ingreep bij. Aanvoeren komt als laatste en van **buiten** de plaat af: het is
   de enige van de vier die tegen droogte werkt, en daarmee de brug naar de
   verdeling twee beats verderop.
8. **de twee koppelingen.** Weer één plaat met twee helften: boven hangen drie
   gebieden als een ketting aan elkaar, onder trekken ze aan dezelfde bron.
9. **het schema, gevuld voor de microduck.** Toestand, actie, exogeen, transitie,
   beloning, policy — met de symbolen die daarna elk hun eigen stap krijgen.
10. **hetzelfde schema, gevuld voor de polder.** De tekening blijft staan en
   alleen de inhoud wisselt; de twee ringen erbij zetten hem op het standpunt van
   de strateeg, en dat is de reden dat de rest van de talk ergens over gaat.

Beat 9 en 10 zijn in de code één `wereldmodel(...)` met twee vullingen, zodat
"hetzelfde schema" ook letterlijk waar is en niet twee SVG's die uit elkaar
kunnen lopen. Elke vulling draagt een **plaatje in dezelfde vrije hoek** — de
eend zelf, en de polder van boven van drie beats terug. Zonder dat moet de zaal
uit de bijschriften halen over wie dit schema gaat; met dat plaatje is het één
blik, en omdat het op dezelfde plek staat verspringt er bij de wissel niets.

### De twee ringen, en waarom ze hier staan en niet later

Het idioom komt van de plaat bij `T`: een ring markeert wat je **niet weet**. Hier
zijn het er twee, om `e` en om `a`, en ze gaan apart aan omdat het twee soorten
niet-weten zijn.

| ring | wat de strateeg zegt |
|---|---|
| om `e` | dit kan ik niet kiezen, en het is niet één toekomst — het zijn er duizenden |
| om `a` | dit kan ik wél kiezen, en ik weet niet hoe het uitpakt |

Tussen die twee zit de verlamming: er valt zo geen keuze te maken. Dat is het
probleem waar deze talk over gaat, en het is een probleem van een mens en niet
van een model.

Ze staan op de **eerste** beat waarop de polder in het schema staat, en niet
later bij `E`. Wie de vraag pas bij het weer stelt, heeft een halve stap lang al
een andere stand gezet — en alles daarna wordt gehoord in de stand die hier
gezet wordt. Ze staan om de **letter** en niet om het bijschrift, want het gaat
om het lid van de transitie en niet om het voorbeeld eronder.

Wat hier stond was een aankondiging van ons eigen tekort — *de rest van deze talk
gaat over wat er dan nog ontbreekt*. Dat is een ware zin op de verkeerde plek: op
de slotbeat van de eerste stap zet hij de hele talk in de stand "wij zijn er nog
niet", terwijl de strateeg daar met zijn eigen vraag hoort te zitten.

De lus in dat schema loopt **rechthoekig** om de twee dozen heen: de maatregel
gaat links omhoog naar binnen, de volgende toestand komt rechts naar buiten en
zakt daar weer af naar wie kiest. Dat is niet cosmetisch — met een diagonale
teruglus liep er een lijn dwars door "de volgende polder", door de beloning, en
door het label van de maatregel zelf. Nu kruist geen lijn een letter, en dat is
nagemeten door de paden af te lopen en tegen de tekstkaders te toetsen.

De teruglus **takt af** van de pijl van de volgende toestand, met een knooppunt
op dat punt. Zo blijft de pijl naar buiten kloppen als de policy weg is: de
maatregel is een *ingang* van de transitie en hoort dus bij het transitiedeel,
niet bij de policy.

In de doos staat in beide vullingen één regel, en die is even lang opgebouwd:
**Physics Engine** bij de microduck, **Waterbalans Engine** bij de polder. Dat is
de wissel in twee woorden — hetzelfde slot, andere motor — en het maakt de
tekening ook letterlijk uitwisselbaar in plaats van alleen qua vorm.

Er stonden bij de polder twee regels onder die naam: "geen neuraal netwerk" en
"opgeschreven vuistregels". Die claim staat nu nog in de voordeur van
`index.html` en op de Ribasim-plaat bij `T`, maar niet meer in het schema zelf —
wil je hem daar terug, dan is dat een tweede regel in de doos en geen bijschrift.

Het schema kent twee weergaven van dezelfde vulling. Gedempt (`wereldmodel(…)`)
laat de delen die uit staan flauw staan, en dat is wat je wilt terwijl je ze één
voor één aanzet. Hard (`wereldmodel(…, true)`) zet ze op nul, en dat is wat je
wilt op de beat die zegt *dit hoort er níet bij* — half zichtbaar is daar het
verkeerde antwoord. `T` en `π` gebruiken de harde weergave.

En de reden dat die brug draagt, is een feit en geen analogie: de microduck heeft
**geen geleerd** world model. Zijn policies worden getraind met **PPO** in
**mjlab (MuJoCo Warp)** — een opgeschreven natuurkundemodel. 4096 werelden
parallel, één tot twee uur op één GPU voor een werkende gang, 61 observaties in
en 14 gewrichtsdoelen uit op 50 Hz, geëxporteerd naar ONNX en onboard uitgevoerd.

Dat is precies onze opzet. Robotica schrijft zijn transitie ook op, en heeft daar
de tweede stap al op gezet; wij hebben de transitie en die stap nog niet. Zeg dus
**niet** dat de dynamica in robotica geleerd wordt omdat je hem niet kunt
opschrijven — voor een lopende robot is dat onjuist, en iemand uit de robotica
weet dat.

Onderaan het schema staat in beide vullingen een **doel**: "doel: leer lopen" en
"doel: klimaatbestendig, tot 2100". Dat is niet hetzelfde als de beloning ernaast.
De beloning is het signaal per stap — *vooruit komen en niet omvallen*, of
*schade voorkomen en wat dat mag kosten* — en het doel is de taak waarop je
traint. Een policy heeft ze allebei nodig, en ze op één plaat naast elkaar zetten
is de eerlijkste uitleg van wat een policy is.

Waar de asymmetrie dan zit, nu beide regels een doel zijn: in het woord **zou**.
De robot heeft een policy die "elke stap kiest wat hij doet"; de polder heeft er
een die "zóu kiezen wat je doet, en wanneer". Dat is één woord, en het draagt de
hele stand van zaken. `π` zegt het daarna nog een keer met zoveel woorden.

Let op het jaartal. De landelijke doelstelling uit de Deltabeslissing Ruimtelijke
Adaptatie is **2050**, niet 2100. Het jaartal hier is de horizon van deze deck
zelf — de zaagtand bij `γ` loopt van 2026 naar 2100, en dat is de termijn waarop
zeespiegel- en klimaatscenario's uitspraken doen. Wie in de zaal aan 2050 denkt,
hoort iets anders dan er staat; noem dat verschil als het opkomt.

Waar PPO in beide gevallen om dezelfde reden nodig is: de transitie is exact,
maar de beslisvariabele heeft geen bruikbare gradiënt. Contact is niet-glad; een
geheel bouwjaar heeft er helemaal geen.

Tweede aansluiting, en die is voor een waterzaal misschien nuttiger: de duck
randomiseert batterijspanning, wrijving en commandovertraging omdat hij de vloer
niet kent. Wij randomiseren over KNMI'23-scenario's, herhaaltijden en regio's
omdat we 2100 niet kennen. Dezelfde truc, en het laat `E` dubbel werk doen.

Bronnen: [pollen-robotics/microduck_rl](https://github.com/pollen-robotics/microduck_rl) ·
[Pollen Robotics](https://pollen-robotics.com/microduck/) ·
[MarkTechPost, 28 augustus 2026](https://www.marktechpost.com/2026/08/28/pollen-robotics-hugging-face-microduck-399-open-source-rl-biped-robot/)

### De vier maatregelen komen laag voor laag

Ze stonden een tijd op één beat, alle drie tegelijk: dit publiek kent
wateroverlast, watertekort en de maatregelen die erbij horen, en een opbouw
*léért* dan iets wat de zaal al weet. Toch staan ze er weer als drie beats.

De reden is niet de uitleg maar de **plek**. Vasthouden, bergen, afvoeren en
aanvoeren komen straks terug als knoppen bij `A` en met een prijs bij `R`, en dan
helpt het dat elke ingreep zijn eigen hoek van de plaat heeft gekregen in plaats
van dat ze samen één beeld waren. Ze kosten hier weinig: de plaat blijft staan en
er komt per beat één laag bij.

Elk woord staat **naast zijn eigen vlak** en niet in de rand van de plaat. Dat
was het niet: "vasthouden" hing negentig eenheden onder het bruine vlak en "open
water" stond rechtsonder terwijl de watergang linksboven binnenkomt. Op een
beamer moet je in één blik zien welk woord bij welk vlak hoort, en dat kost een
label dat er tegenaan ligt.

De **kale plaat** gaat eraan vooraf, en dat is geen inleiding maar de eis van een
opbouw. Staat vasthouden er al op zodra de plaat verschijnt, dan zie je hem niet
bijkomen — en dat bijkomen is het enige wat een opbouw doet dat één beat niet
doet.

Wat blijft is de tweedeling die niet bekend is: nat is een **ketting** en droog een
**verdeling**. Die twee staan boven elkaar op één plaat en niet op twee beats,
want het **verschil** is het punt — en twee koppelingen die je na elkaar ziet
vergelijk je niet. Om dezelfde reden staan wateroverlast en watertekort op één
plaat: een polder moet ze allebei doorkomen.

## Het verloop boven de tijdbalken

Naast elke bewegende plaat staat een compact grafiekje, en het deelt zijn x-as
met de tijdbalk eronder: de dagteller die daar loopt is dus ook de leeswijzer van
de grafiek. Beide komen uit dezelfde rekenkern als de animatie ernaast — zie
`scripts/gen_verloop.py`.

**Nat is de neerslag-afvoergrafiek** die elke hydroloog kent. De neerslag hangt
omgekeerd aan de bovenrand, de afvoer van het land ligt er als vlak onder, en
tussen die twee zit de **vertraging**: de bui piekt op dag vier met 29 mm, de
afvoer een dag later met 3,07 l/s/ha. De streeplijn is wat het gemaal aankan —
1,5 m³/s over 950 hectare land is 1,58 l/s/ha — en wat daarboven uitsteekt is de
titel van de grafiek: een oplopend tekort aan afvoercapaciteit. Dat vlak is
precies de stijging die u op de plaat ernaast ziet gebeuren, en het staat in twee
tinten omdat er twee dingen na elkaar gebeuren (zie hieronder).

### Twee tinten die in beide beelden hetzelfde betekenen

Boven de gemaallijn gebeuren er **twee dingen na elkaar**, en de doorrekening zegt
precies wanneer het omslaat. Eerst loopt de berging vol; zodra het peil door de
norm van 30 cm gaat staat het water op het **land**. Gemeten op de
referentiepolder: dat gebeurt op **dag 4,93** en het zakt er weer onder op **dag
6,38**.

| wat | tint | waar hij nog meer staat |
|---|---|---|
| de berging loopt vol | `--berging` | de vijver op de plaat, die zich vult |
| het land loopt onder | `--overstroming` | de watergang op de plaat, buiten zijn oevers |

Dat is de hele reden dat de plaat en de grafiek naast elkaar staan: dezelfde
kleur hoort in beide beelden bij hetzelfde verschijnsel, en dan hoeft er geen
legenda bij. Nagemeten dat ze ook op dezelfde dag omslaan — de plaat wisselt van
tint tussen dag 4,8 en 5,2, en de liniaal staat dan precies op de rand van het
donkere vlak in de grafiek.

**Beide tinten staan dekkend, en dat is geen smaak.** Ze stonden eerst
doorzichtig, en toen kwam dezelfde kleurwaarde er links anders uit dan rechts: op
de plaat ligt de vijver op een lichte dekplaat, in de grafiek ligt het vlak op een
al blauw gekleurd oppervlak. Gemeten scheelde dat 0,07 in rood — zichtbaar genoeg
om de koppeling te breken die de hele opzet draagt. Dekkend is de kleur op beide
plekken per definitie gelijk; nagemeten `rgb(158, 190, 214)` en `rgb(30, 91, 128)`
in beide beelden, en in donkere modus `rgb(70, 119, 156)` en `rgb(158, 211, 242)`.

Alleen de watergang **binnen** zijn oevers houdt zijn eigen doorzichtige blauw:
die hoort niet bij dit paar, en doorzichtig laat de plaat eronder meespelen.

De tint van de watergang zit in de **keyframes** en niet in een klasse: hij hangt
aan het peil, en dat is precies wat `gen_polderanimatie.py` per stop uitrekent.
Tussen twee stops kruist de kleur over in een halve seconde, en dat leest als
water dat over de kant komt.

Beide vlakken in de grafiek staan er als **knipvorm** op één en dezelfde curve, en
niet als drie losse paden: zo kan er niets uit elkaar lopen. De berging krijgt
twee knipvormen — vóór dag 4,93 en ná dag 6,38 — en de overstroming de strook
ertussen.

De curve is **vloeiend en monotoon**. De getallen zijn de dagwaarden uit de
rekenkern; de interpolatie ertussen is Fritsch-Carlson, en die is gekozen omdat
hij geen piek of dal verzint dat in de reeks niet zit. Een trapje van negen
treden leest als een staafgrafiek van iets anders.

**Droog is de spiegel, maar niet van de vertraging.** Droog is er geen piek om op
te wachten, alleen een optelsom die doorloopt. Het tekort zakt van de bovenrand
weg naar 279 mm over het groeiseizoen; de eigen voorraad van de polder is de
blauwe lijn die na tien dagen vlak wordt op 15 mm. Het bruine vlak ertussen is de
264 mm die van buiten moet komen, en dat is de hele reden dat droogte hier een
**aanvoervraag** heet en geen bergingsvraag.

Die twee grootheden staan als **vlak** en niet als lijn. Vijftien millimeter
tegen tweehonderdnegenentwintig is als lijn een haartje onder de bovenrand, en
als vlak een streepje blauw tegen een wig bruin — en dat verschil is de hele
boodschap.

**Geen assen, geen getallen op de grafiek.** Wat er staat is een vorm en een
titel; de maat staat in de tijdbalk eronder en in deze README. Een compact
grafiekje van tweehonderdzestig eenheden breed dat óók zijn assen moet uitleggen,
legt niets meer uit.

Om dezelfde reden staat er bij de droge grafiek **geen** naam bij de twee vlakken.
"eigen voorraad" en "moet van buiten komen" stonden er onder elkaar en werden
gelezen als één zin — *eigen voorraad moet van buiten komen* — wat het omgekeerde
zegt van wat de plaat laat zien. Twee labels die samen een verkeerde zin vormen
zijn erger dan geen labels: de titel draagt de boodschap al, en het streepje
blauw tegen de wig bruin doet de rest.

Door beide loopt een **liniaal** die met de klok meebeweegt: hetzelfde
`p-dag`-blok dat de teller op de balk eronder verschuift, en over dezelfde 260
eenheden. Nat loopt hij in vijftien seconden rond, droog in achttien — de twee
klokken van de platen ernaast.

Dat de plaat en de grafiek dan ook echt dezelfde dag tonen, is **nagemeten** en
niet afgeleid. Bij negen standen van de klok is de regenintensiteit op de plaat
naast de staafhoogte in de grafiek gelegd, en ze komen tot op drie decimalen
overeen: 0,209 tegen 0,208 op dag 2,5, 0,722 tegen 0,722 op dag 4,5, 0,114 tegen
0,113 op dag 7,5. Hetzelfde voor de overstroming — de watergang zwelt tussen dag
5 en dag 6,3, precies waar de doorrekening boven de norm van 30 cm uitkomt.

Er zit één uur speling in, en die is te verwaarlozen: de keyframes lopen van uur
nul tot uur 215 en de liniaal van dag nul tot dag negen, dus aan het eind van de
lus staat de plaat een uur achter. Op een venster van negen dagen is dat een
halve procent.

Wat **niet** hetzelfde is: de blauwe curve is de afvoer van het **land** naar de
watergang, en het gemaal is de streeplijn erboven. Op de plaat ernaast is de
zichtbare afvoer juist het gemaal. Twee verschillende debieten dus, en het vlak
ertussen is waarom de polder volloopt. Op het scherm staat dat niet — er staan
geen asnamen — dus dat is een zin voor de spreker.

## De animaties

Twee bewegende beelden, en ze delen één gegenereerd bestand: `gegenereerd.css`.

**De bui van boven** (bij `⟳`, de tegenhanger van de microduck-clip, en boven de
droge helft op dezelfde plaat). Van boven zie je geen diepte, dus een stijgend
peil is onzichtbaar zolang het in de
watergang past. Wat je wél ziet is het moment dat het eroverheen gaat: dan zwelt
de watergang en loopt het land onder. De overstroming en de watergang zijn
daarom **één vlak** — van boven is een overstroming niets anders dan de
watergang die buiten zijn oevers komt.

**De peilband in doorsnede** (bij `T`). Dit is de enige stap waar de band zelf
het argument is, en een band is van boven niet te zien.

**Het seizoen van boven** (bij `⟳`, onder de bui op dezelfde plaat, en er de
spiegel van). Andere klok: geen
negen dagen maar 1 april tot 1 oktober, want dat is de tijdschaal waarop een
tekort zich opbouwt. Die klok hangt aan de **droge groep** en niet aan de plaat,
anders zou de bui erboven er ook op gaan lopen. Hij loopt in 18 seconden rond
tegen 15 voor de bui —
een half jaar mag langer duren dan negen dagen, maar niet zóveel langer dat de
zaal op het beeld staat te wachten. De watergang krimpt binnen zijn oevers en het land droogt
op, en op de seizoenbalk staat een streepje waar de eigen buffer leeg is.

Wat dat beeld moet overbrengen zit in twee getallen die er permanent bij staan:
de eigen buffer van deze polder is **15 mm** en het tekort is **279 mm**. Een
band van 30 cm over 5 % open water is nu eenmaal 15 mm over de polder, en die is
**na 9,9 van de 183 dagen leeg**. Droogte is bij ons dus geen bergingsvraag maar
een aanvoervraag, en daarmee is dit beeld de brug naar de verdeling.

En het is geen scenario: op **30 augustus 2026** stond het landelijk gemiddelde
neerslagtekort op **276 mm** met een terugkeertijd van de grondwaterdroogte van
**37 jaar** (mediaan 28), volgens de
[grondwaterdroogte-indicator](https://hkv-products-services.github.io/grondwaterdroogteindicator/).

Let op het verschil tussen die twee terugkeertijden: 276 mm is ongeveer de T=10
van de STOWA-statistiek, maar de grondwaterdroogte staat op T=37. Dat is geen
tegenspraak maar het punt dat die indicator zelf maakt — het neerslagtekort
houdt geen rekening met hoe nat de winter ervoor was. Het `meta`-blok van
`drought_statistics.json` zegt hetzelfde: boven ongeveer T=5 lopen de
droogte-indicatoren uiteen.

### Wat gegenereerd is en wat niet

| grootheid | herkomst |
|---|---|
| het peil per uur | de rekenkern, piek 36,0 cm |
| wat het gemaal draait | de rekenkern |
| de regenintensiteit | de rekenkern, 81 mm over acht dagen |
| het peil per dag, droog | de rekenkern, band leeg na 9,9 dagen |
| het cumulatieve tekort | STOWA 2025-23, 279 mm bij T=10 (Aa en Maas) |
| **de breedte van de overstroming** | **illustratief** — proportioneel aan de overschrijding |
| **hoe smal de watergang wordt** | **illustratief** — hangt aan het profiel, en dat kent het model niet |

Die laatste regel is de eerlijke: het model geeft een *stand* en geen
inundatiecontour, dus hoe breed het land onderloopt is een visuele afbeelding en
geen uitkomst. Dat staat ook op het scherm, in de bronregel van die beat.

Regenereren na een wijziging in de kern:

```bash
python3 scripts/gen_polderanimatie.py
```

en zet de uitvoer in `gegenereerd.css`, tussen de twee `GEGENEREERD`-bakens. Het script
levert acht `@keyframes`-blokken: nat `polderpeil`, `poldergemaal`,
`polderregen`, `polderinundatie` en `polderberging`; droog `polderdroogte`,
`polderbergingdroog` en `polderdorst`.

### Waarom de overstroming een matrix is

De overstroming groeit langs de as van de watergang, en dat is een schaling in
*plaatcoördinaten*, niet in schermcoördinaten. Omdat de axonometrische projectie
lineair is, is zo'n schaling op het scherm óók lineair: met `M` de projectie is
het `M · diag(1, k) · M⁻¹`, en dat werkt uit tot

```
[[(1+k)/2,              cos30/sin30 · (1-k)/2],
 [sin30/cos30 · (1-k)/2, (1+k)/2             ]]
```

onafhankelijk van de plaatgrootte. Daarom kan het gewoon in CSS: één
`transform: matrix(...)` per stop, met `transform-box: fill-box` zodat het
middelpunt precies de hartlijn van de watergang is. Bij `k = 4` geeft dat
`matrix(2.5, -0.866, -2.598, 2.5)`, en dat is met de hand na te rekenen.

En dat is meteen de hele droge kant erbij: **dezelfde formule met `k` kleiner
dan één**. Nat zwelt de watergang buiten zijn oevers, droog krimpt hij
erbinnen. "Eén kern, klem gespiegeld" is daarmee niet alleen een uitspraak over
de code maar iets dat je op het scherm ziet — bij `k = 0,45` geeft het
`matrix(0.725, 0.159, 0.476, 0.725)`.

### Media die blijft staan

Een element dat uit het document wordt gehaald en er weer in gezet, begint zijn
CSS-animatie opnieuw en een video springt terug naar frame nul. Twee beats over
dezelfde bui lieten de bui dus twee keer bij dag 1 beginnen — gemeten 1487 ms
terug naar 184 ms — en dan hoort de zaal "en dan loopt het land onder" terwijl er
nog niets gebeurd is.

Daarom bouwt `teken()` het toneel niet meer op maar **vult** het: de kop, het
toneel, de zijde en de romp blijven staan, en media draagt een sleutel
(`figuur:naam`, `video:bron`, `rijen:stap`). Verandert die sleutel niet, dan
blijft het element staan en werken we alleen bij wat wél verschilt — welke delen
oplichten, en welke rijen zichtbaar zijn.

Kom je hier ooit terug omdat een animatie "opnieuw begint": dit is de eerste
plek om te kijken, en `media.sleutel` is de knop.

Aan die keuze hangt één ding dat je moet weten: **een `<video>` die uit de DOM
verdwijnt stopt niet.** Hij speelt gedetacheerd door, dus je hoort de clip nog
terwijl er al een andere slide staat.

Dat stond eerst als opruimpad op de twee plekken waar media wordt weggegooid, en
dat bleef fout gaan — er is altijd nog een route waarlangs een element blijft
hangen. Nu is het een **invariant** die `teken()` bij elke beat afdwingt:
`alleenDezeMagSpelen()` pauzeert elke video die niet op het toneel staat.
`alleVideos` houdt bij wat er ooit gemaakt is, want het gaat juist om de
elementen die je niet meer via de DOM kunt vinden.

Hoor je toch geluid van een vorige slide, dan kijk je bijna zeker naar een
gecachete `motor.js`: `python3 -m http.server` stuurt geen no-cache, dus
een gewone verversing haalt het oude script op. Één harde reload (Cmd+Shift+R)
en het is weg.

## Het gebied van boven, in 2,5D

Na de doorsnede kantelt het beeld: van "hoe hoog komt het" naar "wat kun je
eraan doen", en dat is ruimtelijk. Drie platen, zeven beats: nat tegenover droog,
de kale polder met de vier maatregelen laag voor laag, en de twee koppelingen.

**Eén polder, vier vuistregels.** Een plaat van boven met dikte, een strook open
water erover, en dan achter elkaar: vasthouden kleurt een deel van het land in,
bergen zet een vijver neer, afvoeren maakt het gemaal zwaarder. De basis van dit
idioom staat in `docs/images/vuistregel-tools.svg`; hier is het gekanteld en in
beats gezet.

**Bergen is een apart object en geen bredere watergang.** Je koopt een stuk land
en zet het onder water, dus het is een vijver — rechts op de plaat, diagonaal
tegenover vasthouden en los van de watergang. Dat is niet alleen netter: zo is
in de natte animatie te zien dat hij *vult* en in de droge dat hij *droogvalt*,
en dat verdwijnt zodra hij aan de watergang vastzit.

Een **cirkel** op de plaat is op het scherm een asgerichte **ellips**, en dat is
geen benadering. Met `M = [[c,−c],[d,d]]` is `M·Mᵀ` diagonaal, dus de assen
liggen langs x en y:

```
rx = r · cos30 · s · √2      ry = r · sin30 · s · √2      rx/ry = √3
```

Nagemeten tegen 720 punten op de cirkel: gelijk tot op drie decimalen. En omdat
een *gelijkmatige* `scale()` op zo'n ellips weer een cirkel op de plaat is, zijn
vullen en droogvallen gewone schalingen — geen matrix nodig, in tegenstelling
tot de overstroming die maar langs één as groeit.

**Drie knopen, twee koppelingen.** Dezelfde drie gebieden staan er **twee keer**,
boven elkaar, en wat verandert is alleen wat ze met elkaar doet:

* **nat is een ketting** — wat A wegpompt is de aanvoer van B, en het water loopt
  langs een boom naar buiten. De uitkomst die telt is niet welk gemaal te klein
  is maar welk gemaal *geblokkeerd* staat, en bovenstrooms bijbouwen doet daar
  niets aan. De ring om de middelste knoop heet daarom **"mogelijk knelpunt
  hier"**: op deze plaat is niet te zien of het er ook echt knelt, en een label
  dat dat wél beweert zegt meer dan de tekening kan waarmaken;
* **droog is een verdeling** — ze staan naast elkaar aan dezelfde eindige bron,
  geen volgorde lost dat op, en de wet zegt in welke orde er verdeeld wordt.

Ze staan **tegelijk** op het scherm en niet op twee beats. Het verschil tussen
een ketting en een verdeling is het punt, en dat vergelijkt een zaal niet als ze
de een pas ziet als de ander weg is. Dat de topologie het verschil maakt en niet
de hydrologie, is precies waarom er twee gereedschappen zijn en niet één.

**De projectie is gerekend, niet geplaatst.** Alle platen, vlakken, wanden en
pijlen komen uit één axonometrische formule in `teken/iso.js`:

```
schermx = midx + (x − y) · cos 30° · s
schermy = midy + (x + y) · sin 30° · s
```

met `x` en `y` van 0 tot 1 over de plaat en `s` als halve diagonaal. Met de hand
geplaatste ruiten lopen onherroepelijk uit elkaar zodra er één maat verandert;
`isoVlak`, `isoWanden`, `isoPlaat` en `isoPijl` doen het werk, en `figuren.css`
zet alleen nog kleur en lijn. Wil je een knoop verplaatsen of een plaat groter,
dan verzet je één getal.

## De kop markeert het world model

`S`, `A`, `E`, `T` en de brug `⟳` staan in de accentkleur; `R` in de
nadrukkleur. Dat is het antwoord op de vraag uit PR 71: het world model is
**niet de hele tuple** maar die vier leden. `R` zegt niet wat er gebeurt maar
wat je wíl, en dat is precies wat er van een simulator een beslisprobleem maakt.
Stap `T` zegt dat ook in woorden.

## T — de omkering hoort hier, en zo heet die richting elders

`T` draagt twee beats, en ze zeggen twee dingen over dezelfde afbeelding: dat
hij de volgende polder geeft, en dat hij **naar de maatregel op te lossen** is.

De twee platen komen uit één bouwer, `transitiePaneel(terug)`, en dat is geen
zuinigheid maar de claim: ze moeten tot op de eenheid over elkaar vallen. Alleen
de **pijlen** draaien om, de **ring** verspringt van het ene onbekende naar het
andere, en de kleur gaat van blauw naar bruin. Boven staat het schema, onder
dezelfde kromme — hectare open water tegen de piek — twee keer gelezen:

| | heen | terug |
|---|---|---|
| gegeven | +40 hectare bergen | de piek moet onder de norm |
| gevraagd | ΔH | hoeveel hectare |
| antwoord | 16 cm lager | +10 hectare |
| hoe | `simulate` | `solve`, bisectie op een monotone tak |
| lezen | van de x-as omhoog naar de y-as | van de y-as naar rechts en omlaag |

De terugvraag mikt op de **inundatienorm van 30 cm** en niet op een willekeurige
grens. Dat is de eis die de rest van de deck ook gebruikt, het antwoord is een
rond getal — tien hectare, zes centimeter lager — en het scheelt een uitleg
waarom er ineens 24 in het spel is.

**Vet staat op het antwoord, en dat is aan elke kant een ander getal.** Heen is
dat de verlaging, dus "16 cm lager" staat vet en "40 ha" en "20 cm" niet. Terug
is het de maatvoering, dus "10 ha" staat vet en "30 cm" en "6 cm lager" niet.
Wie de plaat bevroren ziet, ziet zo meteen wat er uit de som komt.

Tussen het schema en de kromme staat één zin, en die komt **uit de rekenkern
zelf**: het is de docstring van de tool die op die beat draait, met de maat
ingevuld.

| beat | tool | de zin op het scherm |
|---|---|---|
| heen | `calculate_store_given_area` | *Met 40 hectare extra open water — hoeveel lager komt de piek?* |
| terug | `calculate_store_given_h` | *Hoeveel open water is nodig om de piek onder de norm te houden?* |

Dat is niet gelegenheidsproza. Wat de zaal hoort is wat de tool doet, dus wie
later de MCP-server aanroept herkent zijn eigen vraag terug — en als de docstring
verandert, hoort deze zin mee te veranderen. De plek is ook geen toeval: het
schema zegt welke leden erin en eruit gaan, de kromme geeft het getal, en de
vraag staat ertussen omdat ze precies daar overgaan in elkaar.

Er stond eerst *Welke stijging hoort bij 40 hectare extra open water?*, en dat is
de forward-docstring letterlijk overgenomen. Op een scherm las het fout: veertig
hectare open water veroorzáákt geen stijging, hij dempt er juist een. Twee dingen
gaan daar mis. **"Stijging" zonder onderwerp** klinkt als het gevolg van de
maatregel, terwijl het de piek is die de bui maakt. En **"hoort bij"** suggereert
oorzaak en gevolg waar een tabel bedoeld is.

De heen-vraag vraagt nu naar de **verlaging** en niet naar de resterende stand,
want dat is waar de plaat over gaat. De absolute stand blijft wel bij `s′` staan:
dat lid *is* de volgende toestand, en de inverse vraag op de beat erna heeft hem
nodig. De vraag wijst dus naar de maatlat in de kromme, en `s′` naar het getal
dat de transitie oplevert.

De docstring in de rekenkern zelf — *Welke waterstandstijging hoort bij een
gegeven hoeveelheid extra open water?* — heeft dezelfde zwakte, en die staat nog
open. Voor een taalmodel dat het veldschema erbij heeft is hij te volgen, voor
een mens die hem koud leest niet. De inverse tegenhanger is wél in orde: *Hoeveel
open water is er nodig om de waterstandstijging onder een grens te houden?* noemt
de grootheid en de relatie allebei.

Onder de plaat stond *de rode ring staat om wat je niet weet*. Met de getallen
erbij is die zin overbodig: op de ene beat staat er een maat bij de maatregel en
de uitkomst bij de stand, op de andere andersom, en de ring zit op allebei de
beats om het lid dat als antwoord uit de som komt. Een plaat die het zelf laat
zien heeft geen bijschrift nodig dat het uitlegt.

**Het gaat niet om de 36 centimeter maar om de verlaging.** De stand zonder
maatregel stond eerst als getal boven de plaat, daarna als maatstreepje op de
y-as, en is nu een **streeplijn dwars over de kromme** met alleen het woord
*zonder maatregel* erbij. Wat ertussen zit, staat er wél als getal: een maatlat
van die streeplijn naar de aflezing, met *16 cm lager* en *12 cm lager*. De
absolute stand blijft op de as staan omdat de inverse vraag hem nodig heeft — je
vraagt om een piek ónder de norm, niet om een verlaging van zes — maar wat de
zaal moet zien is de sprong. Bij `s′` staat daarom heen alleen **ΔH** en terug
**"houd waterstand onder de norm"**: het lid en wat ermee moet, en niet nog een
keer het getal dat de kromme eronder al geeft.

Die maatlat heeft een eigen klasse `g-maat`: doorgetrokken, met een eindstreepje
aan weerskanten en geen pijlpunten. Bij zes centimeter is hij maar twintig
eenheden lang, en dan lopen twee pijlpunten door elkaar heen. De streeplijn van
`f-norm` betekent in deze deck bovendien **een eis**, en dit is een afstand.

### Waarom deze plaat dezelfde viewBox heeft als het schema bij ⟳

`transitiePaneel` draait op `viewBox="-30 0 790 460"`. De **breedte** en de
oorsprong zijn tot op de eenheid die van `wereldmodel`, en dat is wat telt: bij
`preserveAspectRatio="xMidYMid meet"` is de schaal `min(breedte/vbBreedte,
hoogte/vbHoogte)`, en zolang beide platen op hun bréédte worden uitgetekend is
dezelfde eenheid dus dezelfde pixel. Het schema staat daarom met **precies de
maten van `wereldmodel`** in deze plaat: doos op 210..460, `a` op 138, `s′` op
574. Nagemeten: de doos loopt op beide beats van 802,4 tot 1140,4 px, gelijk tot
op een tiende.

Hoger mág hij dus wel zijn, en dat is hij ook: deze twee beats dragen **geen
bronregel**, dus er is onder de figuur ruimte over, en die veertig eenheden gaan
naar lucht om de vraag heen — de zin tussen het schema en de kromme stond er
eerder ingeklemd. De grens is `790 / containerverhouding`; daarboven wordt de
plaat op zijn hoogte uitgetekend en verspringt de uitlijning.

Het kader van de kromme staat om dezelfde reden op **85..592**: op het scherm valt
het samen met de statistiekplaat bij `E`, die van 96 tot 520 loopt in een viewBox
van 660. Nagemeten 633,4 tegen 633,3 px links en 1318,9 tegen 1319,4 px rechts.
Die twee viewBoxen zijn niet gelijk, dus de uitlijning houdt zolang beide platen
op hun **breedte** worden uitgetekend — bij het toneel van deze deck is dat altijd
zo, maar het is geen wet zoals bij het schema.

De astitels staan waar `statistiekAssen` ze ook zet: de y-titel boven de as, de
tickwaarden end-anchored links ervan, de x-titel gecentreerd onder de plot.

### T⁻¹ op het toneel, T in de kop

Op de tweede beat wisselt het symbool naast de plaat naar **T⁻¹** en de titel
naar *de omkering*. In de **kop** blijft het lid gewoon `T`, en dat verschil is
inhoudelijk: de tuple heeft geen T⁻¹. De omkering is geen zesde lid maar iets
wat je met `T` *doet*, en de kop is de inhoudsopgave van de tuple.

Daarvoor kennen beats een `sym`, een `macht` en een `titel` die die van de stap
overschrijven — zie de kop van `inhoud.js`. Er is precies één beat die ze
gebruikt, en dat is de bedoeling: wisselt het symbool vaker, dan is de kop geen
inhoudsopgave meer.

De macht is een echte `<sup>` en niet het teken ⁻¹ uit de tekenset. Die twee
tekens dragen hun eigen spatiëring mee, en in een cursieve schreefletter van
tweehonderd pixels staat er dan een gat tussen het streepje en de één.

Naast de ring staat op beide beats een **vraagteken**, aan de buitenkant. De ring
zegt *dit is het lid dat we niet weten*, het vraagteken zegt het hardop, en samen
hebben ze geen bijschrift meer nodig. Er stonden ook twee tekstblokken links —
*heen / geef de maatregel, lees de stand* en de tegenhanger — en die zijn weg: de
pijlen, de kleur, de ring en de vraag erboven zeggen het al, en een blok dat
datzelfde in woorden herhaalt maakt de plaat voller zonder hem duidelijker te
maken.

De getallen zijn **uitgerekend en niet gekozen**: de kromme, de twee knikken en
de twee antwoorden komen uit `scripts/gen_tweerichting.py`, dat `simulate` en
`solve` op de referentiepolder loslaat. Dat 40 hectare precies 16 cm verlaging
geeft en de norm precies 10 hectare vraagt, is toeval — prettig toeval, want
ronde getallen op een scherm lezen sneller dan 15,98 en 9,97.

Die tweede beat is het antwoord op de twee ringen waarmee `⟳` sluit. Daar zegt de
strateeg dat hij het weer niet kiest en van zijn maatregel niet weet hoe hij
uitpakt; hier staat waarom dat op te lossen valt. Daarom opent de zin met *daar
helpt deze transitie* en niet met hoe bijzonder hij is.

Die tweede beat staat bij `T` en niet bij `A`, en de reden is precies één regel:
**`A` is een verzameling, `T` is een afbeelding, en inverteerbaarheid is een
eigenschap van afbeeldingen.** De omkering verandert `A` niet — er zijn nog
steeds zes maatregelen in dezelfde eenheden. Wat verandert is welke kant van `T`
je oplost. Bij `A` zou de figuur zeggen "onze tools hebben twee ingangen", en dat
is waar maar zwak; bij `T` zegt hij "deze transitie is exact, deterministisch én
naar de maatregel op te lossen".

En dat is geen los geluk maar een gevolg van de vorm van de tuple hieronder: uit
een overgangskans `P(s′ | s, a)` valt geen maatregel te halen, alleen een
verdeling om over te integreren. Doordat `T` deterministisch is en `E` er los van
staat, **bestaat** deze richting.

De omkering heeft in het algemeen meer dan één antwoord — dertig centimeter haal
je met bergen, óf met afvoeren, óf met een mix. Per maatregel is hij uniek en
exact op te lossen; over maatregelen is hij onderbepaald, en dát is bij `x*` de
reden dat het antwoord een band is en geen punt.

### De term: inverse ontwerpvraag, geen invers model

Vier vakgebieden hebben een naam voor deze richting en citeren elkaar
nauwelijks:

| waar | hoe het daar heet |
|---|---|
| robotica | *inverse kinematics* — gewenste handpositie, welke gewrichtshoeken |
| reinforcement learning | *goal-conditioned*, en in de UDRL-tak *upside-down* — conditioneer op de gewenste uitkomst en genereer de actie |
| regeltechniek | een *setpoint* en een invers plantmodel |
| ontwerp met differentieerbare simulatie | *inverse design* — gewenste prestatie, welke ontwerpparameters |

Op het scherm staat er **één** naam, en dat is de **inverse ontwerpvraag**. Het
woord *ontwerp* zit erin, en dat is het enige waar een strateeg iets aan heeft:
gegeven de gewenste prestatie, welk ontwerp hoort daarbij. *Inverse kinematics*
gaat over gewrichtshoeken en zegt dat niet, en de brug naar de openingsclip
draagt hij ook niet — die brug is de eend zelf en het schema eronder. Eén naam
per beat is genoeg; de andere drie horen in de zaal alleen als iemand ernaar
vraagt.

Zeg tegen een hydrologisch publiek nooit "invers model". Daar betekent inverse
modellering standaard iets anders — parameters schatten uit observaties, dus
doorlatendheid uit stijghoogtes, dus calibratie. Wij doen inverse **ontwerp**, en
geen inverse **schatting**. De term die we zelf gebruiken is daarom **de inverse
ontwerpvraag**, en in tooltaal simpelweg "geef de gewenste stand en je krijgt de
maatregel" — dat is onmisleidbaar.

Aardig detail: de niet-uniciteit van hierboven heeft in beide tradities een eigen
naam. In de robotica is het de nulruimte van een redundante arm, in de hydrologie
heet het equifinaliteit.

## E — twee beats, en beide dragen twee verdiepingen

| beat | boven | onder |
|---|---|---|
| nat | de familie per buiduur (2/4/8 dagen, T van ½ tot 1000 jaar), plus wat seizoen en regime met dezelfde bui doen (zomer 59, winter 73 mm bij T=10) | één trekking als reeks millimeter per dag — een bui is geen getal maar een reeks |
| droog | het cumulatieve tekort per waterschap (band over 21) en per KNMI'23-scenario | de minimale 7-daagse rivierafvoer als deel van een normaal jaar — Rijn 1077 m³/s, Maas 50 m³/s |

Vraag en aanbod staan gestapeld in één figuur maar met een **eigen as elk**, en
dat is geen luxe: een fractie van 0,9 op een millimeter-as leest als 540 mm, en
een secundaire as leest niemand op een beamer. Hetzelfde geldt voor de trekking
onder de natte familie: millimeter per dag is een andere grootheid dan de
buisom, dus een eigen kader.

**De drie buiduren dragen één tint in drie treden** en geen drie kleuren. Dat is
het verschil tussen een ordening en een categorie: 2, 4 en 8 dagen is een reeks,
en meer duur is meer neerslag. Dus loopt de tint mee met de grootheid — in licht
naar donker toe, in donker naar licht toe, want daar is lichter juist sterker
tegen de grond. Drie losse hues zouden suggereren dat het drie soorten zijn.

De treden zijn gevalideerd en niet geschat: elk aangrenzend paar houdt een
normaalziend verschil van 18,7 (licht) en 19,7 (donker), en alle drie halen 3:1
tegen hun eigen grond. Dat laatste begrenst de lichtste trede, en daarom is de
donkerste in lichte modus bijna zwart — met een lichtere reeks zijn drie treden
niet te scheiden op beamerafstand.

Wat er in STOWA 2025-23 wél staat maar **niet in onze data**: de 45-daagse
neerslagsom en het aantal droge dagen. Dat staat in de bronregel van die beat,
zodat niemand denkt dat we alle indicatoren hebben.

## Wat waar hoort: A tegen R

De **actie** is wat je kunt doen; de **beloning** is wat het waard is. De prijzen
staan daarom bij `R` en niet bij `A`, en ze staan er als **bandbreedte** —
vasthouden € 1.250–3.000 per ha, bergen € 120–230 duizend per ha, afvoeren
€ 1,86–2,04 mln per m³/s. De rekenkern draagt `low`/`typical`/`high`, en één
getal zou valse precisie zijn: de grondprijs verschilt regionaal een factor drie.

Bij `A` staan de zes maatregelen met hun **eenheid**, en met beide ingangen als
derde en vierde kolom naast elkaar: heen levert een stand bij een maatregel,
terug levert een maatregel bij een gewenste stand. Die twee horen per maatregel
te staan en niet in aparte beats.

`A` is daarmee de **interface** — welke knoppen er zijn, in welke eenheid, en dat
elke knop twee ingangen heeft. De uitspraak dat de transitie zelf omkeerbaar is,
staat bij `T`; zie de sectie daarover hierboven. Dezelfde claim op twee plekken
verzwakt beide, dus de figuur staat waar hij het argument is.

En wat `R` **niet** heeft: de vermeden jaarschade. Dat staat als zodanig op het
scherm, want zonder die kant is er geen afweging te maken — alleen een prijslijst. Dat is niet alleen netter — het is hoe
Yarens scriptie het doet (`A` is een controlevector, de gewichten zitten in `J`)
en hoe het bij de microduck werkt (`A` zijn gewrichtsdoelen, de prijs zit in de
beloning). Prijzen in de actieruimte was een fout, en hij stond er.

Bij `R` staat daarnaast de vraag die er echt toe doet: **kun je de norm als
beloning uitdrukken?** Ja — als strafterm, en de referentieregelaar in Yarens
scriptie doet dat ook (§2.4.3, een lineaire plus een kwadratische straf op
overschrijding). Maar dan is het gewicht van die straf een verkapte prijs voor
een overstroming, en de scriptie noemt die gewichten zelf heuristisch: er is geen
unieke methode om ze te bepalen. Wij houden de norm daarom een eis, en
rapporteren in plaats daarvan bij welke prijs het antwoord kantelt.

## γ — twee krachten, niet één

Disconteren maakt **uitstellen goedkoper**: een investering in jaar *t* is
vandaag `C/(1+r)^t` waard, precies omdat geld dat je niet uitgeeft rendeert. Dat
duwt alles naar later.

Maar elk jaar wachten kost schade, en dat risico **loopt op** door klimaat en
bodemdaling. Dat duwt naar eerder. Het beste moment is waar die twee elkaar
raken — en dat is precies de som die Van Dantzig in 1956 voor de Deltacommissie
maakte: investeringskosten tegen contant gemaakte verwachte schade, met de
dijkhoogte als enige beslisvariabele. Eijgenraam en het CPB hebben daar de
moderne versie van.

Die bronvermelding staat hier en **niet in de gesproken zin**. Op één beat met
één zin kost een jaartal de helft van de aandacht, en de vorm op het scherm is
het argument — niet wie hem het eerst opschreef.

Twee dingen om scherp te houden in de talk:

* een **hoge** discontovoet schuift adaptatie systematisch de toekomst in. Dat is
  de bekende kritiek op marktrentes voor klimaatadaptatie, en het is de reden dat
  de discontovoet een beleidskeuze is en geen technische constante;
* in de zaagtandfiguur loopt de lijn "zonder maatregelen" **exact samen** met de
  zaagtand tot de eerste ingreep. Dat moet ook: vóór die ingreep is er geen
  verschil. Elke stijgende tak heeft daarom dezelfde helling als de driftlijn.

## x* — de uitkomsten

De rest van de deck legt de **methode** uit. Deze stap zegt wat het model
*antwoordt*, en dat is het enige waarvoor je zo'n model bouwt. Twee helften in
één stap: eerst wat een maatregel je aan bescherming oplevert, dan wat een eis
kost.

**De frequentielijn, met de polder eronder.** Twee verdiepingen in één figuur.
Boven het huisidioom van de waterveiligheid: hoogtes tegen hun
overschrijdingsfrequentie, met een lijn per maatregel. Onder de polder in 2,5D,
zodat te zien is *waarmee* gerekend wordt en niet alleen wat eruit komt. Elke
maatregel verschijnt op dezelfde beat twee keer — als lijn boven en als ingreep
op de plaat beneden — en in dezelfde kleur, zodat het effect naast zijn oorzaak
staat.

De **lijnen stapelen zich op** en op de **plaat staat er precies één**. Dat is
met opzet: de lijn is het resultaat dat je wilt vergelijken, de plaat is de
ingreep die erbij hoort. Zonder die scheiding leest de derde beat als een pakket
van drie maatregelen, en dat is het niet — elke lijn is de referentiepolder met
één maatregel erop.

Bij elke maatregel verschijnt zijn **maat** in de toestandsregel links, onder de
kale polder, zodat je ziet wat er in de toestand verandert en niet alleen wat er
uit komt:

| maatregel | wat er in de toestand verandert |
|---|---|
| bergen 10 ha | 5 → 6 % open water |
| vasthouden 708 ha | 74 % van het land houdt zijn water vast |
| afvoeren +0,5 m³/s | gemaal 1,5 → 2,0 m³/s |

De x-as is logaritmisch in de terugkeertijd: dat is de conventie, en zonder log
liggen alle interessante kruisingen op elkaar. Op de y-as staat de piek boven
streefpeil, en die loopt tot **80 cm**: de hoogste lijn haalt 74 cm, en een as tot
100 perst het verschil tussen de maatregelen in driekwart van de hoogte.

| lijn | bij T=10 | onder de norm van 30 cm tot | idem bij 4 afvoerdagen |
|---|---|---|---|
| geen maatregel | 36,0 cm | T = 7 jaar | T = 43 |
| bergen 10 ha | 30,0 cm | T = 10 jaar | T = 66 |
| vasthouden 74 % | 18,9 cm | T = 22 jaar | T = 98 |
| afvoeren +0,5 m³/s | 18,0 cm | **T = 34 jaar** | > 100 |

Die laatste kolom is de reden dat er een bronregel onder de figuur staat. De
**neerslag-afvoerrelatie is een keuze en geen meetwaarde** — de bron geeft twee tot
vier dagen, en minder dagen concentreert de afvoer en geeft een hogere piek. De
figuur rekent met twee, de ongunstige kant. Wat daarmee schuift is niet de vorm maar
de terugkeertijd, en die staat op het scherm.

Wat daar houdt is **welke maatregel wint**: in alle drie de kolommen ligt geen
maatregel onder bergen onder vasthouden onder afvoeren. Wat niet houdt zijn de absolute getallen. Dat
staat zo onder de figuur, want de `R`-stap belooft een bandbreedte en dan mag `x*`
geen kaal getal geven zonder te zeggen waar het aan hangt. `band_over_afvoerdagen()`
in het generatorscript rekent die kolom uit, dus hij is na te meten en niet
aangenomen.

**Vier series, vier tinten.** Geen maatregel is neutraal (zwart, of wit in donker) en
de drie maatregelen dragen blauw, amber en magenta. Die derde tint — `--derde` —
bestaat omdat het palet er twee had: blauw voor nat en amber voor droog, een
*semantische* as. Zodra drie maatregelen naast elkaar staan is dat er een te weinig,
en `--accent` en `--nat` zijn allebei blauw: in donker zelfs exact hetzelfde hex. Op
de laatste beat staan alle vier de lijnen samen, en dát is de beat waar de
vergelijking het argument is.

De twee waarden zijn gekozen met een palletvalidator en niet met het oog. Over álle
paren haalt blauw/amber/magenta een kleurenblind-verschil van 9,3 (licht) en 8,3
(donker) en een normaalziend verschil van 20,6 en 20,4; blauw tegen blauw haalde 0,6
en 0,0 — onder de 15 is een paar ook met volledig kleurenzicht niet te scheiden.

De beats lopen die vier langs in die volgorde: eerst de kale polder, dan de
acht losse doorrekeningen als punten, dan diezelfde punten als lijn, en dan de
drie maatregelen. Peilopzet staat er níet bij: hij gaat omhoog in plaats van
omlaag en leidt af van de vraag die deze figuur stelt.

Wat de plot geeft en een enkel getal niet: **dezelfde centimeter is niet
dezelfde bescherming.** Vasthouden en afvoeren schelen bij de ontwerpbui nog
geen centimeter — 18,9 tegen 18,0 — en dat is 22 tegen 34 jaar. Precies daarom
kijk je naar de hele lijn en niet naar één punt.

Regenereren: `python3 scripts/gen_frequentielijn.py`, en de vier padjes in
`frequentielijn` vervangen, samen met de acht rondjes van de losse runs. De
"veilig tot"-waarden komen uit hetzelfde script, log-lineair geïnterpoleerd
tussen de omliggende herhaaltijden — lineair interpoleren op een logas zit daar
systematisch naast.

Achtergrond bij het idioom:
[STOWA Deltafact nieuwe normering](https://www.stowa.nl/deltafacts/waterveiligheid/beoordelen-waterkeringen/nieuwe-normering-van-waterveiligheid)
· [HKV, overstromingsrisicomodel](https://www.hkv.nl/wp-content/uploads/2023/05/RO0917.10_Overstromingsrisicomodel_voor_ruimtelijke_-investeringsvraagstukken.pdf)
· [Deltaprogramma, systeemanalyse waterveiligheid](https://www.deltaprogramma.nl/site/binaries/site-content/collections/documents/2023/06/05/systeemanalyse-waterveiligheid-rijnmonddrechtsteden-en-rivierengebied---kp-zss/Systeemanalyse+waterveiligheid+RijnmondDrechtsteden+en+Rivierengebied+-+KP+ZSS.pdf).
Slide 14 van `20260629 The engineer as world model.pptx` is dezelfde plot voor
Dordrecht.

**De kostencurve.** Niet "welke maatregel" maar "wat kost een eis" — en in de
vorm die de literatuur gebruikt. De as begint links bij **36 cm**, en dat getal
valt niet uit de lucht: het is de kale piek van de vorige figuur, de polder
zonder maatregel op de ontwerpbui. Dat staat als tweede regel onder de as, want
zonder die verwijzing is het een willekeurig begin.

Van Dantzig (1956) en Eijgenraam zetten de investering tegen het
beschermingsniveau en tellen daar de resterende verwachte schade bij op.

| eis | goedkoopste pakket | kosten |
|---|---|---|
| 36 cm (de kale piek van de vorige figuur) | niets | € 0 |
| 30 cm (de norm van nu) | afvoeren +0,115 m³/s | € 0,22 mln |
| 20 cm | afvoeren +0,384 m³/s | € 0,74 mln |
| 10 cm | afvoeren +0,963 m³/s | € 1,85 mln |

De vier prijzen staan als eigen rij ónder de eis-as. In het vlak zelf botsen ze
op de curve die er in de laatste beat bij komt, en onder elkaar laten ze zien
wat het punt is: **de sprongen worden groter.** Zes centimeter strenger kost
twee ton, de tien daarna kost er vijf, en de tien daarna elf. Tot een eis van
ongeveer 24 cm is pompen alleen genoeg en loopt de curve recht; daarna buigt hij
omhoog.

En dan de eerlijke helft. **De vermeden jaarschade hebben we niet** — geen
schadefunctie, geen EAD — dus de curve die je erbij nodig hebt ontbreekt. De
voorlaatste beat zet hem er als streeplijn bij met het label "hier hoort de
schadecurve — nog in te vullen". Dat is de enige eerlijke manier om deze
figuur af te maken: de vorm laten zien zonder het getal te beweren.

En de laatste beat zegt wat we met die som **wél** zouden doen, en dat is niet
optimaliseren. De bodem van zo'n som is vlak: binnen een band aan eisen zijn
meerdere hele pakketten allemaal verdedigbaar, en welke je kiest hangt af van
dingen die niet in de doelfunctie staan. Daarom staat er een band in de figuur
en geen punt, en daarom genereren we alternatieven. De plek van die band is,
net als de schadecurve zelf, de **vorm** uit de literatuur en niet een getal van
ons — dat staat in de bronregel van die beat.

Regenereren:

```bash
python3 scripts/gen_kostencurve.py
```

en het padje in `kostencurve` vervangen, samen met de vier prijzen in `EISEN`.
Het script vraagt de pakketzoeker per eis opnieuw en neemt het goedkoopste
pakket dat eraan komt.

**Wat er niet op het scherm staat.** De drie maatregelen los tegen elkaar op een
geldas — welke koopt de meeste centimeter per euro — is een eerdere vorm van
deze stap. Hij is eruit omdat de vraag "wat kost een eis" beter aansluit bij de
literatuur, maar de bevindingen staan nog:
`python3 scripts/gen_maatregelcurves.py` geeft dat **bergen zes keer zo duur is
als afvoeren** voor dezelfde centimeters (€ 1,35 mln tegen € 0,23 mln voor de
norm van 30 cm), en dat **vasthouden een bodem heeft** — voorbij 74 % van het
land maakt meer geld het slechter, want de vertraagde afvoer van het ene deel
valt samen met de piek van het andere (18,9 cm bij 1,67 mln, 19,4 cm bij
3,0 mln).

## π — de noodzaak zit in de tijd, niet in de ruimte

De vraag die deze stap moet beantwoorden is waarom je een policy zou wíllen,
gegeven dat de zoeker al kiest. Het gangbare antwoord — "een policy
generaliseert naar een gebied dat hij niet gezien heeft" — houdt hier geen
stand. De zoeker enumereert eenendertig mixen en lost per mix exact op; draai
hem in een nieuw gebied gewoon opnieuw. Snel genoeg is snel genoeg, en het
antwoord is op elke machine hetzelfde getal.

Wat de zoeker níet kan, is reageren op wat je volgend jaar weet. Hij geeft een
**plan**: bouw dit, in dat jaar. Een nieuwe meting, een herzien
klimaatscenario, een kade die het niet hield — een plan zegt niet wat je met die
informatie doet. Een policy is een plan dat kan antwoorden, en dat is adaptief
deltamanagement in één woord.

Daarom sluit deze stap op hetzelfde schema als `T`: zet er een blok bij dat
kiest en de lus is rond. Op één beat, en het blok komt erbij in plaats van dat
het er al stond — zo is "wat mist er nog" een plaatje in plaats van een bewering.

**Eén beat over het schema, en dat waren er acht.** Het tijdslot is vijftien
minuten, en de langste sectie mag niet die over het onderdeel zijn dat nog niet
bestaat — al helemaal niet nu de voorkeursvolgorde die er wél uit komt bij `x*`
twee beats heeft gekregen. Wat overbleef is de enige zin die het argument draagt:
nodig om te kiezen is de policy niet, nodig om te zeggen wat je doet met wat je
volgend jaar weet wél.

## De vijf punten van de sessievoorzitter

De voorzitter van de sessie vroeg vijf dingen op de slides. Ze staan er niet als
een eigen blok maar **in de stap waar ze thuishoren**, want vier van de vijf zijn
uitspraken over iets dat al een plek in de kop heeft.

| gevraagd | waar het staat | figuur |
|---|---|---|
| de meerwaarde tegenover conventioneel modelleren | `T`, beat 3 | `ribasim` |
| hoe de agent pakketten verkent en waardeert | `x*`, beat 10–13 | `pakketvraag` |
| waar het werkt en waar niet | `x*`, beat 14–15 | `grenzen` |
| wat de agent doet en zijn rol in de workflow | `π`, beat 1–3 | `agent` |

**Punt twee staat nog open**: wat "world model" hier betekent tegenover AI en
robotica. Er stond een beat met een tabel die de herkomst van `T` naast die van
een robot legde, en die klopte niet — "leren uit data" is niet wat elk
robotica-world-model doet, en "drie regels" verkleint onze waterbalans tot iets
wat hij niet is. Een fout antwoord op de scherpste vraag uit de zaal is erger dan
geen antwoord, dus is hij eruit.

Er stond daarna nog een halve zin bij `T` beat 2 — "daar wordt hij geleerd, bij
ons is hij exact" — en die is met de omkering meegegaan toen die beat de inverse
ontwerpvraag ging dragen. Het punt staat dus **helemaal** open: de deck zegt
nergens meer wat een world model is. Het antwoord dat er hoort te komen heeft
geen tabel nodig, want het gaat niet over hoe het model gemaakt is maar over waar
het zit: buiten de lus draai je scenario's en kijk je ernaar, binnen de lus loop
je heen en weer tussen wat je kunt doen en wat er op je afkomt. De twee ringen bij
`⟳` en de heen-en-weer-beats bij `x*` laten dat inmiddels zíen; wat ontbreekt is
de beat die het ook zegt.

De kop is niet aangeraakt. Dat is geen zuinigheid: de agent is geen term in de
formule, en een zesde symbool ernaast zou beweren dat hij dat wel is.

**`ribasim` antwoordt niet met "wij zijn beter" of "wij zijn sneller"** maar met
wat vastligt en wat beweegt. Zet de polder vast en laat het water bewegen, dan
kun je vragen wat er gebeurt. Zet de bui vast en laat de polder bewegen, dan kun
je vragen hoe de polder moet worden.

**Deze plaat volgt het tabelidioom van de deck en niet zijn eigen.** `kolommen`
was een SVG-vergelijkingsmatrix: waarden gecentreerd onder hun kop, rijlabels
rechts uitgelijnd in grijs, en alleen een lijn onder de kop. Dat is een geldig
diagramidioom, maar niet dát van deze deck — en het maakte `T.3` de enige tabel
die er anders uitzag dan `S`, `A` en `R`.

Het argument dat de vorm anders is, houdt niet: **`A` is óók een
vergelijkingstabel**, met vier kolommen, en die volgt het huisidioom wel. En
`lijsten` — de andere SVG-helper met twee kolommen, bij `x*` — deed het al goed.
`kolommen` was een helper met één gebruiker die is afgedreven.

Nu, met de maten van `table.rijen`: labelkolom links, waarden **links** uitgelijnd
onder hun kop, een haarlijn onder elke rij, en de voetregels links in plaats van
gecentreerd.

**Onze kolom staat links.** De plaat beantwoordt een vraag over ons werk — waarom
niet gewoon Ribasim — en dan hoort er eerst te staan wat wij doen, en daarnaast
hoe Ribasim daarop aansluit. Andersom leest de plaat als een vergelijking waarin
wij de uitdager zijn, en dat is de verkeerde toon voor een zaal waar de bouwers
van het andere model in zitten.

De koppen noemen de **richting** en niet een werkwoord: *het onze: van eis naar
ontwerp* tegenover *Ribasim: van ontwerp naar gedrag*. In vier woorden staat er
wat je erin stopt en wat eruit komt, en dat werkt ook voor iemand die Ribasim
nooit heeft gezien.

Er stond eerst *"het systeem laten draaien"*, en daarna *"doorrekenen"*. Allebei
fout, en de tweede erger dan de eerste: **elk model rekent door**, dus dat zegt
niets, en het laat de vraag open waaróp dan. Een kop op zo'n plaat moet informatie
dragen voor wie de naam niet kent, en een werkwoord dat op beide kolommen past
draagt er geen.

De namen staan in die kop en niet in de voetregel. Op een bevroren plaat moet te
zien zijn welke kolom welk model is; de spreker die "Ribasim" zegt is er dan
niet.

De voetregel zegt wat de twee werkelijk oplossen, **in woorden die een zaal
volgt**:

> Wij lossen de waterbalans naar de maatregel toe: een world model om te ontwerpen.
> Ribasim lost de waterbalans naar de standen en debieten toe: een world model voor gedrag.

De twee regels lossen **dezelfde vergelijking** op en verschillen alleen in het
lid dat eruit moet komen. Dat is het idioom van de twee beats hiervoor, een
verdieping hoger: bij `T` stond de ring om de stand en bij `T⁻¹` om de maatregel,
en hier staat datzelfde tussen twee modellen. *De waterbalans* is bovendien
letterlijk wat er in de doos staat op die beats, dus de plaat haakt terug in
plaats van een begrip te introduceren.

Twee formuleringen hebben het niet gehaald, en allebei om een reden die het
onthouden waard is:

* *"optellen per uur, en dat is achterstevoren te lezen"* — waar, en het verklaart
  waaróm de omkering kan, maar het is de **werkwijze** en niet het resultaat.
  Naast een regel die zegt wat Ribasim oplost, hoort een regel die zegt wat wij
  oplossen.
* *"Ribasim lost per tijdstap het hele netwerk op"* — te vaag, en erger: het is
  geen verschil. Wij willen juist óók het hele netwerk in één keer; alleen weten
  we dan welke **maatregel** er in elke knoop moet, en dat is precies wat Ribasim
  niet geeft. Een contrast dat op beide kolommen past, is geen contrast.

*Bekkens* is er om dezelfde reden uit als *doorrekenen*: het is Ribasim-jargon,
en deze zaal denkt in gebieden, standen en debieten.

Er stond *"Ribasim integreert een stelsel differentiaalvergelijkingen"* tegenover
*"wij lossen een verschilvergelijking op"*. Dat is exact hetzelfde onderscheid en
het klopt woord voor woord, maar niemand leest dat van een scherm — en wie
"verschilvergelijking" niet kent, weet na het lezen nog niets. Een voetregel op
een beamer heeft één seconde.

De wiskunde eronder, voor wie ernaar vraagt: Ribasim lost `du/dt = f(u, p(t), t)`
op, een stelsel eerste-orde ODE's met OrdinaryDiffEq.jl uit de Julia-SciML-stapel,
en doet dat **impliciet** — per tijdstap staat er een gekoppeld stelsel voor alle
bekkens samen, precies zodat bekkens binnen die stap informatie uitwisselen. Zie
[equations](https://ribasim.org/concept/equations.html) en
[numerics](https://ribasim.org/concept/numerics.html). Bij ons is de transitie
`h[t] = klem(h[t−1] + Δ[t])`: een lopende optelsom met een klem, op een vaste
uurstap.

Er stond ook *"de oplosser kiest zijn eigen stap"*. Dat is waar — Ribasim stapt
adaptief, "as large a step as possible while keeping error tolerances within
requirements" — maar het is de verkeerde bijzin. Vast tegenover adaptief is niet
waarom de omkering bij ons kan; *een stelsel oplossen tegenover optellen* is dat
wel, en dat is bovendien te volgen zonder woordenboek.

Dat verschil is niet cosmetisch, en daarom staat het er. Zo'n optelsom is per stap
in gesloten vorm te schrijven — `_reflected_scan` doet het met een cumulatieve som
en een lopend minimum, zonder tijdlus — en dán is de weg terug naar de maatregel
een rekensom in plaats van een zoektocht. De omkering bij `T⁻¹` hangt aan die
eigenschap, en dat is wat de tweede regel zegt.

**En differentieert Ribasim zelf dan niet?** Jawel, maar voor iets anders. De
numerics-pagina zegt dat automatische differentiatie via `ForwardDiff.jl` de
**Jacobiaan van de rechterhandfunctie** berekent, nodig voor de Newton-iteraties
van de impliciete solver — uitdrukkelijk *"not parameter sensitivities or
gradients"*. Nagekeken in
[`core/Project.toml`](https://github.com/Deltares/Ribasim/blob/main/core/Project.toml):
`ForwardDiff`, `DifferentiationInterface`, `SparseConnectivityTracer` en
`SparseMatrixColorings` staan erin — de machinerie voor een ijle Jacobiaan —
en **`SciMLSensitivity` staat er niet**. Ribasim differentieert dus om te kunnen
**oplossen**; een adjoint naar ontwerpparameters doet het niet.

**Wat hier níet staat: "de kern is differentieerbaar, één pas geeft de gradiënt
naar elke knoop".** Verleidelijk, en half waar. Nagemeten in de `jax`-omgeving van
de repo:

| wat | uitkomst |
|---|---|
| `xp = jnp` en dezelfde uitkomst als numpy | ja, verschil 0,0 |
| gradiënt door `clamped_scan` | ja, `jax.grad` 0,046184454 tegen centrale differentie 0,046184454 |
| gradiënt naar een **maatregel** via `simulate()` | **nee** — pydantic weigert een tracer met een `ValidationError` |
| gradiënt door het **netwerk** | **nee** — `scatter_add` valt terug op `np.add.at` en geeft `TracerArrayConversionError` |
| `running_minimum` op het snelpad | **nee** — `xp.minimum.accumulate` wordt onder JAX een sequentiële `lax.scan`, niet `lax.cummin` |

Twee naden dragen hun eigen oplossing al in hun docstring (`lax.cummin` en
`jax.ops.segment_sum`); de derde leek echt werk. **Nagemeten bleek dat mee te
vallen**, en dat is het opschrijven waard.

Met alleen die twee regels vervangen loopt een gradiënt van een netwerkdoelfunctie
naar de **gemaalcapaciteit van elke knoop** — zonder één regel in `network.py` aan
te raken. Dat kan omdat het voorwerk er al ligt: `SystemState` is een gewone
frozen dataclass met arrayvelden en geen pydantic, `_forward_pass` is met opzet
functioneel geschreven ("Buffers … zijn allebei mutatie, en dat is wat een tracer
niet aankan"), en `simulate_network(..., iterations=n)` bestaat expliciet als de
vorm die uitrolt in plaats van een `while_loop` te worden. De pydantic-muur zit
alleen op het pad van één polder via `Action.apply()`, en dat pad heeft het
ontwerpprobleem op schaal niet nodig.

Gemeten op een topologie zoals Nederland — veel polders op een handvol boezems,
diepte twee:

| knopen | voorwaarts | gradiënt naar elk gemaal |
|---|---|---|
| 208 | 0,6 ms | 1,7 ms |
| 1008 | 1,3 ms | 5,2 ms |
| 4008 | 6,0 ms | 20,8 ms |

De gradiënt kost dus ongeveer drieënhalf keer een voorwaartse pas, en compileren is
eenmalig een halve seconde. En hij klopt: tegen centrale differentie wijkt hij
**2·10⁻⁹** af.

**Behalve op een knik.** Staan alle gemalen precies op 1,50, dan geeft AD 0,2925
waar centrale differentie 0,3096 geeft — en de linker- en rechterafgeleide
(+0,1368 en +0,4824) lopen uiteen en convergeren niet als je de stap verkleint. De
doelfunctie is stuksgewijs lineair, dus daar bestáát geen afgeleide en geeft AD een
subgradiënt. Geen fout, wel een eigenschap die een optimalisator moet kunnen
hebben — precies het gemengd-discrete punt dat `PLAN_UITWISSELING_EN_NETWERK.md`
§7 al maakt.

**Wat er dan nog tussen zit.** Een diepe ketting rolt uit tot een graaf zo diep als
de ketting: een test met vijfduizend polders achter elkaar bleef in het compileren
hangen. Nederlandse topologie is breed en ondiep, dus dat knelt niet, maar het is
een grens om te kennen. Verder: JAX in `pixi.toml`, `optimize.py` op de analytische
gradiënt in plaats van centrale differenties, en tests. Dat is werk van dagen, geen
maanden — en het is geen onderzoeksvraag meer.

Twee regels en niet drie: een plaat met een tabel erboven heeft geen alinea
eronder nodig.

Wat hier níet meer staat is "twee gaten, en niet dezelfde". Dat is waar, maar het
volgt uit de gemaaltest — het gemaal ánders aanzetten tegenover het gemaal gróter
maken — en die test staat niet op deze plaat. Een voetregel hoort te concluderen
uit wat er boven staat.

**`agent` draagt de eerlijke regel onderaan en niet als bijzin:** het taalmodel
rekent niet, het vertaalt. Geen getal op het scherm komt uit het taalmodel. Die
beat staat bij `π` en niet ergens los, omdat `π` de stap "wie kiest de maatregel"
is — en in de praktijk is dat vandaag een gesprek en geen policy. Eerst wat er
wél kiest, dan wat er nog niet is.

**`pakketvraag` is de opmaat en de nazit van de live demo**, op dezelfde polder
van duizend hectare als de rest van de deck. Eén eis — de piek onder achttien
centimeter — want twee eisen erbij verklaren kost meer tijd dan het antwoord
waard is. Blijft de demo weg, dan staat de beat stil ook goed: de vraag en het
antwoord staan er beide.

Wat eruit komt is gemeten en niet gekozen:

| | |
|---|---|
| het goedkoopste pakket | vasthouden 114 ha + afvoeren 0,34 m³/s |
| wat het kost | € 0,92 mln, band € 0,77–1,03 |
| en binnen die band | afvoeren 0,5 m³/s alléén, voor € 0,96 mln — vier procent meer |

En dan loopt de figuur de andere kant op, want dat is waar de twee ringen van
`⟳` hun antwoord krijgen: dezelfde eis, een andere bedreiging. Bij eens per
vijfentwintig jaar koopt de zoeker alleen een gemaal van 0,91 m³/s, bij eens per
eeuw staat vasthouden er groter bij dan in de demo. Leg de eis vervolgens langs
het hele natte rooster — elke terugkeertijd, elk buiduur, beide seizoenen, elk
regime, 312 bedreigingen — en de voorkeur staat er: het gemaal in 212 van de 216
pakketten waarin een maatregel nodig is, vasthouden in 140. Bergen en peilopzet
koopt hij bij deze eis nooit. Regenereren: `python3 scripts/gen_voorkeursvolgorde.py`.

Die drie onderste blokken delen één vlak en stapelen niet: `pakketvraag` draagt
`f-hard`, dus de beat wisselt de inhoud van de onderste helft.

Dat laatste is waarom deze casus de goede is. Het gemaal is **forced** — het zit
in elk even goed pakket — en de retentie is **optional**, 113 tot 222 hectare.
Dus geeft de zoeker een verzameling terug en geen punt, en dat is precies wat de
`R`-stap belooft en wat de kostencurve twee beats eerder zegt. Elke maatregel in
dit antwoord heeft een prijs, dus er staat een echt bedrag met een echte band en
geen ontbrekende post.

Regenereren: `python3 scripts/gen_kostencurve.py` toont per eis welk pakket wint;
achttien centimeter is de eis waar de mix het van de enkele maatregel wint.

**`grenzen` zet acht regels op één plaat** die elk ergens in de repo als caveat of
open punt staan. Bij elkaar zijn ze een uitspraak in plaats van een verzameling
voetnoten, en dat is wat een zaal ervan moet meenemen. De bronregel zegt het
scherp: een simpel model is niet hetzelfde als een onschuldig model.

### Twee helpers, omdat drie figuren dezelfde vorm hebben

Ze staan samen in `teken/raster.js`.

`kolommen()` tekent dit-tegenover-dat op een handvol regels, `lijsten()` twee
gekopte lijsten naast elkaar. Drie losse tekeningen zouden drie keer hetzelfde
raster met andere woorden zijn.

In `kolommen()` staat de **koprij buiten elk `f-deel`**, net als de s-doos in
`transitie`: zonder de twee namen erboven zegt geen enkele rij iets, dus mag hij
nooit wegvallen. `agent`, `pakketvraag` en `lijsten()` dragen `f-hard`, want daar
draagt een later deel het **antwoord** — en een half zichtbaar antwoord is verteld
voordat het verteld is.

## De vorm van de tuple: ⟨S, A, E, T, R⟩ en niet ⟨S, A, P, R, γ⟩

De leerboekvorm van een MDP zet de dynamiek in één overgangskans `P(s′ | s, a)`.
Dat past hier slecht, en de scriptie kiest voor precies dit probleem dan ook de
andere vorm (§4.1): `⟨S, A, E, T, R⟩`,
met het exogene deel `E` los van een **deterministische** transitie `T(s, a, e)`.

Dat is hier geen detail maar de hele pointe:

* de transitie is deterministisch — gegeven polder, maatregel en weer staat de
  volgende polder vast, en dat is wat "transparant world model" betekent;
* alle onzekerheid zit in `E`, en `E` is bij ons een **statistiek** en geen
  scenario: STOWA 2019 voor de bui, STOWA 2025-23 voor het neerslagtekort per
  waterschap en per KNMI'23-scenario.

Zou `E` in `P` verstopt zitten, dan was de neerslag- en droogtestatistiek een
implementatiedetail geworden in plaats van een lid van de tuple. Nu is het een
eigen stap, en dat is de stap waar de zaal het meest aan heeft.

`γ` en `π` staan bewust **buiten** de haken: `γ` hoort bij de doelfunctie en `π`
is het antwoord, niet het model. Vandaar `+ γ` en `⇒ π` in de kop.

## Wat de getallen zijn

Alles op het scherm is uit het model gehaald, met twee uitzonderingen die zichzelf
als zodanig aankondigen.

| stap | herkomst |
|---|---|
| ⟳ | de microduck-cijfers uit `microduck_rl`; peil, gemaal en regen uit de rekenkern (piek 36,0 cm); het idioom van de top-downplaten uit `docs/images/vuistregel-tools.svg` |
| S | de referentiepolder: 1000 ha, 5 % open water, gemaal 1,5 m³/s, inlaat 0,35 m³/s |
| A | de zes maatregelen en hun eenheid uit `actions.py`; géén prijzen — die horen bij `R` |
| E | 59 en 87 mm uit de neerslagstatistiek; 279, 473, 237 en 291 mm uit de droogtestatistiek, opgevraagd bij de bron |
| R | de prijzen als bandbreedte — grondprijzen Kadaster/NVM 2025, gemalen De Poel en Galgenrak, STOWA-drainage; de vermeden jaarschade staat er als "nog invullen" |
| γ | **de vorm klopt, het getal niet** — de discontovoet ligt nog niet vast |
| x* | de vier frequentielijnen en de vier pakketprijzen, uit `gen_frequentielijn.py` en `gen_kostencurve.py`; de schadecurve is een streeplijn zonder getal |
| π | de zaaggrens tussen zoeker en policy; de policy bestaat nog niet |

De 23 % spreiding bij `E` is gemeten over alle eenentwintig waterschappen bij een
herhaaltijd van tien jaar: Hunze en Aa's 237 mm tegen Scheldestromen 291 mm. In
het `meta`-blok van de droogtestatistiek staat "> 30 %"; dat geldt niet op deze
herhaaltijd, dus hier staat het gemeten getal en niet het geciteerde.

## De voordeur: wat er staat zonder JavaScript

Deze map is de GitHub Page, dus de deck is ook de pagina die iemand krijgt die de
link doorgestuurd krijgt zonder presentator — of een zoekmachine, of een
linkvoorbeeld. Die zag eerder alleen een titel en een lijstje toetsen.

In `index.html` staat daarom **statische inhoud in `#app`**: de titel, de teaser van
het abstract, en twee links — naar `docs/` en naar de repo. `motor.js` roept
`app.replaceChildren`, dus dat is weg zodra de deck boot en het kost geen enkele
beat. Dezelfde twee links staan in het **hulpscherm** achter `?`, want dat is de enige
plek waar een link niet op een slide staat.

`body` staat op `overflow: hidden` omdat een beamer geen scrollbalk heeft, dus
`.voordeur` scrollt zelf — anders is de tekst afgekapt voor precies de lezer voor wie
hij bedoeld is.

## Waarom geen React en geen Framer Motion

De verkenning in `scratchpad/mdp-zoom/` doet hetzelfde met React, Framer Motion en
htm van esm.sh, en de FLIP-overgang daar is echt beter dan wat hier staat: het lid
groeit van chip naar kaart en de buren schuiven mee.

Twee redenen om dat hier niet te doen:

1. **De kop blijft staan.** Zodra de tuple een vaste inhoudsopgave is en de inhoud
   naar een eigen toneel verhuist, is er geen shared-element transition meer nodig.
   Dat was het enige waar Framer Motion voor binnenkwam.
2. **Een zaal heeft geen wifi.** Drie imports van een CDN zijn drie manieren waarop
   je presentatie niet begint. Hier is geen enkele netwerkaanroep, en `index.html`
   werkt ook op `file://`.

De machinerie in `scratchpad/mdp-zoom/zoom.js` houdt de opgemeten bevindingen over
`mode="popLayout"` bij. Wil je die overgang terug, dan is dat de plek.

### Tekst in een figuur staat altijd even groot op het scherm

Een `font-size` in een SVG telt in **eenheden van de viewBox**, dus hij krimpt
mee zodra een figuur groter wordt uitgetekend. Een plaat met twee helften is
bijna twee keer zo hoog als een enkele, past dus op een kleinere schaal, en dan
staat dezelfde 13 op het scherm ineens op twee derde. Zo werd de deck bij elke
nieuwe plaat een beetje onleesbaarder.

`schaalFiguur()` in `motor.js` meet daarom per beat de werkelijke
uittekenschaal en zet de omgekeerde ervan als `--px` op de figuur; `figuren.css`
rekent daarmee terug:

```
font-size: calc(clamp(15px, 1.31vw, 44px) * var(--px, 1));
```

Eenheden maal schaal is dan weer precies het aantal pixels uit de clamp. Gemeten
op een venster van 1600 bij 900: gewone tekst 21 px, klein 18,6 px, cursief 27,5
px — in **elke** figuur, of hij nu 660 bij 340 is of 920 bij 520. Op 1920 bij
1080 wordt dat 25,2 en 22,3 px, en de ondergrens van 15 en 13 px houdt hem
leesbaar op een klein venster.

De maat groeit mee met **`vw`** en niet met `vmin`. Het toneel deelt zijn breedte
met de zijkolom, dus hoe breed een figuur wordt uitgetekend hangt aan de breedte
van het scherm; met `vmin` blies een smal-en-hoog venster de letters op tot ze de
figuur uit liepen. Nagemeten op 1600×900, 1280×1024 en 1920×1080: geen enkele
regel loopt buiten zijn viewBox.

Dat de letters groter zijn, betekent dat ze in **eenheden** ook breder zijn, en
dat kost marge. Twee kaders zijn daarom ruimer gemaakt dan hun tekening: het
world-modelschema loopt van −30 tot 760 in plaats van 0 tot 720, en de plaat met
de drie knopen is 920 breed. Marge is goedkoper dan een regel die op de ene
schermmaat net wel en op de andere net niet past.

### De figuur krimpt, de bronregel niet

Het toneel is een raster met twee kolommen, en de rechterkolom is een flexkolom
met de figuur erin en de bronregel eronder. Die kolom stond op `align-items:
start`, en dan is hij zo hoog als zijn inhoud: een figuur die hoger is dan breed
genoeg om te passen, groeit er gewoon doorheen en duwt de bronregel onder de
onderrand — waar `overflow: hidden` hem afknipt. Gemeten: bij een beat met drie
regels tekst in de voet was de bron 36 px voorbij de rand en dus wég.

Met `align-items: stretch` (en de zijde op `align-self: start`, want die hoort
wél bovenaan) kent die kolom zijn eigen hoogte, en dan doet `flex: 1 1 auto` op
de figuur zijn werk: hij krimpt tot wat overblijft. De `margin-top: auto` op de
bronregel doet nu ook wat er altijd al stond — hij hangt op elke stap onderaan
het toneel, ook bij de stappen met een tabel in plaats van een figuur.

Wie een figuur hoger dan ongeveer 1,7 : 1 tekent, leunt dus op deze regel. Dat
zijn de twee platen die nat tegen droog en ketting tegen verdeling zetten.

## De clip

`Microduck Sim 2 Real.mp4` staat naast de pagina en niet op YouTube, want geen
netwerk is hier een eis. Hij is opnieuw gecodeerd om onder de 500 kB van
`check-added-large-files` te blijven, zodat hij gewoon in de repo kan:

| | origineel | in de repo |
|---|---|---|
| beeld | H.264 720p, 427 kbit/s | H.264 720p, 113 kbit/s |
| geluid | AAC stereo, 128 kbit/s | AAC mono, 40 kbit/s |
| grootte | 1620 kB | 465 kB |
| SSIM | — | 0,9869 |

De stereo-audio was 380 kB van die 1,6 MB; mono op 40 kbit/s is voor
servogeluid meer dan genoeg. En 720p bleek bij dit bitrate BETER dan 540p
(SSIM 0,9869 tegen 0,9863 bij dezelfde bytes) — downscalen en in de pagina weer
opschalen kost meer dan het aan compressie oplevert. VP9/WebM haalde 412 kB bij
SSIM 0,9871, maar die 53 kB winst is de universele afspeelbaarheid van H.264
niet waard.

Het origineel staat in `scratchpad/` en gaat dus niet mee de repo in.
Regenereren:

```bash
ffmpeg -i bron.mp4 -c:v libx264 -b:v 105k -pass 1 -an -preset veryslow -f mp4 /dev/null
ffmpeg -i bron.mp4 -c:v libx264 -b:v 105k -pass 2 -preset veryslow   -c:a aac -b:a 40k -ac 1 -movflags +faststart "Microduck Sim 2 Real.mp4"
```

## Alles narekenen

Elk getal op het scherm komt uit de rekenkern, en voor elk getal is er een
commando. Draaien vanuit de wortel van de repo:

| script | wat het reproduceert |
|---|---|
| `scripts/gen_polderanimatie.py` | de acht `@keyframes`-blokken van de twee animaties |
| `scripts/gen_verloop.py` | de twee verlopen boven de tijdbalken: de neerslag-afvoergrafiek en het tekort tegen de eigen voorraad |
| `scripts/gen_tweerichting.py` | de kromme bij `T` en de twee lezingen ervan, heen met `simulate` en terug met `solve` |
| `scripts/gen_frequentielijn.py` | de vier frequentielijnen, de acht losse runs en hun "veilig tot"-waarden |
| `scripts/gen_kostencurve.py` | de kostencurve en de vier prijzen onder de eis-as |
| `scripts/gen_maatregelcurves.py` | de drie responsecurven — achtergrond, staat niet op het scherm |
| `scripts/gen_pakkettabel.py` | de pakketten per eis — achtergrond, staat niet op het scherm |
| `scripts/gen_statistiek.py` | de twee statistiekfiguren van stap E |
| `scripts/gen_voorkeursvolgorde.py` | de twee heen-en-weer-beats: de zwaardere buien en de telling over 312 bedreigingen |

Ze geven padjes die in `teken/` gaan, of keyframes die in `gegenereerd.css`
tussen de `GEGENEREERD`-bakens gaan. Alleen dat CSS-blok heeft die bakens; de
padjes staan met een comment erboven, en dus is er geen manier om te controleren
of ze nog bij de kern horen. Dat is een open punt, zie onderaan. `gen_maatregelcurves` en `gen_pakkettabel`
staan er voor het narekenen: hun getallen komen niet meer op een scherm, maar ze
zijn wél de onderbouwing van wat de kostencurve beweert.

Alle vier delen dezelfde twee uitgangspunten, en die staan bovenaan elk script:

* **de referentiepolder** — 1000 ha, 5 % open water, gemaal 1,5 m³/s;
* **de referentiebui** — zomer, herhaaltijd 10 jaar, 192 uur, regime R, patroon
  p1c, 2 dagen afvoer. Voor de frequentielijn varieert alleen de herhaaltijd.

Er zit geen toeval in: de pakketzoeker enumereert de mixen en lost per mix de
maatvoering op, dus dezelfde invoer geeft hetzelfde pakket. Wijkt een getal af
na een wijziging in de kern, dan is dat een echt verschil en geen ruis.

## Waar de verwijzingen liggen

Twee dingen waar deze README naar wijst staan **niet in de repo**, want
`scratchpad/` is gitignored:

* `scratchpad/Masters_Thesis_Report_Final_Version.pdf` — de scriptie waar de vorm
  van de tuple uit komt (§3.1 voor het formalisme, §4.1 voor deze variant);
* `scratchpad/mdp-zoom/` — de React-verkenning waar deze pagina uit is gegroeid.

De scriptie is van **Yaren Aslan** (TU Delft); §3.1 geeft het formalisme en §4.1
de variant die deze kopregel gebruikt.

Wie de repo verst kloont heeft ze dus niet. De presentatie werkt zelfstandig; de
verwijzingen zijn er voor wie wil weten waarom de vorm zo is.

## Open punten

* De discontovoet bij `γ`, zie hierboven.
* **De gegenereerde padjes hebben geen bakens.** `gegenereerd.css` staat tussen
  twee `GEGENEREERD`-regels en is dus na te rekenen; de padjes in `teken/` staan
  met alleen een comment erboven. Er is geen manier om te controleren of een pad
  in de deck nog zegt wat de kern zegt. De ingreep: laat elke `gen_*.py` zijn
  uitvoer tussen dezelfde bakens printen, zet ze in één `gegenereerd.js`, en laat
  één script alle negen opnieuw draaien en tegen die blokken diffen. Voor een
  deck die beweert dat de getallen uit de kern komen, is dat het verschil tussen
  een comment en een bewijs.
* **Twee stille faalpaden.** Een onbekende naam in `figuur:` wordt
  `FIGUREN[naam] || ""`, dus een leeg blok; een `nadruk`-index zonder
  bijbehorende `data-deel` laat niets oplichten. Beide zijn op een beamer
  onzichtbaar. Vandaag klopt alles — de controle hieronder loopt schoon — maar
  het klopt bij toeval en niet doordat iets het tegenhoudt.
* **`rijenTabel` staat er twee keer** in `motor.js`, en de eerste is
  onbereikbaar: twee `function`-declaraties in dezelfde scope, dus de tweede
  overschrijft de eerste. Niets breekt, want `stemAf()` doet het werk dat de
  eerste zelf deed. Weg te gooien.
* Geen tests, maar de overloopcontrole is wél te draaien in plaats van te
  geloven. Open de deck en voer dit uit in de console; hij loopt elke beat langs
  en meldt welke buiten het venster valt:

      const uit = [], de = document.documentElement;
      for (const st of INHOUD.stappen)
        for (let i = 1; i <= st.beats.length; i++) {
          location.hash = "#" + st.sleutel + "." + i;
          dispatchEvent(new HashChangeEvent("hashchange"));
          await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
          const ox = de.scrollWidth - innerWidth, oy = de.scrollHeight - innerHeight;
          if (ox > 0 || oy > 0) uit.push(st.sleutel + "." + i);
        }
      uit

  Op alle 39 beats is er geen overloop in x of y, ook niet op 646 × 781, in licht
  en in donker.
* Donkere modus volgt `prefers-color-scheme` en is nagekeken, maar niet op een
  echte beamer — die staan bijna altijd in licht.
* Niet getest op mobiel. De kop gebruikt `flex-wrap: nowrap`, dus op een heel
  smal scherm wordt hij liever klein dan dat hij wikkelt.
