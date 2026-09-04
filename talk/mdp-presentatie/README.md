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
| `presentatie.js` | de machinerie plus de drie figuren |
| `style.css` | de opmaak |

## ⟳ — de brug die de titel belooft

De titel is *from robots to polders*, dus de talk hoort bij de robot te beginnen.
Stap `⟳` doet dat in drie zetten:

0. **het titelscherm.** Alleen de kop, en de voet zegt waar we beginnen: bij een
   mini-eendrobot van vijfentwintig centimeter. Er stond een ondertitel met de
   stelling, maar op een titelscherm is dat een tweede bewering naast een titel
   die het al doet.
1. **de clip.** Een microduck loopt, links in de simulatie en rechts op een echte
   vloer. Eén beat; het fragment loopt door in plaats van te herstarten.
2. **het schema.** Toestand, actie, exogeen, transitie, beloning, policy — met de
   symbolen die daarna elk hun eigen stap krijgen.
3. **de wissel.** De vulling gaat van de microduck naar de polder terwijl de
   tekening staat. In de code is dat één `wereldmodel(...)` met twee vullingen,
   zodat "hetzelfde schema" ook letterlijk waar is en niet twee SVG's die uit
   elkaar kunnen lopen.

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

Wat er ónder de naam van de transitie staat, verschilt per vulling. Bij de
microduck staat er alleen "de natuurkunde van bewegen" — niet *van lopen*, want
in zijn oefenwereld skeelert en schommelt hij ook, en de naam zegt daar verder
alles. Bij de polder is juist **waarom** het geen netwerk is het punt, dus daar
staan twee regels onder: "geen neuraal netwerk" en "opgeschreven vuistregels".
Zonder onderregels staat de naam midden in de doos in plaats van bovenin.

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
de tweede stap al op gezet; wij hebben de transitie en die stap nog niet. Daarom
eindigt het robotschema op "en zo heeft hij leren lopen" en het polderschema op
dezelfde plek met een vraag: **"en hoe laten we de polder lopen naar 2100?"**
Diezelfde zin staat er op `π`, waar hij de open vraag van de talk is. Zeg dus
**niet** dat de dynamica in robotica geleerd wordt omdat je hem niet kunt
opschrijven — voor een lopende robot is dat onjuist, en iemand uit de robotica
weet dat.

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

### De vier maatregelen staan op één beat

Ze stonden er als vier, die de plaat één laag per keer opbouwden. Dit publiek kent
wateroverlast, watertekort en de maatregelen die erbij horen, en een opbouw léért
dan iets wat de zaal al weet. Eén beat met alle drie de ingrepen tegelijk is de
snelle uitleg, visueel gemaakt — en die snelheid is waar het tijdslot om vraagt.

Wat blijft is de tweedeling die niet bekend is: nat is een **ketting** en droog een
**verdeling**. Die twee houden hun eigen beat, want een zaal die per polder denkt
heeft daar niets aan liggen.

## De animaties

Twee bewegende beelden, en ze delen één gegenereerd blok in `style.css`.

**De bui van boven** (bij `⟳`, de tegenhanger van de microduck-clip). Van boven
zie je geen diepte, dus een stijgend peil is onzichtbaar zolang het in de
watergang past. Wat je wél ziet is het moment dat het eroverheen gaat: dan zwelt
de watergang en loopt het land onder. De overstroming en de watergang zijn
daarom **één vlak** — van boven is een overstroming niets anders dan de
watergang die buiten zijn oevers komt.

**De peilband in doorsnede** (bij `T`). Dit is de enige stap waar de band zelf
het argument is, en een band is van boven niet te zien.

**Het seizoen van boven** (bij `⟳`, de spiegel van de bui). Andere klok: geen
negen dagen maar 1 april tot 1 oktober, want dat is de tijdschaal waarop een
tekort zich opbouwt. Die klok loopt in 18 seconden rond tegen 15 voor de bui —
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

en zet de uitvoer tussen de twee `GEGENEREERD`-bakens in `style.css`. Het script
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
gecachete `presentatie.js`: `python3 -m http.server` stuurt geen no-cache, dus
een gewone verversing haalt het oude script op. Één harde reload (Cmd+Shift+R)
en het is weg.

## Het gebied van boven, in 2,5D

Na de doorsnede kantelt het beeld: van "hoe hoog komt het" naar "wat kun je
eraan doen", en dat is ruimtelijk. Twee tekeningen, negen beats.

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

**Drie knopen, twee koppelingen.** Dezelfde drie gebieden, en wat verandert is
alleen wat ze met elkaar doet:

* **nat is een ketting** — wat A wegpompt is de aanvoer van B, en het water loopt
  langs een boom naar buiten. De uitkomst die telt is niet welk gemaal te klein
  is maar welk gemaal *geblokkeerd* staat, en bovenstrooms bijbouwen doet daar
  niets aan;
* **droog is een verdeling** — ze staan naast elkaar aan dezelfde eindige bron,
  geen volgorde lost dat op, en de wet zegt in welke orde er verdeeld wordt.

Dat de topologie het verschil maakt en niet de hydrologie, is precies waarom er
twee gereedschappen zijn en niet één.

**De projectie is gerekend, niet geplaatst.** Alle platen, vlakken, wanden en
pijlen komen uit één axonometrische formule in `presentatie.js`:

