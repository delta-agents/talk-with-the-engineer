# Voorstel Deltares Software Days — world models in hydrologie



Vervolg op *Conversational Agents in Hydrology* (18 nov 2025)
Werktitel: **From Robots to Polders: World Models in Hydrology**
Inzenders: Ton Botterhuis en Mattijn van Hoek
Datum: 2026-08-21 · Status: concept, deel 2 van de demo is gebouwd



---



## 1. De pitch in drie regels



Vorig jaar presenteerden we `talk-with-the-engineer` als conversational agent. Dat
frame verstopte het interessantere deel: de vuistregels zijn een
**actie-geconditioneerd model van een watersysteem dat je in milliseconden kunt
ondervragen in plaats van de werkelijkheid**. Dat is de definitie van een world
model.



De literatuur legt world models uit via neurale netwerken. Maar het netwerk is
alleen *hoe je aan de dynamiek komt als je die niet kunt opschrijven*. In een
polder kun je dat wel — het is een massabalans.



Dus we nemen onze eigen claim serieus en toetsen hem, onderdeel voor onderdeel.
Op een deel scoren we, op een deel niet. Het gat blijkt klein, specifiek, en
dichtbaar zonder een gram machine learning.



---



## 1b. De zaal



**Wie er zit:** hydrologen en softwareontwikkelaars van state-of-the-art
hydrologische modellen, plus twee of drie strategische beleidsmakers die die
modellen gebruiken om te bepalen welke maatregelen in welke mate goed zijn.



**Waar deze zaal op reageert.** Een model wordt hier automatisch beoordeeld op
fidelity — resolutie, procesdekking, validatie — want dat is hun vak. Zodra er een
massabalans op het scherm staat, is de conclusie "grof" al getrokken voordat de
vraag gehoord is. Dat is geen begripsprobleem maar een **reflex op modelkwaliteit**,
en je moet hem vóór zijn in plaats van hem weerspreken.



En de vraag gaat over iets wat **orthogonaal is aan fidelity**:



| | |
|---|---|
| **Fidelity** | hoe goed benadert het model de werkelijkheid? |
| **Rol** | kun je er beslissingen in zoeken? |



Dat zijn twee assen, geen één. Hun modellen scoren hoog op de eerste as en — dit
is het interessante deel — **laag op de tweede**. Niet omdat ze slecht zijn, maar
omdat ze "wat gebeurt er" beantwoorden in plaats van "wat gebeurt er als ik dít
kies", omdat hun uitvoer niet in dezelfde ruimte ligt als hun invoer, en omdat ze
te langzaam zijn om binnen een zoeklus te bevragen.



**De aanpak: maak de eenvoud expliciet de methode.** Niet verdedigen, maar
vooraan zetten:



> Wij bouwen bewust het kleinste systeem dat alle zeven onderdelen heeft, zodat
> je de structuur kunt zien zonder discussie over fysica.



Dat is een **minimal working example**. Softwareontwikkelaars respecteren dat
concept diep — het is hun eigen minimal reproducible example. Daarmee kantelt
"te simplistisch" van zwakte naar ontwerpkeuze, en wel vóórdat de reflex kan
vuren.



**Drie consequenties voor de talk:**



1. **Zeg het op slide 2, niet op slide 10.** Expliciet: dit is geen claim over
   hydrologie, dit is een claim over structuur. We competen niet op fysica.
2. **Getallen zijn geen resultaten.** Vorig jaar stonden er zes slides met
   `input ∆Q → output ∆H` en concrete uitkomsten (53 % van het gebied voor
   retentie, 68 % open water). Voor een modelbouwer is dat geen indicatie maar
   een foutmelding. Comprimeer die zes naar één slide die het *interface* toont,
   niet de uitkomsten. Daarmee verdwijnt het fidelity-doelwit uit de deck.
3. **Richt de slotvraag op hún modellen.** Niet "is ons model goed genoeg", maar
   "kan jullie model dit ook". Bij hen ontbreekt niet de resolutie — die is
   ruimschoots in orde — maar de structuur. Dat is een echte, bruikbare vraag en
   het is bovendien vleiend zonder leeg te zijn.



