# De polder als MDP — de presentatievorm

Acht stappen door één formalisme, met de tuple als vaste kopregel. De kop is de
inhoudsopgave: hij staat er altijd, en het lid waar je bent staat omkaderd. Het
toneel eronder hoort bij dat ene lid, en de voet draagt de ene zin die je zegt.

```
┌──────────────────────────────────────────────────────────┐
│  ⟳ ⇒ M = ⟨ S , A , E , T , R ⟩  +  γ  ⇒  π               │  de kop = de TOC
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

## Bediening

| toets | wat |
|---|---|
| → spatie Enter | volgende beat |
| ← Backspace | vorige beat |
| ↓ ↑ | volgende of vorige stap |
| 1 … 8 | rechtstreeks naar een stap |
| Esc | terug naar de titel |
| f | volledig scherm |
| ? | de hulp |

Klikken werkt ook: rechts vooruit, de linkerstrook terug — maar alleen op het
toneel en de voet, zodat een klik om het venster naar voren te halen niet
ongevraagd een beat opschuift. In de kop is een klik een sprong naar dat lid.

`#E.4` in de URL opent stap `E` op beat 4, ook als de pagina al open staat. Zo
kun je één beat delen in een issue of naast je andere slides zetten.

## De bestanden

| bestand | wat |
|---|---|
| `index.html` | het omhulsel |
| `Microduck Sim 2 Real.mp4` | de openingsclip, 1,6 MB — lokaal, niet van YouTube |
| `inhoud.js` | **de inhoud** — dit is het enige bestand dat je normaal aanraakt |
| `presentatie.js` | de machinerie plus de drie figuren |
| `style.css` | de opmaak |

## ⟳ — de brug die de titel belooft

De titel is *from robots to polders*, dus de talk hoort bij de robot te beginnen.
Stap `⟳` doet dat in drie zetten:

1. **de clip.** Een microduck loopt, links in de simulatie en rechts op een echte
   vloer. Twee beats, en het fragment loopt door in plaats van te herstarten.
2. **het schema.** Toestand, actie, exogeen, transitie, beloning, policy — met de
   symbolen die daarna elk hun eigen stap krijgen.
3. **de wissel.** De vulling gaat van de microduck naar de polder terwijl de
   tekening staat. In de code is dat één `wereldmodel(...)` met twee vullingen,
   zodat "hetzelfde schema" ook letterlijk waar is en niet twee SVG's die uit
   elkaar kunnen lopen.

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
tekort zich opbouwt. De watergang krimpt binnen zijn oevers en het land droogt
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
levert zes `@keyframes`-blokken: nat `polderpeil`, `poldergemaal`,
`polderregen` en `polderinundatie`; droog `polderdroogte` en `polderdorst`.

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

## Het gebied van boven, in 2,5D

Na de doorsnede kantelt het beeld: van "hoe hoog komt het" naar "wat kun je
eraan doen", en dat is ruimtelijk. Twee tekeningen, negen beats.

**Eén polder, vier vuistregels.** Een plaat van boven met dikte, een strook open
water erover, en dan achter elkaar: vasthouden kleurt een deel van het land in,
bergen verbreedt de strook, afvoeren maakt het gemaal zwaarder. De basis van dit
idioom staat in `docs/images/vuistregel-tools.svg`; hier is het gekanteld en in
beats gezet.

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
| A | eenheidsprijzen uit `actions.py` — grondprijzen Kadaster/NVM 2025, gemalen De Poel en Galgenrak, STOWA-drainage |
| E | 59 en 87 mm uit de neerslagstatistiek; 279, 473, 237 en 291 mm uit de droogtestatistiek, opgevraagd bij de bron |
| R | de omslagprijzen € 0,14 mln en € 1,5 mln per cm drooglegging |
| γ | **de vorm klopt, het getal niet** — de discontovoet ligt nog niet vast |
| π | de zaaggrens tussen zoeker en policy; de policy bestaat nog niet |

De 23 % spreiding bij `E` is gemeten over alle eenentwintig waterschappen bij een
herhaaltijd van tien jaar: Hunze en Aa's 237 mm tegen Scheldestromen 291 mm. In
het `meta`-blok van de droogtestatistiek staat "> 30 %"; dat geldt niet op deze
herhaaltijd, dus hier staat het gemeten getal en niet het geciteerde.

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
* Geen tests. Wat er staat is met de hand nagekeken en met opgemeten frames:
  op alle 32 beats is er geen overloop in x of y, ook niet op 646 × 781.
* Donkere modus volgt `prefers-color-scheme` en is nagekeken, maar niet op een
  echte beamer — die staan bijna altijd in licht.
* Niet getest op mobiel. De kop gebruikt `flex-wrap: nowrap`, dus op een heel
  smal scherm wordt hij liever klein dan dat hij wikkelt.
