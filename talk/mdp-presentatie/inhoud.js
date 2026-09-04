// ═══════════════════════════════════════════════════════════════════════════
// De inhoud. Dit is het enige bestand dat je normaal aanraakt.
// ═══════════════════════════════════════════════════════════════════════════
//
// Een stap is een lid van de kop, en hij draagt zijn eigen beats:
//
//   {
//     sleutel : "E"            uniek; komt in de URL-hash
//     sym     : "E"            wat er in de kop staat
//     zone    : "tuple"        "tuple" staat binnen de haken, "buiten" erbuiten
//     titel   : "het weer"     naast het symbool op het toneel
//     formule : "…"            de regel eronder, in woorden
//     rijen   : [[label, waarde, uitleg], …]
//     figuur  : "transitie"    in plaats van rijen; zie FIGUREN in presentatie.js
//     bron    : "…"            klein, onderaan het toneel
//     beats   : [{ regel, toon, nadruk }]
//   }
//
// Per beat:
//   regel    de ene zin die de presentator zegt. Groot, onderin. Eén zin.
//   toon     hoeveel rijen zichtbaar zijn (weglaten = alle, 0 = alle gedempt)
//   nadruk   welke rijen of figuurdelen oplichten, 0-geïndexeerd
//   figuur   overschrijft de figuur van de stap; zo wisselt één stap van vulling
//   video    een videobestand naast deze pagina, in plaats van de figuur. Het
//            element blijft hetzelfde zolang de bron gelijk is, dus twee beats
//            over hetzelfde fragment laten het doorlopen in plaats van herstarten
//   formule  overschrijft de regel onder de titel
//   bron     overschrijft de bronregel; "" laat hem weg
//
// Twee regels voor de inhoud, en ze zijn beide hard:
//
//   1. Elke beat staat stil goed. Bevroren op een beamer is het beeld het
//      argument, dus zet niets achter een muisbeweging.
//   2. Geen veldnamen, functienamen of bestandspaden. `area_ha` is een naam uit
//      de code; op een scherm heet dat "oppervlak". De zaal leest geen repo.