**En voor de beleidsmakers in de zaal** werkt de demo op een andere laag: die
laat niet structuur zien maar gedrag — wat een norm kost, en welke maatregel bij
welke bui aan de beurt is. Vasthouden is goedkoop maar loopt vast op een optimum;
bergen en afvoeren gaan verder. Waar dat omslagpunt ligt is een beleidsvraag, en
het model rekent hem zelf uit. Eén demo, twee publieken.



---



## 2. Abstract (EN, submission-ready, ~230 woorden)



> **What if I do this?**
> *Rules of thumb as a world model for hydrology — no neural networks required*
>
> Hydrology is good at forecasting: how high will the water get? It is less well
> equipped for the question an engineer actually asks: how high will it get *if I
> do this*? That second question is not a prediction. It needs a model of what
> your choices do to the system.
>
> Last year we presented *Talk with the Engineer*: a set of hydrological rules of
> thumb, exposed as tools a language model can call, answering questions such as
> *"how much more pumping capacity do I need to lower the peak water level by
> 90 cm in a 1-in-10-year event?"* We framed it as a conversational agent. We now
> think that framing hid the more interesting part.
>
> In machine learning, a model that answers what-if questions about a system —
> cheap, fast, and good enough to plan in — is called a *world model*. The
> literature explains them through neural networks, but the network is only *how
> you obtain the dynamics when you cannot write them down*. In a polder, you can:
> it is a mass balance.
>
> So we take our own claim seriously and test it. We walk through the anatomy of a
> world model — state, action, exogenous input, transition, rollout, objective,
> planning — and check our tools against it, part by part. We pass on some and
> fail on others. The gap turns out to be small, specific, and closable without
> any machine learning, and we show what closing it does.
>
> We suspect a lot of the tooling in this room is in the same position.



---



## 3. De toets: anatomie van een world model



Zeven onderdelen. Dit is het inhoudelijke skelet van de talk en tegelijk een
checklist die de zaal op eigen code kan leggen.



| # | Onderdeel | Vraag |
|---|---|---|
| 1 | **Toestand** `s` | Wat moet je van het systeem weten om zijn toekomst te voorspellen? |
| 2 | **Actie** `a` | Wat kun jij veranderen? |
| 3 | **Exogeen** `w` | Wat verandert er buiten jou om? |
| 4 | **Gesloten transitie** `s' = f(s, a, w)` | Ligt de uitvoer in dezelfde ruimte als de invoer? |
| 5 | **Rollout** | Kun je stap 4 herhaald toepassen? |
| 6 | **Doelfunctie** `J` | Welk getal maakt het ene traject beter dan het andere? |
| 7 | **Planning in het model** | Kies je je actie door in `f` te zoeken in plaats van in de werkelijkheid? |



Punt 4 is de scherpe: **uitvoertype = invoertype**. Dat is het verschil tussen een
voorspelling en een model waarin je kunt leven.



---



## 4. Onze eerlijke score



| # | Onderdeel | vóór (talk 2025) | ná (aug 2026) |
|---|---|---|---|
| 1 | Toestand | ✅ oppervlak, % open water, afvoercapaciteit, afvoervertraging | ✅ nu één expliciet object, vijf velden |
| 2 | Actie | ✅ retain / store / discharge, met maatvoering | ✅ getypeerde acties met eigen eenheid en prijs |
| 3 | Exogeen | ✅ bui uit STOWA-2019: terugkeertijd, seizoen, duur, patroon, regime | ✅ ongewijzigd |
| 4 | Gesloten transitie | ⚠️ **nee** — we geven Δh terug, geen volgende toestand | ✅ `apply(s, a) → s'`, uitvoertype = invoertype |
| 5 | Rollout | ❌ volgt uit 4 | ✅ volgt inderdaad gratis |
| 6 | Doelfunctie | ❌ geen kosten, geen €, geen normoverschrijding | ⚠️ de plek is er, de prijzen nog niet |
| 7 | Planning | ⚠️ één stap — de inverse tools (Δh → maatvoering) zijn precies dit, maar voor één gebeurtenis | ⚠️ de buitenste loop over terugkeertijden is de laatste stap |



**Vóór: 3 volledig, 2 gedeeltelijk, 2 afwezig. Ná: 5 volledig, 2 gedeeltelijk.**



