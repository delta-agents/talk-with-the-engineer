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
//     bron    : "…"            klein, onderaan het toneel
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
      titel: "a cheap world",
      formule: "the simulation on the left, the floor on the right",
      bron: "microduck — Pollen Robotics and Hugging Face, August 2026",
      beats: [
        { regel: "This is a microduck: twenty-five centimetres, fourteen motors, and it can learn what you ask of it — kick a ball, stand up, pick something up.",
          video: "Microduck Sim 2 Real.mp4" },
        // Dezelfde clip loopt door: de tweede zin wijst naar de linkerhelft.
        { regel: "And it did not learn that on the floor. It learned it on the left: in a simulated world, where falling over costs nothing.",
          video: "Microduck Sim 2 Real.mp4" },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // Nat en droog staan onder elkaar op één plaat: een polder moet ze allebei
    // doorkomen, dus samen zijn ze de vraag. De maatregelen komen in de volgorde
    // van het waterbeleid: vasthouden, bergen, afvoeren, en dan aanvoeren.
    { sleutel: "polder", sym: "2", kop: "polder", zone: "route",
      titel: "the polder",
      formule: "one polder, seen from above",
      figuur: "topdown_polder",
      beats: [
        { regel: "Our polder has two problems, and the same polder has to get through both: too much water when it pours, too little when it stays dry for months.",
          figuur: "topdown_nat_droog",
          formule: "the same polder, wet and dry" },
        { regel: "You can do something about that, and you know the options: retain water on the land, store it in open water, discharge it with a bigger pumping station.",
          nadruk: [0, 1, 2, 3] },
        // Aanvoeren staat apart: hij komt van BUITEN de polder, en hij is de
        // enige die tegen droogte werkt.
        { regel: "And supply: let water in from outside — the only one of the four that works against drought.",
          nadruk: [0, 1, 2, 3, 4] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // Eén tekening, eerst gevuld voor de robot en dan voor de polder. De twee
    // ringen zetten het schema op het standpunt van wie moet kiezen: één om het
    // weer, één om de maatregel. De demo beantwoordt die twee ringen.
    //
    // De definitie rust op de ROL en niet op de herkomst. Dat is de ene claim
    // die tegenover een zaal vol machine learning te verdedigen is: in de AI is
    // een world model meestal geleerd, het onze is opgeschreven, en wat ze delen
    // is de vraag die je eraan stelt.
    { sleutel: "model", sym: "3", kop: "world model", zone: "route",
      titel: "the world model",
      formule: "a state, an action, and what happens next",
      figuur: "wereldmodel_robot",
      beats: [
        { regel: "Everything the microduck needs in that simulated world is this: where it is, what it can do, and what happens next. The box in the middle is its world model.",
          bron: "microduck — Pollen Robotics and Hugging Face, August 2026",
          nadruk: [0, 1, 2] },
        { regel: "Our polder fits the same drawing: a measure goes in, the weather comes from above, and the next polder comes out.",
          figuur: "wereldmodel_polder",
          formule: "the same drawing, different content",
          nadruk: [0, 2] },
        { regel: "Only: you do not choose the weather, and you do choose the measure. With thousands of possible storms, and no idea how a measure will turn out, nobody can choose between those two rings.",
          figuur: "wereldmodel_polder",
          formule: "the same drawing, different content",
          bron: "one ring around what you cannot choose, one around what you cannot foresee",
          nadruk: [0, 2, 3, 4] },
        { regel: "So what is a world model? A model you can ask: what if I do this? And that answers fast enough to try things before you do them for real.",
          figuur: "wereldmodel_rol",
          formule: "the same question, asked of a different world",
          nadruk: [0, 1, 2] },
        { regel: "In AI it is usually learned. Ours is written down — a water balance and rules of thumb — because in a polder you can write the dynamics down. The role makes it a world model, not the neural network.",
          figuur: "wereldmodel_rol",
          formule: "the same question, asked of a different world",
          nadruk: [0, 1, 2, 3] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // Het schema met een UITGEREKEND voorbeeld erin, en de kromme eronder laat
    // zien waar dat getal vandaan komt. Dezelfde kromme wordt twee kanten op
    // gelezen: dat kan omdat de transitie deterministisch is en het weer er los
    // van staat.
    { sleutel: "T", sym: "4", kop: "both ways", zone: "route",
      titel: "the transition",
      formule: "the polder, the measure and the weather give the next polder",
      figuur: "transitie_heen",
      beats: [
        { regel: "This is ours at work: measure and weather in, the next polder out. Forty hectares of extra open water bring the peak down by sixteen centimetres." },
        { regel: "And it reads backwards too: which measure gets me this? Staying below the standard takes exactly ten hectares — calculated, not searched.",
          figuur: "transitie_terug",
          titel: "the inverse",
          formule: "the inverse design question: the same curve, a different unknown" },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // De vraag die bij dit publiek als eerste komt. Het antwoord is een
    // VOLGORDE en geen wedstrijd: er ligt iets anders vast, dus je kunt iets
    // anders vragen, en het grove model gaat vóór het fijne.
    { sleutel: "detail", sym: "5", kop: "detail models", zone: "route",
      titel: "next to the detailed models",
      formule: "what is fixed, and what moves",
      figuur: "ribasim",
      beats: [
        { regel: "So why not simply run Ribasim? Because there the polder is fixed and the water moves. With us the storm is fixed and the polder moves — and that is the question design asks.",
          nadruk: [0, 1, 2, 3] },
        { regel: "It does not replace the detailed models, it goes first. Before you brute-force, you need to be on the right side of the moon: sweep wide in coarse steps, find where the workable packages are, and let the detailed model do its work there.",
          figuur: "grof_fijn",
          formule: "coarse first, then fine",
          nadruk: [0, 1] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // De agent staat VOOR het model en niet erin: hij vertaalt, de vuistregels
    // rekenen. De derde beat zegt wat dat in het werk verandert, op de sterkte
    // die te verdedigen is: de rol waarvoor het ontworpen is, niet een gemeten
    // resultaat.
    { sleutel: "agent", sym: "6", kop: "agent", zone: "route",
      titel: "the agent",
      formule: "what the agent does, and what it does not",
      figuur: "agent",
      bron: "the rules of thumb are tools for a language model",
      beats: [
        { regel: "And where is the agent? In front. Someone asks, in plain language: thirty centimetres lower — how?",
          nadruk: [0] },
        { regel: "The agent picks a rule of thumb, fills it in, and reads the answer back with its assumptions. And this is the honest rule: the language model does not calculate, it translates.",
          bron: "no number on the screen comes from the language model",
          nadruk: [0, 1, 2, 3] },
        { regel: "That changes who does what. Whoever has the question walks back and forth themselves, and the hydrologist gets the question once it is sharp. We do not replace the expert — we use the expert better.",
          figuur: "werkwijze",
          titel: "the agent in the workflow",
          formule: "who explores, and who decides",
          bron: "the role it is designed for — not yet evaluated in practice",
          nadruk: [0, 1] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // De opmaat en de nazit van de live demo. De vraag staat op het scherm en
    // dan gaat het beeld naar de agent zelf; komt de demo niet, dan staat elke
    // beat stil ook goed.
    //
    // Eerst één bui en een pakket met een band. Dan de andere kant op: dezelfde
    // eis langs alle buien, en dan blijkt de ene maatregel te staan waar de
    // andere komt en gaat. Dat is de ordening waar de twee ringen om vroegen.
    { sleutel: "demo", sym: "7", kop: "demo", zone: "route",
      titel: "the demo",
      formule: "one requirement, thirty-one mixes",
      figuur: "pakketvraag",
      bron: "the package finder, live",
      beats: [
        { regel: "Now let it search. One requirement: keep the peak below eighteen centimetres, on a polder of a thousand hectares.",
          nadruk: [0] },
        { regel: "This comes back, with a band around it. And inside that band a very different package works too — so it returns the set, not a single point.",
          formule: "and what comes back",
          bron: "",
          nadruk: [0, 1, 2] },
        { regel: "Now the other way: the same requirement, a heavier storm. At once in twenty-five years retention drops out; at once a century it is back, and larger.",
          formule: "the same requirement, a different threat",
          bron: "",
          nadruk: [0, 1, 3] },
        { regel: "Run that requirement past everything the statistics can draw and a preference appears: the pumping station is in nearly every answer, retention in two out of three.",
          formule: "and the preference that comes out",
          bron: "312 threats — every return period, every duration, both seasons, every regime",
          nadruk: [0, 1, 4] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // De grens heeft in de robotica een naam, en de drie polders meten hem: elk
    // antwoord ligt naast een gepubliceerde rapportconclusie. Dat het met geen
    // van de drie overeenkomt staat er zonder verzachting, met de oorzaak erbij.
    { sleutel: "limits", sym: "8", kop: "limits", zone: "route",
      titel: "where it holds",
      formule: "our floor: three polders with a published report",
      figuur: "casussen",
      beats: [
        { regel: "Every robot has a gap between simulation and floor. So we took three polders with a published study and put our answer next to it — and it matched none of the three.",
          bron: "Gnephoek 2023, Zuidplaspolder 2022, Kockengen 2014",
          nadruk: [0, 1, 2, 3] },
        { regel: "So where does it hold? Which measure comes before which, what a package costs with its band, and one polder exactly — thousands of times in a row.",
          figuur: "grenzen",
          formule: "what this model can do, and what it cannot",
          nadruk: [0] },
        { regel: "And where does it break? A node is an area and not a map, water level and supply have no price, and the avoided damage is still missing.",
          figuur: "grenzen",
          formule: "what this model can do, and what it cannot",
          bron: "a simple model is not the same as a harmless model",
          nadruk: [0, 1] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "close", sym: "9", kop: "close", zone: "route",
      titel: "to take home",
      formule: "and what happens next",
      figuur: "slot",
      bron: "open source, GPL-3 — github.com/delta-agents/talk-with-the-engineer",
      beats: [
        { regel: "A robot tries things in a cheap world before it touches the floor. A polder can have that too: walk back and forth between measure and threat, and bring in the detailed models once you know where to look.",
          nadruk: [0, 1] },
      ] },

    // ═══════════════════════════════════════════════════════════════════════
    // De reserve: wat niet in vijftien minuten past en wel een vraag uit de zaal
    // kan beantwoorden. Deze stappen staan niet in de kop.
    // ═══════════════════════════════════════════════════════════════════════

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
      bron: "the soil comes from the area types; the rest is the reference polder",
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
      bron: "→ give the measure · ← give the level you want",
      beats: [
        { regel: "Five knobs, each in its own unit, and each knob touches exactly one number of the state.",
          nadruk: [0, 1, 2, 3, 4] },
        { regel: "The sixth is not a knob but an investment: you buy control or you do not, and the level margin is what you agree on within it.",
          bron: "a system or no system is the choice; the margin is the size within it",
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
          bron: "STOWA 2019 — summer, areal rainfall, per duration",
          nadruk: [0, 1, 2] },
        { regel: "And for drought we know two things: how much falls short, and how much the river still delivers by then.",
          figuur: "droogtestatistiek",
          formule: "demand and supply, at the same return period",
          bron: "STOWA 2025-23",
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
      bron: "price level 2024/25 — Kadaster and NVM, two pumping station projects, STOWA",
      beats: [
        { regel: "This is where the price sits, and as a range — a single number would be false precision, because land prices differ by a factor of three between regions." },
        { regel: "Two of them cost no money but something else. And for control we know the shape — a system plus operation — and not the amount, so it does not take part.",
          nadruk: [3, 4, 5] },
        { regel: "And to weigh it you need the other side: the damage you avoid each year. That still has to be filled in.",
          nadruk: [6] },
      ] },

    // Het verschil tussen een ketting en een verdeling is het punt, dus staan de
    // twee koppelingen boven elkaar.
    { sleutel: "N", sym: "N", zone: "reserve",
      titel: "the network",
      formule: "the same three areas, coupled in two ways",
      figuur: "topdown_netwerk",
      bron: "wet is a chain, dry is an allocation",
      beats: [
        { regel: "A polder does not stand alone. Wet, they hang together like a chain; dry, all three draw on the same finite source." },
      ] },

    // Elke maatregel staat ALLEEN op de plaat, niet gestapeld: de lijnen blijven
    // om te vergelijken, maar het is geen pakket van drie.
    { sleutel: "F", sym: "F", zone: "reserve",
      titel: "the frequency curve",
      formule: "the water level against the return period",
      figuur: "frequentielijn",
      bron: "runoff over two days; with four days every return period shifts — which measure wins does not change, the numbers do",
      beats: [
        { regel: "This is the polder we calculate with.",
          bron: "eight return periods from the STOWA statistics, on the reference polder of a thousand hectares",
          nadruk: [0] },
        { regel: "We run it eight times: once per return period, from once a year to once a century.",
          bron: "eight return periods from the STOWA statistics, on the reference polder of a thousand hectares",
          nadruk: [0, 1] },
        { regel: "Put those eight points side by side and you have a frequency curve. Without a measure this polder holds up to once in seven years.",
          bron: "eight return periods from the STOWA statistics, on the reference polder of a thousand hectares",
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
      bron: "the package finder over thirty-one mixes, again for every requirement",
      beats: [
        { regel: "What does a requirement cost? The axis starts on the left at the thirty-six centimetres of the bare curve — doing nothing — and runs to the right towards stricter.",
          nadruk: [0] },
        { regel: "Today's standard costs two hundred thousand euros for this polder of a thousand hectares. Ten centimetres stricter costs seven — the curve is steeper than linear.",
          nadruk: [0, 1] },
        { regel: "But where do you stop? For that you need the other curve, the damage you avoid — and the bottom of that sum is flat, so the answer is a band and not a point.",
          formule: "and why the answer is a band",
          bron: "Van Dantzig 1956 and Eijgenraam add those two up; where the band lies exactly we do not know",
          nadruk: [0, 1, 2, 3] },
      ] },

    { sleutel: "g", sym: "γ", zone: "reserve",
      titel: "time",
      formule: "when you build, not only what",
      figuur: "zaagtand",
      bron: "the shape is the point; the discount rate is not fixed yet",
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
      bron: "the search runs; the policy does not exist yet",
      beats: [
        { regel: "Add a block that chooses and the loop is closed — that is a policy. You do not need it to choose; you do need it to say what you do with what you know next year.",
          nadruk: [0, 1] },
      ] },

  ],
};
