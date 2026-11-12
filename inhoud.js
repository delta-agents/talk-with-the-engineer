// ═══════════════════════════════════════════════════════════════════════════
// De inhoud. Dit is het enige bestand dat je normaal aanraakt.
// ═══════════════════════════════════════════════════════════════════════════
//
// Een stap is een deel van de route in de kop, en hij draagt zijn eigen beats:
//
//   {
//     sleutel : "demo"         uniek; komt in de URL-hash
//     sym     : "7"            het teken groot op het toneel
//     kop     : "demo"         het woord in de kop; weglaten bij een reservestap
//     zone    : "route"        "route" staat in de kop, "reserve" niet
//     titel   : "the demo"     naast het teken op het toneel
//     formule : "…"            de regel eronder, in woorden
//     rijen   : [[label, waarde, uitleg], …]
//     figuur  : "transitie"    in plaats van rijen; zie FIGUREN in figuren.js
//     bron    : "…"            klein, onderaan het toneel; alleen voor een bronvermelding
//     beats   : [{ regel, toon, nadruk }]
//   }
//
// Per beat:
//   regel    de zin die de presentator zegt. Niet op het scherm: hij zit achter
//            het knopje `notes` in de voet (hover, klik of de toets `n`).
//   toon     hoeveel rijen zichtbaar zijn (weglaten = alle, 0 = alle gedempt)
//   nadruk   welke rijen of figuurdelen oplichten, 0-geïndexeerd
//   figuur   overschrijft de figuur van de stap; zo wisselt één stap van vulling
//   video    een videobestand naast deze pagina, in plaats van de figuur. Het
//            element blijft hetzelfde zolang de bron gelijk is, dus twee beats
//            over hetzelfde fragment laten het doorlopen in plaats van herstarten
//   titel    overschrijft de titel naast het teken
//   formule  overschrijft de regel onder de titel
//   bron     overschrijft de bronregel; "" laat hem weg
//
// Drie regels voor de inhoud, en ze zijn alle drie hard:
//
//   1. Elke beat staat stil goed, zonder de gesproken zin. Bevroren op een
//      beamer is het beeld het argument, dus titel, formule en figuur moeten
//      het samen dragen.
//   2. Geen veldnamen, functienamen of bestandspaden. `area_ha` is een naam uit
//      de code; op een scherm heet dat "area". De zaal leest geen repo.
//   3. Alles wat de zaal ziet of hoort is Engels: de sessie is internationaal.
//
// De route is vijftien minuten: negen stappen, vijfentwintig beats. Wat daar
// niet in past staat erachter als reserve, met de pijltjes of de hash te
// bereiken als de zaal ernaar vraagt.