> **Voor de deck:** presenteer op slide 10 alleen de linkerkolom, expliciet als
> momentopname van vorig jaar. Anders vervalt de spanning die slide 11 en 12 moeten
> oplossen. De rechterkolom is de payoff van slide 12, niet de opzet van slide 10.



Dat is een beter verhaal dan "wij hebben een world model", om drie redenen: het is
waar, het gat is aanwijsbaar, en de zaal kan de score op zijn eigen tools
narekenen.



De eerlijke samenvatting: we hebben een **surrogaat met een actie-geconditioneerde
interface** — het moeilijke en waardevolle deel — maar het is nog geen world
model, want de lus is niet gesloten in toestandsruimte.



---



## 5. Het ene ontbrekende stuk



Nu geldt: `g(s, a, w) → Δh`. Δh is een *uitleesbare grootheid*, geen toestand. Je
kunt hem niet terugvoeren.



De fix in één zin: **laat maatregelen de toestand permanent veranderen in plaats
van alleen een effect rapporteren.**



Na een `store`-maatregel is % open water blijvend hoger — en dát is de nieuwe
toestand. Dan:



- **punt 4** is gesloten: `(% open water, pompcapaciteit, retentie-areaal)` in,
  hetzelfde eruit;
- **punt 5** volgt gratis: jaar voor jaar een bui trekken uit de STOWA-statistiek;
- **punt 6** is een prijslijst met **drie** posten: € per ha open water (bergen),
  € per m³/min pompcapaciteit (afvoeren), € per ha land (vasthouden). Die eenheden
  zijn niet uitwisselbaar: bij bergen koop je de grond, bij vasthouden het recht om
  hem af en toe onder water te zetten;
- **punt 7** wordt een loop over terugkeertijden.



En dan verschijnt het gedrag dat het interessant maakt: niet **of** je investeert
maar **hoeveel** een norm kost, en welke maatregel bij welke bui aan de beurt is.
Vasthouden haalt maximaal 24 cm en heeft daarna een optimum; bergen en afvoeren gaan
verder. Waar dat omslagpunt ligt rekent het model zelf uit.



Geen neuraal netwerk nodig. Niet één.



---



## 6. Waarom "zonder neurale netwerken" het argument is, niet de beperking



Drie concrete winsten, geen bescheidenheid:



1. **Auditeerbaar.** We kunnen onze eigen claim onderdeel voor onderdeel nalopen
   omdat elk onderdeel leesbaar is. Bij een latente Dreamer-dynamiek kun je dat
   niet — je kunt alleen de performance meten.
2. **Exacte transitie ⇒ schone foutdiagnose.** De transitie is geen benadering met
   een leerfout. Gaat de planning mis, dan is het een *algoritmefout*, niet een
   *modelfout*. Die scheiding is bij een geleerd world model het lastigste
   probleem dat er is.
3. **Uitlegbaar in twintig minuten.** De hele anatomie past op één polder van
   4000 ha en drie regels massabalans.



De punchline voor de zaal: **het neurale netwerk is het minst essentiële onderdeel
van een world model.** Je hebt het nodig zodra je de dynamiek niet kunt
opschrijven — niet eerder.



---



## 7. Waar de LLM dan zit



Belangrijk om expliciet te maken, want dit is de zelfcorrectie op vorig jaar.



De LLM **is** het world model niet. De LLM is de **interface**: hij vertaalt een
vraag in natuurlijke taal naar een query op het model, en het resultaat terug naar
twee uitlegbare zinnen (slide 17 van vorig jaar — compact, uitlegbaar op
A1/B1-niveau).



Dat is echt nuttig. Maar het staat volledig los van de vraag of je een world model
hebt. Precies daarom verstopte het frame "conversational agent" wat we hadden
gebouwd. Dat toegeven kost niets en levert geloofwaardigheid op.



---



## 8. Slide-outline (~12 slides, slotlengte-onafhankelijk)



De term *world model* valt pas op slide 4, en dan als naam voor iets dat de zaal
op slide 3 al zelf heeft zien gebeuren. Niet als geïmporteerd jargon.