var INHOUD = {
  label: "M =",
  open: "⟨",
  sluit: "⟩",

  // De titelbeat: dit staat er zolang geen enkele stap open is (Esc, of begin).
  //
  // De kop is de titel van de talk en staat daarom in het Engels; de rest van
  // het scherm is Nederlands. Dat is geen slordigheid maar een eigennaam.
  //
  // Alleen de kop, en de voet zegt waar we beginnen. De stelling stond hier
  // eerst als ondertitel, maar op een titelscherm is dat een tweede bewering
  // naast een titel die het al doet.
  titel: {
    kop: "From robots to polders: world models in hydrology",
    regel: "We beginnen bij een mini-eendrobot van vijfentwintig centimeter.",
  },

  stappen: [

    // ───────────────────────────────────────────────────────────────────────
    // De brug van de titel: van robots naar polders. Eén schema, eerst gevuld
    // voor de microduck en dan voor de polder — de tekening blijft staan en
    // alleen de vulling wisselt. Zie `wereldmodel` in presentatie.js.
    //
    // De stap opent met het filmpje van de microduck. Dat bestand staat NAAST
    // deze pagina en niet op YouTube: geen netwerk is hier een eis, en een
    // embed is precies wat er in een zaal zonder wifi stukgaat.
    { sleutel: "W", sym: "⟳", zone: "voor",
      titel: "het schema",
      formule: "een toestand, een actie, en een transitie",
      figuur: "wereldmodel_robot",
      bron: "microduck — Pollen Robotics en Hugging Face, augustus 2026",
      beats: [
        // Eén videobeat. Twee zinnen over dezelfde clip was een zin te veel.
        { regel: "Dit is een microduck: vijfentwintig centimeter, veertien motoren. Niemand heeft die gang geprogrammeerd.",
          video: "Microduck Sim 2 Real.mp4",
          formule: "links de simulatie, rechts de vloer" },

        { regel: "Alles wat hij nodig had om dat te leren, is dit: waar hij is, wat hij kan doen, en wat er dan gebeurt.",
          nadruk: [0, 1, 2] },

        { regel: "Bij ons gebeurt er dit als het te hard regent.",
          figuur: "topdown_bui",
          formule: "de polder van boven, tijdens een bui",
          bron: "" },
        { regel: "En dit als het te lang droog blijft.",
          figuur: "topdown_droogte",
          formule: "de polder van boven, over een groeiseizoen",
          bron: "" },

        { regel: "Daar kunt u iets aan doen, en u kent ze alle drie: vasthouden op het land, bergen in een overloopgebied, afvoeren met een zwaarder gemaal.",
          figuur: "topdown_polder", formule: "dezelfde polder, van boven",
          bron: "", nadruk: [0, 1, 2, 3] },

        { regel: "Maar een polder staat niet alleen. Neem er drie.",
          figuur: "topdown_netwerk",
          formule: "dezelfde drie gebieden, twee koppelingen",
          bron: "nat is een ketting, droog is een verdeling", nadruk: [0] },
        { regel: "Nat loopt het water langs een boom naar buiten: wat A wegpompt, is de aanvoer van B.",
          figuur: "topdown_netwerk", formule: "dezelfde drie gebieden, twee koppelingen",
          bron: "nat is een ketting, droog is een verdeling", nadruk: [0, 1] },
        { regel: "Droog staan ze naast elkaar en trekken ze alle drie aan dezelfde eindige bron.",
          figuur: "topdown_netwerk", formule: "dezelfde drie gebieden, twee koppelingen",
          bron: "nat is een ketting, droog is een verdeling", nadruk: [0, 2] },

        // De twee slotbeats zetten het schema op het standpunt van de strateeg,
        // en de ringen doen het werk: eerst om het weer, dan om de maatregel.
        // Ze staan hier en niet later, want dit is de eerste beat waarop de
        // polder in het schema staat - alles daarna wordt gehoord in de stand
        // die deze twee zinnen zetten.
        { regel: "En dat past in hetzelfde schema als de robot. Alleen staat u er anders in: wat van boven komt kiest u niet, en het is niet één toekomst maar duizenden.",
          figuur: "wereldmodel_polder", nadruk: [0, 1, 2, 3],
          formule: "dezelfde tekening, andere inhoud",
          bron: "de rode ring staat om wat u niet kiest" },
        { regel: "De maatregel kiest u wél. Alleen weet u niet hoe hij uitpakt — en tussen die twee ringen valt er geen keuze te maken.",
          figuur: "wereldmodel_polder", nadruk: [0, 1, 2, 3, 4],
          formule: "dezelfde tekening, andere inhoud",
          bron: "en de tweede om wat u niet ziet aankomen" },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "S", sym: "S", zone: "tuple",
      titel: "de toestand",
      formule: "alles wat je van de polder moet weten",
      rijen: [
        ["oppervlak",         "1000", "hectare"],
        ["open water",        "5,0",  "procent van het oppervlak"],
        ["vertraagde afvoer", "0",    "procent van het land"],
        ["vertraging",        "2",    "dagen"],
        ["peilopzet",         "0",    "centimeter boven streefpeil"],
        ["peilmarge",         "0",    "centimeter eronder"],
        ["gemaal",            "1,5",  "kubieke meter per seconde"],
        ["inlaat",            "0,35", "kubieke meter per seconde"],
        ["bodemvoorraad",     "6–15", "millimeter, veen tot klei"],
        ["bodemplafond",      "0,7–2", "millimeter per dag naar het gewas"],
      ],
      bron: "de bodem komt uit de gebiedstypen; de rest is de referentiepolder",
      beats: [
        // Geen kleurmarkering: het is een overzicht en niet een argument.
        { regel: "Dit is de toestand: tien getallen, en meer heeft dit model niet nodig om een polder door te rekenen." },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "A", sym: "A", zone: "tuple",
      titel: "de maatregel",
      formule: "welke maatregel, hoeveel, en in welke eenheid",
      // Deze stap is de INTERFACE: welke knoppen er zijn, in welke eenheid, en
      // dat elke knop twee ingangen heeft. Die twee ingangen staan als derde en
      // vierde kolom NAAST elkaar per maatregel, en niet in aparte beats.
      //
      // Dat de transitie zelf omkeerbaar IS, is een uitspraak over het model en
      // die staat bij T. Hier alleen de knoppen; dezelfde claim op twee plekken
      // verzwakt beide. GEEN prijzen hier - die horen bij de beloning.
      rijen: [
        ["vasthouden", "hectare land",    "→ hoeveel lager de piek", "← hoeveel hectare"],
        ["bergen",     "hectare water",   "→ hoeveel lager de piek", "← hoeveel hectare"],
        ["afvoeren",   "m³/s gemaal",     "→ hoeveel lager de piek", "← hoeveel capaciteit"],
        ["aanvoeren",  "m³/s inlaat",     "→ hoeveel tekort blijft", "← hoeveel capaciteit"],
        ["peilopzet",  "centimeter",      "→ hoeveel voorraad",      "← hoeveel opzet"],
        ["peilmarge",  "centimeter",      "→ hoeveel lager de piek", "← hoeveel marge"],
      ],
      bron: "→ geef de maatregel · ← geef de gewenste stand",
      beats: [
        { regel: "Zes maatregelen, elk in zijn eigen eenheid, en elke maatregel raakt precies één getal uit de toestand." },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "E", sym: "E", zone: "tuple",
      titel: "het weer",
      formule: "getrokken uit een statistiek, niet gekozen",
      figuur: "neerslagstatistiek",
      beats: [
        // Twee beats. Nat: de familie per buiduur, wat seizoen en regime doen,
        // en de trekking als reeks ONDER de grafiek. Droog: vraag en aanbod
        // gestapeld, want twee eenheden horen niet op één as.
        { regel: "Het weer kiest niemand. Maar het is ook geen scenario — dit is wat we ervan weten.",
          figuur: "neerslagstatistiek",
          formule: "hoe hard het regent, en hoe vaak",
          bron: "STOWA 2019 — zomer, gebiedsneerslag, per buiduur",
          nadruk: [0, 1, 2] },
        { regel: "En droog weten we twee dingen: hoeveel er tekortkomt, en hoeveel de rivier dan nog levert.",
          figuur: "droogtestatistiek",
          formule: "de vraag en het aanbod, op dezelfde herhaaltijd",
          bron: "STOWA 2025-23 — de 45-daagse som en het aantal droge dagen zitten niet in onze data",
          nadruk: [0, 1] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "T", sym: "T", zone: "tuple",
      titel: "de transitie",
      formule: "de polder, de maatregel en het weer geven de volgende polder",
      figuur: "wereldmodel_polder_hard",
      bron: "een waterbalans in uurstappen, geklemd rond het streefpeil",
      beats: [
        // Hetzelfde schema als bij ⟳, maar wat er niet bij hoort is hier wég en
        // niet gedempt. Op de beat die zegt "dit hoort er níet bij" is half
        // zichtbaar het verkeerde antwoord.
        { regel: "Dit is het world model — deze vier leden. De maatregel en het weer gaan erin, de volgende polder komt eruit.",
          nadruk: [0] },

        // En dan de tweede uitspraak over dezelfde afbeelding: hij is naar de
        // maatregel op te lossen. Dat kan omdat de transitie deterministisch is
        // en het weer er los van staat - uit een overgangskans valt geen
        // maatregel te halen, alleen een verdeling om over te integreren.
        //
        // De term is de inverse ONTWERPvraag en niet inverse kinematics: dat
        // laatste gaat over gewrichtshoeken en het woord ontwerp zit er niet in,
        // terwijl dat het enige is waar de strateeg iets aan heeft. Zo staat hij
        // ook in `solve.py` en `read_me.py`.
        //
        // Dat de omkering meer dan één antwoord heeft, wordt bij x* de reden dat
        // het antwoord een band is. Hier alleen de vooruitwijzing.
        { regel: "En daar helpt deze transitie, want hij is ook achterstevoren te lezen: niet wat doet deze maatregel, maar welke maatregel haalt dít. Dat is de inverse ontwerpvraag, en bij ons is hij exact op te lossen.",
          figuur: "tweerichting",
          formule: "dezelfde transitie, een andere onbekende",
          bron: "de rode ring staat om wat je niet weet",
          nadruk: [0, 1] },


        // En de vraag die bij dit publiek als eerste komt. Niet "wij zijn beter"
        // maar: er ligt iets anders vast, en daarom kun je iets anders vragen.
        { regel: "En waarom dan niet een model dat het watersysteem laat draaien? Omdat daar de polder vastligt en het water beweegt — bij ons is het omgekeerd, en dat is precies wat een ontwerpvraag nodig heeft.",
          figuur: "ribasim",
          formule: "wat vastligt, en wat beweegt",
          bron: "",
          nadruk: [0, 1, 2, 3] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "R", sym: "R", zone: "tuple",
      titel: "de beloning",
      formule: "wat een pad beter maakt dan een ander",
      // De prijzen staan hier en niet bij de actie, en ze staan als RANGE: de
      // rekenkern draagt low/typical/high en een enkel getal zou valse
      // precisie zijn.
      rijen: [
        ["vasthouden",        "€ 1.250 – 3.000",  "per hectare land"],
        ["bergen",            "€ 120 – 230 dzd",  "per hectare open water"],
        ["afvoeren",          "€ 1,86 – 2,04 mln", "per kubieke meter per seconde"],
        ["aanvoeren",         "geen prijs",       "kost verdringing"],
        ["peilopzet",         "geen prijs",       "kost drooglegging"],
        ["vermeden jaarschade", "nog invullen", "per jaar, in euro" + "\u2019s"],
      ],
      bron: "prijspeil 2024/25 — Kadaster en NVM, twee gemaalprojecten, STOWA",
      beats: [
        { regel: "Hier zit de prijs, en als bandbreedte — een enkel getal zou valse precisie zijn, want grondprijs verschilt regionaal een factor drie." },
        { regel: "En om af te wegen heb je de andere kant nodig: de schade die je per jaar vermijdt. Die moet nog ingevuld worden.",
          nadruk: [5] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "g", sym: "γ", zone: "buiten",
      titel: "de tijd",
      formule: "wanneer je bouwt, niet alleen wat",
      figuur: "zaagtand",
      bron: "de vorm is het punt; de discontovoet ligt nog niet vast",
      beats: [
        // Eén beat, alles op volle opacity, en twee zinnen die de VIER punten
        // dragen: de zaagtand, disconteren duwt naar later, wachten kost
        // schade, en wie die som als eerste maakte.
        { regel: "Zet de maatregelen in de tijd en het risico wordt een zaagtand. Uitstellen is goedkoper, maar wachten kost schade.",
          nadruk: [0, 1, 2] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // De uitkomsten. De rest van de deck legt de METHODE uit; hier staat wat
    // het model zégt, en dat is het enige waarvoor je zo'n model bouwt.
    //
    // De stap draagt de pakkettabel als rijen, en de eerste beats zetten met
    // `figuur` de responsecurven ervoor. Zo hoeven het niet twee stappen te
    // zijn voor één antwoord in twee helften: eerst de vorm van elke maatregel,
    // dan wat een eis kost.
    // De uitkomsten. De rest van de deck legt de METHODE uit; hier staat wat
    // het model zégt. Van boven naar onder opgebouwd: eerst waarmee gerekend
    // wordt, dan de losse runs, dan de lijn, dan de maatregelen erin.
    { sleutel: "U", sym: "x*", zone: "buiten",
      titel: "wat het model zegt",
      formule: "de waterstand tegen de terugkeertijd",
      figuur: "frequentielijn",
      bron: "acht herhaaltijden uit de STOWA-statistiek, op de referentiepolder van duizend hectare",
      beats: [
        { regel: "Genoeg methode. Dit is de polder waarmee we rekenen.",
          nadruk: [0] },
        { regel: "We rekenen hem acht keer door: één keer per herhaaltijd, van eens per jaar tot eens per eeuw.",
          nadruk: [0, 1] },
        { regel: "Zet die acht punten naast elkaar en je hebt een frequentielijn. Zonder maatregel houdt deze polder het tot eens per zeven jaar.",
          nadruk: [0, 1, 2] },
        // Elke maatregel staat ALLEEN, niet gestapeld: de lijnen blijven om te
        // vergelijken, maar op de plaat staat er precies één, met zijn maat
        // eronder. Anders lijkt de derde beat een pakket van drie.
        { regel: "Nu elk apart. Bergen: tien hectare land wordt open water, vijf procent wordt zes. Dat duwt de lijn omlaag, en dus naar rechts: eens per tien jaar.",
          bron: "afvoer over twee dagen; met vier dagen schuift elke terugkeertijd mee — welke maatregel wint verandert niet, de getallen wel",
          nadruk: [0, 2, 3, 6] },
        { regel: "Vasthouden, ook alleen: driekwart van het land houdt zijn water dagen vast. Tweeëntwintig jaar.",
          bron: "afvoer over twee dagen; met vier dagen schuift elke terugkeertijd mee — welke maatregel wint verandert niet, de getallen wel",
          nadruk: [0, 2, 3, 4, 7] },
        { regel: "En afvoeren, een halve kuub erbij: vierendertig. Dat scheelt met vasthouden geen centimeter bij de ontwerpbui, en twaalf jaar rechts.",
          bron: "afvoer over twee dagen; met vier dagen schuift elke terugkeertijd mee — welke maatregel wint verandert niet, de getallen wel",
          nadruk: [0, 2, 3, 4, 5, 8] },

        // En dan de prijs, in de vorm die de literatuur gebruikt.
        { regel: "Dan de andere vraag: wat kost een eis? De as begint links bij de zesendertig centimeter van de kale lijn — niets doen — en loopt naar rechts naar strenger.",
          figuur: "kostencurve",
          formule: "de investering tegen het beschermingsniveau",
          bron: "de pakketzoeker over eenendertig mixen, per eis opnieuw",
          nadruk: [0] },
        { regel: "De norm van nu kost twee ton voor deze polder van duizend hectare. Tien centimeter strenger kost er zeven — de curve loopt steiler dan lineair.",
          figuur: "kostencurve",
          formule: "de investering tegen het beschermingsniveau",
          bron: "de pakketzoeker over eenendertig mixen, per eis opnieuw",
          nadruk: [0, 1] },
        // Waar je stopt en waarom dat geen punt is, staan op een beat: het is een
        // gedachte. De som heeft een andere helft nodig, en de bodem van die som
        // is vlak - dat is precies waarom we alternatieven genereren in plaats
        // van optimaliseren.
        { regel: "Maar waar stop je? Daarvoor heb je de andere curve nodig, de schade die je vermijdt — en de bodem van die som is vlak, dus het antwoord is een band en geen punt.",
          figuur: "kostencurve",
          formule: "en waarom het antwoord een band is",
          bron: "Van Dantzig 1956 en Eijgenraam tellen die twee op; waar de band precies ligt weten wij niet",
          nadruk: [0, 1, 2, 3] },

        // De opmaat naar de live demo: de vraag staat op het scherm, en dan gaat
        // het beeld naar de agent zelf. Komt de demo niet, dan staat deze beat
        // stil ook goed - de vraag en het antwoord zijn er allebei.
        { regel: "Tot nu toe koos ík de maatregel. Nu omgekeerd: achttien centimeter, en laat hem zelf zoeken.",
          figuur: "pakketvraag",
          formule: "één eis, eenendertig mixen",
          bron: "de pakketzoeker, live",
          nadruk: [0] },
        { regel: "Dit komt eruit, met een band eromheen. En binnen die band werkt ook een heel ander pakket — dus geeft hij de verzameling terug en niet één punt.",
          figuur: "pakketvraag",
          formule: "en wat er terugkomt",
          bron: "",
          nadruk: [0, 1, 2] },

        // En dan de andere kant op, want daar zaten we op te wachten: dezelfde
        // eis, een andere bedreiging. Dit is de beat waar de twee ringen van W
        // hun antwoord krijgen - je kunt de bui niet kiezen, maar je kunt hem
        // wel allemaal langslopen, en dan blijkt de ene maatregel te staan waar
        // de andere komt en gaat. Dat is de volgorde waar een strateeg om vraagt.
        { regel: "En nu de andere kant op: dezelfde eis, een zwaardere bui. Bij eens per vijfentwintig jaar valt het vasthouden eruit, bij eens per eeuw staat het er groter bij.",
          figuur: "pakketvraag",
          formule: "dezelfde eis, een andere bedreiging",
          bron: "python3 scripts/gen_voorkeursvolgorde.py",
          nadruk: [0, 1, 3] },
        { regel: "Leg die eis langs alles wat de statistiek kan trekken en er komt een voorkeur uit: het gemaal staat in vrijwel elk antwoord, vasthouden in twee van de drie.",
          figuur: "pakketvraag",
          formule: "en de voorkeur die eruit komt",
          bron: "312 bedreigingen — elke terugkeertijd, elk buiduur, beide seizoenen, elk regime",
          nadruk: [0, 1, 4] },

        // En dan de grenzen, op één plaat. Ze staan alle acht ergens in de repo
        // als caveat of open punt; bij elkaar zijn ze een uitspraak in plaats van
        // een verzameling voetnoten.
        { regel: "Waar houdt dit? Welke maatregel vóór welke gaat, wat een pakket kost met zijn band, en één polder exact — duizenden keren achter elkaar.",
          figuur: "grenzen",
          formule: "wat dit model kan, en wat niet",
          bron: "",
          nadruk: [0] },
        { regel: "En waar breekt het? Een knoop is oppervlak en geen kaart, peil en aanvoer hebben geen prijs, en de vermeden schade ontbreekt nog.",
          figuur: "grenzen",
          formule: "wat dit model kan, en wat niet",
          bron: "een simpel model is niet hetzelfde als een onschuldig model",
          nadruk: [0, 1] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    // De policy. Uitgelegd vanuit HETZELFDE schema, en precies vanaf het blok
    // dat bij T uitgegrijsd stond - dan is de vraag "wat mist er nog" een
    // plaatje in plaats van een bewering.
    //
    // En de noodzaak zit NIET in de ruimte maar in de TIJD. Generaliseren naar
    // een ongeziene polder is geen argument: de zoeker is snel genoeg om hem
    // per gebied gewoon te draaien. Wat de zoeker niet kan, is reageren op wat
    // je volgend jaar weet.
    { sleutel: "pi", sym: "π", zone: "buiten",
      titel: "wie kiest de maatregel",
      formule: "de lus die de transitie niet had",
      figuur: "wereldmodel_polder_hard",
      bron: "de zoeker draait; de policy bestaat nog niet",
      beats: [
        // Drie beats over de agent en één over het schema. De verhouding is het
        // punt: wat er vandaag kiest krijgt de ruimte, en wat er nog niet is
        // krijgt één zin. Een sectie over iets dat niet bestaat mag niet de
        // langste zijn, al helemaal niet naast de voorkeur die bij x* wél uit
        // het model komt.
        //
        // Eerst wat er wél staat. Deze stap heet "wie kiest de maatregel", en
        // in de praktijk is dat vandaag een gesprek en niet een policy.
        { regel: "Wie kiest er vandaag? In de praktijk is dat een gesprek: iemand vraagt in gewone taal om dertig centimeter minder.",
          figuur: "agent",
          formule: "wat er nu al kiest",
          bron: "de tools staan als gereedschap voor een taalmodel klaar",
          nadruk: [0] },
        { regel: "De agent kiest daar een vuistregel bij en vult hem in — en die rekent exact, op elke machine hetzelfde getal.",
          figuur: "agent",
          formule: "wat er nu al kiest",
          bron: "de tools staan als gereedschap voor een taalmodel klaar",
          nadruk: [0, 1] },
        { regel: "Het antwoord komt terug met zijn aannames erbij. En dit is de eerlijke regel: het taalmodel rekent niet, het vertaalt.",
          figuur: "agent",
          formule: "wat er nu al kiest",
          bron: "geen getal op het scherm komt uit het taalmodel",
          nadruk: [0, 1, 2, 3] },

        // En dan het schema, met het policyblok erbij. Het komt op deze beat
        // aan en stond er niet al: zo is "wat mist er nog" een plaatje in
        // plaats van een bewering.
        { regel: "En terug naar het schema: zet er een blok bij dat kiest en de lus is rond — dat is een policy. Nodig om te kiezen is ze niet; nodig om te zeggen wat u doet met wat u volgend jaar weet wél.",
          nadruk: [0, 1] },
      ] },

  ],
};