var INHOUD = {
  titel: {
    kop: "From robots to polders: world models in hydrology",
    regel: "We start with a mini duck robot, twenty-five centimetres tall.",
  },

  stappen: [

    // ───────────────────────────────────────────────────────────────────────
    // De robot leert in een goedkope wereld en gaat dan pas de vloer op. Die
    // volgorde is de brug van de hele talk: bij `detail` is het grof vóór fijn,
    // bij `limits` is de vloer een polder met een gepubliceerd rapport.
    //
    // De clip staat NAAST deze pagina en niet op YouTube: geen netwerk is hier
    // een eis, en een embed is precies wat er in een zaal zonder wifi stukgaat.
    { sleutel: "robot", sym: "1", kop: "robot", zone: "route",
      titel: "the microduck",
      formule: "trained in simulation, walking on the floor",
      beats: [
        { regel: "This is a microduck: twenty-five centimetres, fourteen motors, and it can learn what you ask of it — kick a ball, stand up, pick something up. And it did not learn that on the floor. It learned it on the left: in a simulated world, where falling over costs nothing.",
          video: "Microduck Sim 2 Real.mp4",
          bron: "microduck — Pollen Robotics and Hugging Face, August 2026" },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // Eerst één polder in een bui, en wat je daar zelf aan kunt doen. Dan staat
    // hij niet meer alleen: nat hangen de polders als een ketting aan elkaar,
    // droog delen ze één bron, en de verdringingsreeks zegt wie eerst droogvalt.
    // De maatregelen in de volgorde van het waterbeleid: vasthouden, bergen,
    // afvoeren, en aanvoeren pas bij droogte.
    { sleutel: "polder", sym: "2", kop: "polder", zone: "route",
      titel: "the polder",
      formule: "one polder, when it pours",
      figuur: "topdown_nat",
      beats: [
        { regel: "This is our polder when it pours: nine days of rain, and the pumping station cannot keep up. The water rises, the storage fills, and for a day and a half the level is above the flooding standard.",
          nadruk: [0] },
        { regel: "You know what you can do about that: retain water on the land, store it in open water, discharge it with a bigger pumping station.",
          formule: "and what you can do about it",
          nadruk: [0, 1] },
        { regel: "But a polder does not stand alone. What it pumps out, the next area has to take: wet, the polders hang together like a chain. And where it is already full downstream, a bigger pump upstream does not help.",
          figuur: "topdown_netwerk",
          formule: "wet: a chain",
          nadruk: [0] },
        { regel: "And when it stays dry for months, it turns around. Then the fourth measure counts — supply, letting water in — and all the polders draw on the same source. Who gets it is set by the priority sequence: safety and utilities first, and the rest falls dry first.",
          figuur: "topdown_netwerk",
          formule: "dry: one source, shared by priority",
          nadruk: [0, 1] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // Eén tekening, eerst gevuld voor de robot en dan voor de polder. De twee
    // ringen zetten het schema op het standpunt van wie moet kiezen: één om het
    // weer, één om de maatregel.
    //
    // De definitie rust op wat je het model VRAAGT en niet op hoe het gemaakt
    // is. Strikt genomen is het onze een simulator, en die van de microduck
    // ook; dat zegt de gesproken zin, niet de plaat.
    { sleutel: "model", sym: "3", kop: "world model", zone: "route",
      titel: "the world model",
      formule: "a state, an action, and what happens next",
      figuur: "wereldmodel_robot",
      beats: [
        { regel: "Everything the microduck needs in that simulated world is this: where it is, what it can do, and what happens next. The box in the middle is a physics engine: written down, not learned.",
          nadruk: [0, 1, 2] },
        { regel: "Our polder fits the same drawing: a measure goes in, the weather comes from above, and the next polder comes out.",
          figuur: "wereldmodel_polder",
          formule: "the same drawing, different content",
          nadruk: [0, 2] },
        { regel: "Only: you do not choose the weather, and you do choose the measure. With thousands of possible storms, and no idea how a measure will turn out, nobody can choose between those two rings.",
          figuur: "wereldmodel_polder",
          formule: "the same drawing, different content",
          nadruk: [0, 2, 3, 4] },
        { regel: "So what is a world model? A model you can ask: what if I do this? In AI that model is learned. Ours is written down, and to be exact that makes it a simulator — and the microduck has one too. What we take from robotics is the practice: make your mistakes there, where they cost nothing.",
          figuur: "wereldmodel_rol",
          formule: "a model you can ask: what if?",
          nadruk: [0, 1, 2, 3] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // Deze talk is een vervolg. De tijdlijn zegt waar hij vandaan komt, en de
    // gereedschapskist is wat er vorig jaar in deze sessie al stond: de
    // maatregelen als bouwstenen, elk in twee richtingen. Dezelfde plaat komt bij
    // het experiment terug met de telling erop.
    { sleutel: "before", sym: "4", kop: "last year", zone: "route",
      titel: "where this comes from",
      formule: "two years of Delta Agents",
      figuur: "tijdlijn",
      beats: [
        { regel: "This talk is a sequel. In this session last year we showed conversational agents in hydrology: the measures as building blocks, and for each of them the inverse question.",
          nadruk: [0, 1] },
        { regel: "These are those building blocks. Four measures, each in two directions: give the level you want and read the measure, or give the measure and read the level. With four tools for what is bigger than one measure, that makes twelve.",
          figuur: "gereedschap",
          titel: "the building blocks",
          formule: "four measures, in two directions",
          nadruk: [0] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // Wat er dit jaar bij komt: pakketten, en hoe een ingenieur ernaartoe werkt.
    // Het oppervlak is de oplossingsruimte: twee maatregelen als vlak, de piek
    // als hoogte. De beats lopen er stap voor stap overheen: één maatregel nemen
    // en kijken wat hij geeft, vragen wat er over is en welke maatregel dat nog
    // kan, en dan dezelfde stappen in een andere volgorde. Elke stap is een
    // vuistregel, heen of terug.
    //
    // De hoogtes, de lijn van de eis en de twee routes komen uit de rekenkern.
    { sleutel: "space", sym: "5", kop: "solution space", zone: "route",
      titel: "the solution space",
      formule: "two measures, and how high the water still comes",
      figuur: "oplossingsruimte",
      beats: [
        { regel: "New this year: packages. Two measures span a plane, and the height of this mesh is how high the water still comes. Brute force means computing every node — and that is for only two measures.",
          nadruk: [0, 1] },
        { regel: "An engineer does not work like that. You take one measure you can get — say, retention on the land — and a rule of thumb tells you what it gives: the peak drops, but not far enough.",
          formule: "step one: what does a measure give?",
          nadruk: [0, 2, 3] },
        { regel: "Then you ask what is left, and which measure can still do that. The inverse question sizes it — here, some extra pumping — and you stand on the line where the requirement is just met. First get to the right side of the moon; then search.",
          formule: "step two: what is left, and what can still do it?",
          nadruk: [0, 2, 3, 4] },
        { regel: "Do it again in another order, the pump first, and you land elsewhere on the same line, at another price. A few iterations narrow a whole plane down to that line, and to its cheapest stretch. That is where the detailed models and the experts come in: Ribasim and D-HYDRO, to prove the design and tune it.",
          formule: "iterate: another order, another package",
          nadruk: [0, 2, 3, 4, 5, 6] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // De agent staat VOOR het model en niet erin: hij vertaalt, de vuistregels
    // rekenen.
    { sleutel: "agent", sym: "6", kop: "agent", zone: "route",
      titel: "the agent",
      formule: "what the agent does, and what it does not",
      figuur: "agent",
      beats: [
        { regel: "And where is the agent? In front. Someone asks, in plain language: thirty centimetres lower — how?",
          nadruk: [0] },
        { regel: "The agent picks a rule of thumb, fills it in, and reads the answer back with its assumptions. The language model does not calculate, it translates — and translating is where it goes wrong.",
          nadruk: [0, 1, 2, 3] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // Er is geen live demo: het experiment is het bewijs. Gereedschap bouwen voor
    // agents is nieuw, en hoe het gebruikt wordt ontdek je door te kijken. Vier
    // beats: wat er in ging, welk gereedschap is opgepakt, hoe de agent zocht, en
    // wat eruit kwam naast het gepubliceerde antwoord.
    //
    // De derde beat is het punt: de agent rekent niet alles door, maar hij is ook
    // niet grondig. Hij neemt het eerste antwoord dat werkt.
    { sleutel: "experiment", sym: "7", kop: "experiment", zone: "route",
      titel: "the experiment",
      formule: "three polders, one agent, twelve tools",
      figuur: "experiment_opzet",
      beats: [
        { regel: "Building tools for AI agents is new, and we are still discovering how they get used. So we ran an experiment on three areas with a published study: a new district near Alphen, a new district in the Zuidplaspolder, and the flood in Kockengen in 2014. Each with the question its study answers, put to an agent with our twelve tools." },
        { regel: "Fifteen calls. Half the toolbox was never picked up: every forward tool, and the whole dry side. And the tool it used most, it used in a way we never designed — the chain of areas, four times with no chain in it, just to run variants side by side.",
          figuur: "gereedschap_gebruik",
          formule: "which tools it picked up",
          nadruk: [0, 1] },
        { regel: "And look at the pace. The first polder: the manual, then every measure, then the package, then the chain. The next two: straight to an answer, in a fraction of the time.",
          figuur: "experiment_tempo",
          formule: "how it searched",
          nadruk: [0, 1] },
        { regel: "And the answers? Next to the published study in all three, and equal to it in none: a factor of twenty, a factor of two, and one question the study itself left open.",
          figuur: "casussen",
          formule: "and what came out",
          nadruk: [0, 1, 2] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // De grens zit niet in de rekenkern maar in hoe een agent het gereedschap
    // gebruikt: tussen alles doorrekenen en het eerste antwoord dat past.
    { sleutel: "limits", sym: "8", kop: "limits", zone: "route",
      titel: "the limit is in the use",
      formule: "tools for agents are new, and so is how they get used",
      figuur: "experiment_grens",
      beats: [
        { regel: "What does that tell us? Building tools for AI agents is new; we are discovering how they get used. Today a language model picks them up in a brute-force way — misusing them, or at least using them in a way we did not design for. It is not very thorough. It settles for a solution quickly. It feels like a pupil who wants to finish the homework quickly.",
          nadruk: [0, 1] },
        { regel: "We do not want the agent to brute-force: every tool, every node. But we do not want it to rush to a sub-optimal solution either. What we want is in between — the way an engineer narrows it down: what does a measure give, what is left, and what can still do it.",
          nadruk: [0, 1, 2] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // Het slot wisselt de titel: van de vergelijking waarmee we binnenkwamen naar
    // wat we ermee willen bouwen. De nieuwe titel is concreet gemaakt met drie
    // eisen waar een antwoord aan te toetsen is.
    { sleutel: "close", sym: "9", kop: "close", zone: "route",
      titel: "what we are after",
      formule: "from a comparison to something to build",
      figuur: "titelwissel",
      beats: [
        { regel: "We came in with robots and polders. What we are working towards is validation infrastructure for strategic water management: open rules that a professional, a citizen and a machine can all check a plan against. In the KIN report we called it critical validation infrastructure; these three requirements are what makes it concrete.",
          nadruk: [0, 1] },
        { regel: "Next month, at the Digishape day, we evaluate the Delta Agents on exactly this. Two students are taking it to the drought of 2026. And it is open source — come and break it.",
          figuur: "slot",
          titel: "to take home",
          formule: "and what happens next",
          nadruk: [0, 1] },
      ] },

    // ═══════════════════════════════════════════════════════════════════════
    // De reserve: wat niet in vijftien minuten past en wel een vraag uit de zaal
    // kan beantwoorden. Deze stappen staan niet in de kop.
    // ═══════════════════════════════════════════════════════════════════════

    // De transitie met een UITGEREKEND voorbeeld erin, en de kromme eronder laat
    // zien waar dat getal vandaan komt. Dezelfde kromme wordt twee kanten op
    // gelezen.
    { sleutel: "T", sym: "T", zone: "reserve",
      titel: "the transition",
      formule: "the polder, the measure and the weather give the next polder",
      figuur: "transitie_heen",
      beats: [
        { regel: "This is ours at work: measure and weather in, the next polder out. Forty hectares of extra open water bring the peak down by sixteen centimetres." },
        { regel: "And it reads backwards too: which measure gets me this? Staying below the standard takes ten hectares — found by a short search over forward runs, cheap enough to do while you talk.",
          figuur: "transitie_terug",
          titel: "the inverse",
          formule: "the inverse design question: the same curve, a different unknown" },
      ] },

    // Waar het rekenmodel zelf ophoudt: wat het kan, en wat er nog ontbreekt.
    { sleutel: "holds", sym: "H", zone: "reserve",
      titel: "where it holds",
      formule: "what this model can do, and what it cannot",
      figuur: "grenzen",
      beats: [
        { regel: "So where does it hold? Which measure comes before which, what a package costs with its band, and one polder exactly — thousands of times in a row.",
          nadruk: [0] },
        { regel: "And where does it break? A node is an area and not a map, water level and supply have no price, and the avoided damage is still missing.",
          nadruk: [0, 1] },
      ] },

    // Wat vastligt en wat beweegt, tegenover een model dat de andere kant op
    // rekent.
    { sleutel: "ribasim", sym: "≠", zone: "reserve",
      titel: "next to the detailed models",
      formule: "what is fixed, and what moves",
      figuur: "ribasim",
      beats: [
        { regel: "Why not simply run Ribasim? There the polder is fixed and the water moves. With us the storm is fixed and the polder moves. You can ask either one backwards, as a search over forward runs; ours is cheap enough to do that while you talk.",
          nadruk: [0, 1, 2] },
      ] },

    // Wie verkent en wie beslist, zonder en met de agent ervoor.
    { sleutel: "work", sym: "W", zone: "reserve",
      titel: "the agent in the workflow",
      formule: "who explores, and who decides",
      figuur: "werkwijze",
      beats: [
        { regel: "Whoever has the question walks back and forth themselves, and the hydrologist gets the question once it is sharp. We do not replace the expert — we use the expert better. That is the role it is designed for; it has not been evaluated in practice yet.",
          nadruk: [0, 1] },
      ] },

    // Het pakket met zijn band bij één bui, en dezelfde eis langs alle buien.
    { sleutel: "package", sym: "P", zone: "reserve",
      titel: "the package finder",
      formule: "one requirement, thirty-one mixes",
      figuur: "pakketvraag",
      beats: [
        { regel: "One requirement: keep the peak below eighteen centimetres, on a polder of a thousand hectares.",
          nadruk: [0] },
        { regel: "This comes back, with a band around it. And inside that band a very different package works too — so it returns the set, not a single point.",
          formule: "and what comes back",
          nadruk: [0, 1, 2] },
        { regel: "The same requirement, a heavier storm. At once in twenty-five years retention drops out; at once a century it is back, and larger.",
          formule: "the same requirement, a different threat",
          nadruk: [0, 1, 3] },
        { regel: "Run that requirement past everything the statistics can draw and a preference appears: the pumping station is in nearly every answer, retention in two out of three.",
          formule: "and the preference that comes out",
          nadruk: [0, 1, 4] },
      ] },

    { sleutel: "S", sym: "S", zone: "reserve",
      titel: "the state",
      formule: "everything you need to know about the polder",
      // De runoff time staat hier en niet bij het weer: hoe snel neerslag tot
      // afvoer komt is een eigenschap van bodem en drainage.
      rijen: [
        ["area",            "1000",  "hectares"],
        ["open water",      "5.0",   "percent of the area"],
        ["delayed runoff",  "0",     "percent of the land"],
        ["delay",           "2",     "days"],
        ["runoff time",     "2",     "days to regional discharge"],
        ["raised level",    "0",     "centimetres above target level"],
        ["level margin",    "0",     "centimetres below it"],
        ["pumping station", "1.5",   "cubic metres per second"],
        ["inlet",           "0.35",  "cubic metres per second"],
        ["soil storage",    "6–15",  "millimetres, peat to clay"],
        ["soil ceiling",    "0.7–2", "millimetres per day to the crop"],
      ],
      beats: [
        { regel: "This is the state: eleven numbers, and the model needs no more to run a polder." },
      ] },

    // De INTERFACE: welke knoppen er zijn, in welke eenheid, en dat elke knop
    // twee ingangen heeft. Geen prijzen hier - die horen bij de beloning.
    //
    // De laatste rij is een ander soort maatregel, en de tabel zegt dat door hem
    // geen tweede pijl te geven: sturing is een systeem dat je koopt of niet, met
    // de marge als maat erbinnen.
    { sleutel: "A", sym: "A", zone: "reserve",
      titel: "the measure",
      formule: "which measure, how much, and in which unit",
      rijen: [
        ["retain",       "hectares of land",  "→ how much lower the peak", "← how many hectares"],
        ["store",        "hectares of water", "→ how much lower the peak", "← how many hectares"],
        ["discharge",    "m³/s pumping",      "→ how much lower the peak", "← how much capacity"],
        ["supply",       "m³/s inlet",        "→ how much shortage is left", "← how much capacity"],
        ["raised level", "centimetres",       "→ how much storage",        "← how much raising"],
        ["control",      "yes or no",         "→ how much lower the peak", ""],
      ],
      beats: [
        { regel: "Five knobs, each in its own unit, and each knob touches exactly one number of the state.",
          nadruk: [0, 1, 2, 3, 4] },
        { regel: "The sixth is not a knob but an investment: you buy control or you do not, and the level margin is what you agree on within it.",
          nadruk: [5] },
      ] },

    // Nat: de familie per buiduur. Droog: vraag en aanbod gestapeld, want twee
    // eenheden horen niet op één as.
    { sleutel: "E", sym: "E", zone: "reserve",
      titel: "the weather",
      formule: "drawn from statistics, not chosen",
      figuur: "neerslagstatistiek",
      beats: [
        { regel: "Nobody chooses the weather. But it is not a scenario either — this is what we know about it.",
          formule: "how hard it rains, and how often",
          nadruk: [0, 1, 2] },
        { regel: "And for drought we know two things: how much falls short, and how much the river still delivers by then.",
          figuur: "droogtestatistiek",
          formule: "demand and supply, at the same return period",
          nadruk: [0, 1] },
      ] },

    // De prijzen staan als RANGE: de rekenkern draagt laag, typisch en hoog, en
    // een enkel getal zou valse precisie zijn.
    { sleutel: "R", sym: "R", zone: "reserve",
      titel: "the reward",
      formule: "what makes one path better than another",
      rijen: [
        ["retain",       "€ 1,250 – 3,000",    "per hectare of land"],
        ["store",        "€ 120 – 230 k",      "per hectare of open water"],
        ["discharge",    "€ 1.86 – 2.04 mln",  "per cubic metre per second"],
        ["supply",       "no price",           "costs displacement of other users"],
        ["raised level", "no price",           "costs freeboard"],
        ["control",      "to be filled in",    "a fixed part plus operation"],
        ["avoided annual damage", "to be filled in", "per year, in euros"],
      ],
      beats: [
        { regel: "This is where the price sits, and as a range — a single number would be false precision, because land prices differ by a factor of three between regions." },
        { regel: "Two of them cost no money but something else. And for control we know the shape — a system plus operation — and not the amount, so it does not take part.",
          nadruk: [3, 4, 5] },
        { regel: "And to weigh it you need the other side: the damage you avoid each year. That still has to be filled in.",
          nadruk: [6] },
      ] },

    // Eén polder door een droog halfjaar: de eigen voorraad is na tien dagen op,
    // en wat daarna ontbreekt moet van buiten komen.
    { sleutel: "D", sym: "D", zone: "reserve",
      titel: "the dry polder",
      formule: "half a growing season without enough rain",
      figuur: "topdown_droog",
      beats: [
        { regel: "Dry, the same polder runs out of its own water within ten days. After that, every shortage has to come from outside — and that is a supply question for the whole region, not for one polder." },
      ] },

    // Elke maatregel staat ALLEEN op de plaat, niet gestapeld: de lijnen blijven
    // om te vergelijken, maar het is geen pakket van drie.
    { sleutel: "F", sym: "F", zone: "reserve",
      titel: "the frequency curve",
      formule: "the water level against the return period",
      figuur: "frequentielijn",
      beats: [
        { regel: "This is the polder we calculate with.",
          nadruk: [0] },
        { regel: "We run it eight times: once per return period, from once a year to once a century.",
          nadruk: [0, 1] },
        { regel: "Put those eight points side by side and you have a frequency curve. Without a measure this polder holds up to once in seven years.",
          nadruk: [0, 1, 2] },
        { regel: "Now each one on its own. Store: ten hectares of land become open water, five percent becomes six. That pushes the curve down, and so to the right: once in ten years.",
          nadruk: [0, 2, 3, 6] },
        { regel: "Retain, also on its own: three quarters of the land holds its water for days. Twenty-two years.",
          nadruk: [0, 2, 3, 4, 7] },
        { regel: "And discharge, half a cubic metre per second extra: thirty-four. Against retention that is not a centimetre at the design storm, and twelve years to the right.",
          nadruk: [0, 2, 3, 4, 5, 8] },
      ] },

    // De bodem van de som van kosten en vermeden schade is vlak: dat is waarom
    // het antwoord een band is en waarom er alternatieven uitkomen in plaats van
    // één optimum.
    { sleutel: "K", sym: "K", zone: "reserve",
      titel: "the cost curve",
      formule: "the investment against the level of protection",
      figuur: "kostencurve",
      beats: [
        { regel: "What does a requirement cost? The axis starts on the left at the thirty-six centimetres of the bare curve — doing nothing — and runs to the right towards stricter.",
          nadruk: [0] },
        { regel: "Today's standard costs two hundred thousand euros for this polder of a thousand hectares. Ten centimetres stricter costs seven — the curve is steeper than linear.",
          nadruk: [0, 1] },
        { regel: "But where do you stop? For that you need the other curve, the damage you avoid — and the bottom of that sum is flat, so the answer is a band and not a point.",
          formule: "and why the answer is a band",
          nadruk: [0, 1, 2, 3] },
      ] },

    { sleutel: "g", sym: "γ", zone: "reserve",
      titel: "time",
      formule: "when you build, not only what",
      figuur: "zaagtand",
      beats: [
        { regel: "Put the measures in time and the risk becomes a sawtooth. Postponing is cheaper, but waiting costs damage.",
          nadruk: [0, 1, 2] },
      ] },

    // De noodzaak van een policy zit in de TIJD en niet in de ruimte: de zoeker
    // is snel genoeg om hem per gebied te draaien, maar hij kan niet reageren op
    // wat je volgend jaar weet.
    { sleutel: "pi", sym: "π", zone: "reserve",
      titel: "who chooses the measure",
      formule: "the loop the transition did not have",
      figuur: "wereldmodel_polder_hard",
      beats: [
        { regel: "Add a block that chooses and the loop is closed — that is a policy. You do not need it to choose; you do need it to say what you do with what you know next year.",
          nadruk: [0, 1] },
      ] },

  ],
};