| # | Slide | Kern |
|---|---|---|
| 1 | Titel | |
| 2 | Waar we vorig jaar stopten | Vuistregels als tools, twee uitlegbare zinnen. Eén slide, geen recap-blok. |
| 3 | **Twee soorten vragen** | "Hoe hoog komt het water?" tegenover "hoe hoog komt het *als ik dit doe*?" De tweede vraag is geen voorspelling — die vereist een model van wat jouw keuzes doen. Nul jargon. |
| 4 | Hier heeft de AI-wereld een naam voor | *World model*: dynamiek die je bevraagt in plaats van de werkelijkheid. Robotica, Dreamer. En altijd met een netwerk erin. |
| 5 | Het vermoeden | "Volgens ons hebben wij er ook een. Zonder netwerk." Expliciet als hypothese, niet als claim. |
| 6 | **De anatomie** | De zeven onderdelen. De ankerslide. |
| 7 | Toestand / actie / exogeen | Onze componenten-slide van vorig jaar, met de nieuwe labels erop. Het kwartje. |
| 8 | De transitie | De massabalans. Drie regels. Hier is de causaliteit zichtbaar. |
| 9 | Twee richtingen | Maatvoering → Δh is rollout. Δh → maatvoering is planning. Dat tweede hadden we al. |
| 10 | **De score** | 3 ✅ / 2 ⚠️ / 2 ❌. Eerlijk. |
| 11 | Het gat, en de fix | Laat de maatregel de toestand veranderen. Vier gevolgen. |
| 12 | **Demo** | De lus gesloten. Eén norm, dertien terugkeertijden, wat het kost. Live. |
| 13 | Voor de zaal | Leg de zeven vragen op je eigen tool. Je bent dichterbij dan je denkt. |



Vervalt uit de deck van vorig jaar: het hele LLM → AI Agents → Delta Agents blok
(slides 3–6). Dat is het frame dat we juist verlaten.



---



## 9. Demo



Concreet, en te bouwen op wat er staat:



- Polder: 4000 ha, 3,5 % open water (140 ha), 5 m³/s afvoer. Dezelfde polder als het
  rekenblad waartegen de kern gevalideerd is.
- **Deel 1** — zoals vorig jaar: forward en inverse, één bui. Bekend terrein.
- **Deel 2** — de lus gesloten: maatregelen veranderen de toestand permanent, en de
  bui is de **testas**. Kies een norm, en zoek per terugkeertijd het goedkoopste
  maatregelpakket dat eronder blijft.
- **Uitkomst**: een robuustheidscurve — benodigde investering tegen terugkeertijd.
  *"Dit pakket houdt tot T=100; voor T=1000 is nog zóveel extra nodig."*
- Geen klimaatdrift, geen tijdas, geen zaagtand. Er zit dus geen aanname over de
  toekomst in de demo.



**Runtime, gemeten:** één doorrekening 0,015 ms, één inverse berekening 1,5 ms. De hele
curve over dertien terugkeertijden is een kwestie van tienden van seconden. Vóór dit
werk kostte één toolaanroep 0,9 tot 1,5 seconde — een factor 600.



Wat de demo bewijst: het gat tussen "vuistregel-tool" en "world model" is
overbrugbaar in een middag, en de overbrugging is niet ML.



Wat de demo ook oplevert, en dat is geen bijzaak voor déze zaal: **twee van de drie
maatregelen hebben een optimum.** Bij de referentiebui, met een stijging van 181 cm zonder
maatregelen:

| maatregel | laagst haalbaar | bereik | bij |
|---|---|---|---|
| afvoeren | 0 cm | 181 cm | 12 m³/s |
| bergen | 9 cm | 172 cm | al het land omgezet |
| vasthouden | 155 cm | **26 cm** | 3314 ha land |

Vasthouden loopt dus vast: voorbij een zeker areaal valt de vertraagde afvoer van het ene
deel samen met de piek van het andere, en wordt het weer slechter. Dat staat ook zo in het
rekenblad van 2024, dus het is geen artefact van onze herbouw.

Bergen kent hetzelfde effect, maar pas dicht bij 100 % open water: dan is er geen land
meer dat de afvoer over meerdere dagen spreidt, en ontvangt het open water de neerslag
ongedempt. Bij realistische percentages weegt de bergingswinst zwaarder.

Beide zijn niet-triviale, niet-monotone resultaten uit drie regels massabalans. Een
eenvoudig model dat een verrassend antwoord geeft is het beste weerwoord op "te
simplistisch" — sterker dan elke verdediging.



---



## 10. Titelvarianten