```
schermx = midx + (x − y) · cos 30° · s
schermy = midy + (x + y) · sin 30° · s
```

met `x` en `y` van 0 tot 1 over de plaat en `s` als halve diagonaal. Met de hand
geplaatste ruiten lopen onherroepelijk uit elkaar zodra er één maat verandert;
`isoVlak`, `isoWanden`, `isoPlaat` en `isoPijl` doen het werk, en `style.css`
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
Geef de stand die je wilt en je krijgt de maatregel — dat is wat de
`tweerichting`-figuur laat zien, met de rode ring om wat je niet weet.

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

Op het scherm staat er **één** naam, en dat is inverse kinematics: de talk opent
met een robot, dus die brug ligt er al. Eén naam per beat is genoeg; de andere
drie horen in de zaal alleen als iemand ernaar vraagt.

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

Wat daar houdt is de **rangorde**: in alle drie de kolommen ligt geen maatregel onder
bergen onder vasthouden onder afvoeren. Wat niet houdt zijn de absolute getallen. Dat
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

Daarom loopt deze stap door hetzelfde schema als `T`, en begint hij op precies
het beeld waar de transitie eindigde: de maatregel gaat erin, maar wie hem kiest
staat er niet. Op die eerste beat blijft het policyblok **weg** en niet gedempt —
de zin zegt dat wie kiest er niet staat, en dan mag hij er niet al staan. De
tweede beat zet het blok erbij en sluit de lus. Zo is "wat mist er nog" een
plaatje in plaats van een bewering.

De derde beat is de reden dat de zoeker blijft bestaan naast de policy: omdat hij
exact is, kun je de policy erop **toetsen**. Op een horizon van één jaar moeten ze
hetzelfde zeggen — zegt de policy iets anders, dan is dat een fout in de policy en
niet een inzicht.

**Drie beats, en dat waren er acht.** Het tijdslot is vijftien minuten, en de
langste sectie mag niet die over het onderdeel zijn dat nog niet bestaat. Het
argument is niet gesneden maar samengevouwen: de lus rond, waarom een policy
misschien niet nodig is, en waarom in de tijd wel. Wat eruit ging zijn de
tussenstappen die het in drie stappen ook doet.

## De vijf punten van de sessievoorzitter

De voorzitter van de sessie vroeg vijf dingen op de slides. Ze staan er niet als
een eigen blok maar **in de stap waar ze thuishoren**, want vier van de vijf zijn
uitspraken over iets dat al een plek in de kop heeft.

| gevraagd | waar het staat | figuur |
|---|---|---|
| de meerwaarde tegenover conventioneel modelleren | `T`, beat 3 | `ribasim` |
| hoe de agent pakketten verkent en waardeert | `x*`, beat 11–12 | `pakketvraag` |
| waar het werkt en waar niet | `x*`, beat 13–14 | `grenzen` |
| wat de agent doet en zijn rol in de workflow | `π`, beat 1–3 | `agent` |

**Punt twee staat nog open**: wat "world model" hier betekent tegenover AI en
robotica. Er stond een beat met een tabel die de herkomst van `T` naast die van
een robot legde, en die klopte niet — "leren uit data" is niet wat elk
robotica-world-model doet, en "drie regels" verkleint onze waterbalans tot iets
wat hij niet is. Een fout antwoord op de scherpste vraag uit de zaal is erger dan
geen antwoord, dus is hij eruit. Wat er nu van overblijft staat bij `T` beat 2 —
"in de robotica wordt hij geleerd, bij ons is hij exact" — en dat is de helft.

De kop is niet aangeraakt. Dat is geen zuinigheid: de agent is geen term in de
formule, en een zesde symbool ernaast zou beweren dat hij dat wel is.

**`ribasim` antwoordt niet met "wij zijn beter" of "wij zijn sneller"** maar met
wat vastligt en wat beweegt. Zet de polder vast en laat het water bewegen, dan
kun je vragen wat er gebeurt. Zet de bui vast en laat de polder bewegen, dan kun
je vragen hoe de polder moet worden.

En de voetregel trekt in één regel de conclusie die eruit volgt: **Ribasim is een
world model voor het dráaien, het onze voor het ontwerpen.** Dat is de juiste
landing en niet alleen de vriendelijkste — de term hangt aan de vraag die je
stelt en niet aan wie hem gebruikt. Eén regel, geen drie: een plaat met een
tabel erboven heeft geen alinea eronder nodig.

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
het abstract, en twee links — naar `docs/` en naar de repo. `presentatie.js` roept
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
| `scripts/gen_frequentielijn.py` | de vier frequentielijnen, de acht losse runs en hun "veilig tot"-waarden |
| `scripts/gen_kostencurve.py` | de kostencurve en de vier prijzen onder de eis-as |
| `scripts/gen_maatregelcurves.py` | de drie responsecurven — achtergrond, staat niet op het scherm |
| `scripts/gen_pakkettabel.py` | de pakketten per eis — achtergrond, staat niet op het scherm |
| `scripts/gen_statistiek.py` | de twee statistiekfiguren van stap E |

Ze geven padjes of keyframes die in `presentatie.js` respectievelijk `style.css`
tussen de `GEGENEREERD`-bakens gaan. `gen_maatregelcurves` en `gen_pakkettabel`
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