**Randvoorwaarde:** het merendeel van de zaal kent de term *world model* niet. Een
titel die de term als vraag stelt ("Is a rule of thumb a world model?") is dan geen
hook maar een raadsel — je moet het concept al kennen om de spanning te voelen.



Het principe dat wel werkt: **begin bij wat ze herkennen, laat de term de
onthulling zijn.** Wat iedereen daar herkent is de vraag *"wat gebeurt er als ik
dit doe?"* — en dat is exact de technische kern (actie-geconditioneerd) én het
verschil met een voorspelling.



**Harde eis:** *world model(s)* moet in de titel staan, zodat er later naar
verwezen kan worden. De titel hoeft het concept niet te onderwijzen — dat doen
slides 3–4 — maar moet wel houvast geven aan wie de term niet kent.



**Tweede eis, uit §1b:** de titel mag geen fidelity-reflex uitlokken. Een titel die
ons model als onderwerp neemt ("*a world model for a polder*") nodigt precies de
reactie van vorig jaar uit — *jullie poldermodel is simplistisch*. De titel moet
signaleren dat de eenvoud een keuze is, of het onderwerp bij hún modellen leggen.



Vier strategieën.



### A — Bewuste minimalisatie: maak van de eenvoud een methode



| Variant | Waarom het werkt |
|---|---|
| **The smallest possible world model**<br>*what it takes to plan in a hydrological model, and not just predict with it* | ⭐ *aanbevolen* — "smallest possible" ontwapent de fidelity-reflex vóórdat hij vuurt: dit is opzet, geen naïviteit. Modelbouwers lezen dit als minimal working example en respecteren dat. Term staat vooraan, dus goed refereerbaar. |
| **A world model in three lines of mass balance** | Zelfde beweging, concreter, en de contrast-hook zit in het getal. Iets kwetsbaarder — zie de waarschuwing onderaan §10. |



### B — Negatie: definieer de term door wat hij níet is



| Variant | Waarom het werkt |
|---|---|
| **World models without neural networks**<br>*what our hydrological rules of thumb turned out to be* | Beste runner-up. Belooft de zaal dat ze het kunnen volgen, en zet de contraire claim meteen op tafel. Precies een software-days-belofte. |
| **A world model you can read**<br>*rules of thumb, mass balance, and the anatomy of planning* | Elegant, en "you can read" is exact het auditeerbaarheidsargument uit §6. |



### C — Onthulling: maak de term een uitspraak over de zaal zelf



| Variant | Waarom het werkt |
|---|---|
| **The world model we didn't know we had**<br>*testing hydrological rules of thumb against the concept* | Geeft de term stakes zonder voorkennis: het gaat over ons, niet over de definitie. "didn't know we had" dekt ook de eerlijke uitkomst (bijna). |
| **You probably have half a world model**<br>*and the missing half is not machine learning* | Meest provocatief. Spreekt de zaal direct aan en is letterlijk de conclusie van §4. Riskanter, maar memorabel. |



### D — Brug: leen geloofwaardigheid van het bekende domein



| Variant | Waarom het werkt |
|---|---|
| **From robots to polders: world models in hydrology** | ✅ **GEKOZEN** — leest als het reizen van een concept van het ene domein naar het andere; het onderwerp is de overdracht, niet de modelkwaliteit. Het meervoud *polders* helpt daarbij: het duidt een domein aan, niet ons specifieke model. Concreet, warm, en direct begrijpelijk voor deze zaal. |
| **From prediction to planning: world models in hydrology** | Neutrale variant. Benoemt exact de as uit §1b, maar mist het concrete beeld. |
| **World models: what your model is missing (and it isn't resolution)** | Scherpst voor déze zaal, adresseert de wrijving frontaal. Bewaard als reserve — confronterend in de titel. |



### Vervallen



| Variant | Reden |
|---|---|
| ~~The smallest possible world model~~ | ontwapent de fidelity-reflex het best, maar minder concreet dan de gekozen titel |
| ~~A world model for a polder~~ | enkelvoud maakt óns model het onderwerp; het meervoud in de gekozen titel niet |
| ~~Is a rule of thumb a world model?~~ | vereist voorkennis van de term |
| ~~What if I do this?~~ | term ontbreekt in de titel |
| The concepts of world models applied in hydrology, starting with the basics | correct en veilig, maar beschrijvend en zonder spanning |



---



## 10b. Gevolg van de titelkeuze: slide 2 moet het werk doen



De gekozen titel is een brug-titel, geen ontwapenende titel. Hij doet dus **niets**
tegen de fidelity-reflex uit §1b — dat werk verschuift volledig naar de deck. Twee
dingen zijn daarmee niet langer optioneel:



1. **Slide 2 moet de bewuste-minimalisatie expliciet maken.** Niet als
   verdediging halverwege, maar als aankondiging vooraan: *dit is geen claim over
   hydrologie, dit is een claim over structuur; we nemen bewust het kleinste
   systeem dat alle onderdelen heeft.* Dat is wat de titel niet meer zegt.
2. **De zes `input ∆Q → output ∆H`-slides moeten naar één.** Zolang die er zes
   zijn met concrete uitkomsten erin, is het fidelity-doelwit gewoon aanwezig in
   de deck. Eén slide die het interface toont, niet de uitkomsten.



Met de vorige titelkeuze waren dit verbeteringen. Met deze titelkeuze zijn het
voorwaarden.



> ✅ **Opgelost.** De waarschuwing hier was dat `compute_drainage1_mtr` een
> hardgecodeerd 24-uursblokkenschema met vaste indices was, en dat iemand in deze zaal
> dat zou opvragen. Dat schema is vervangen door één convolutie:
> `np.convolve(daily, np.ones(1 + dT) / (1 + dT))`. Massaconserverend per constructie, en
> bij dT = 2 identiek aan het oude schema. Ook de waterbalans zelf is nu drie regels: de
> recursie `h[t] = max(h[t-1] + d[t], 0)` is exact gelijk aan
> `S - minimum.accumulate(S)` met `S = cumsum(d)`.
>
> Het antwoord op de vraag is dus geen anticlimax meer maar het sterkste stuk van de
> talk: de vertraging is massaconserverend per constructie, en dat is aan één regel te
> zien.



---



## 11. Nog te checken / besluiten



### Openstaand



- **Datum, abstract-deadline, slotlengte en trackindeling van de editie 2026.**
  Navraag bij Nicole loopt. Vorige editie was 18 nov 2025, dus vermoedelijk ~nov 2026.
- **Abstract-limiet in woorden.** §2 is ~230; makkelijk naar 150 te trimmen door de
  derde alinea in te korten.
- **Prijslijst.** Drie posten nodig (§5). Hebben we defensibele bedragen, of maken we ze
  expliciet fictief? Fictief mag, als je het zegt.
- **Twee vervolgvragen aan Ton** in `PLAN_TOOLS_REFACTOR.md` §7. Zijn eerste ronde
  antwoorden is verwerkt en leverde een echte modelwijziging op: de waterstandverandering
  is de neerslag die direct op het open water valt plús het water dat op het land tot
  afvoer komt, en die eerste term ontbrak. Dat is bij 3,5 % open water 10,3 cm waard.
  Bruikbaar op een slide, want het is precies een verhaal over **structuur in plaats van
  resolutie**: niet meer resolutie, maar een term die er hoort te staan. Open is nog of
  het neerslagverlies ook voor de neerslag op open water geldt, en of die directe term
  niet al impliciet in de neerslag-afvoerrelatie zit.
- **Een vergelijkingsgetal voor de snelheid.** Onze kant is nu gemeten: 0,015 ms per
  doorrekening. Voor de claim "orders of magnitude" is nog een geverifieerd cijfer nodig
  voor een volledige neerslag-afvoer- plus hydrodynamische run op een vergelijkbaar
  systeem. Zonder dat cijfer: "milliseconden" zeggen en de vergelijking aan de zaal laten.



### Besloten



- **Titel:** *From Robots to Polders: World Models in Hydrology* (werktitel, zie §10 D).
- **Inzenders:** Ton Botterhuis en Mattijn van Hoek.
- **Deel 2 van de demo is gebouwd**, niet gepresenteerd als voorstel. De rekenkern is
  gevalideerd tegen `TttE_v03.xlsx` tot op machineprecisie en er staan 124 tests onder.
- **Robuustheidscurve, geen zaagtand.** Klimaatdrift en de KNMI'23-veranderfactoren zijn
  buiten scope; er zit daarmee geen aanname over de toekomst in de demo.
