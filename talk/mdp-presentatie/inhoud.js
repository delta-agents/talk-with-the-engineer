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
  // De ondertitel draagt de STELLING en niet de inhoudsopgave. Dat de tuple vijf
  // leden heeft, staat al in de kopregel erboven; wat daar niet staat is waaróm
  // een robot en een polder in één talk passen.
  titel: {
    kop: "From robots to polders: world models in hydrology",
    onder: "dezelfde drie ingrediënten — een toestand, een actie, een transitie — "
           + "en bij ons is die transitie opgeschreven",
    regel: "We beginnen bij een robot van vijfentwintig centimeter.",
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
          nadruk: [0, 1, 2, 3] },

        { regel: "Bij ons gebeurt er dit als het te hard regent.",
          figuur: "topdown_bui",
          formule: "de polder van boven, tijdens een bui",
          bron: "" },
        { regel: "En dit als het te lang droog blijft.",
          figuur: "topdown_droogte",
          formule: "de polder van boven, over een groeiseizoen",
          bron: "" },

        { regel: "Daar kun je iets aan doen. Kijk van boven: land, en een strook open water.",
          figuur: "topdown_polder", formule: "dezelfde polder, van boven",
          bron: "", nadruk: [0] },
        { regel: "Vasthouden: een deel van het land laat zijn water dagen later los.",
          figuur: "topdown_polder", formule: "dezelfde polder, van boven",
          bron: "", nadruk: [0, 1] },
        { regel: "Bergen in een overloopgebied.",
          figuur: "topdown_polder", formule: "dezelfde polder, van boven",
          bron: "", nadruk: [0, 1, 2] },
        { regel: "Afvoeren: een zwaarder gemaal.",
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

        { regel: "En dat past in hetzelfde schema als de robot. Wij hebben die transitie al; de rest van deze talk gaat over wat er dan nog ontbreekt.",
          figuur: "wereldmodel_polder", nadruk: [0, 1, 2, 3],
          formule: "dezelfde tekening, andere inhoud",
          bron: "de waterbalans van de vuistregels" },
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
      formule: "welke maatregel, en hoeveel — en elke regel werkt twee kanten op",
      // Vier kolommen: heen en terug staan NAAST elkaar per maatregel, en niet
      // in aparte beats. GEEN prijzen hier - die horen bij de beloning.
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
        { regel: "Zes maatregelen, en elke maatregel raakt precies één getal uit de toestand." },
        { regel: "En elke vuistregel werkt twee kanten op: geef de maatregel en je krijgt de stand, of geef de stand die je wíl en je krijgt de maatregel.",
          figuur: "tweerichting",
          formule: "dezelfde regel, heen en terug",
          bron: "de rode ring staat om wat je niet weet",
          nadruk: [0, 1] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "E", sym: "E", zone: "tuple",
      titel: "het weer",
      formule: "getrokken uit een statistiek, niet gekozen",
      figuur: "neerslagstatistiek",
      beats: [
        // Twee beats, twee vormen. Het VERSCHIL tussen die twee is de stap: de
        // natte statistiek varieert de gebeurtenis, de droge het klimaat.
        { regel: "Het weer kiest niemand. Maar het is ook geen scenario — dit is wat we ervan weten.",
          figuur: "neerslagstatistiek",
          formule: "hoe hard het regent, en hoe vaak",
          bron: "STOWA 2019 — zomer, gebiedsneerslag, per buiduur",
          nadruk: [0, 1, 2] },
        { regel: "Droog is het de vraagkant die we kennen: het tekort over een groeiseizoen, per waterschap én per toekomst.",
          figuur: "droogtevraag",
          formule: "hoeveel neerslag er tekortkomt, en hoe vaak",
          bron: "STOWA 2025-23 — cumulatief tekort over 1 april tot 1 oktober",
          nadruk: [0] },
        // De tweede indicator, met een EIGEN as: een fractie hoort niet op een
        // millimeter-as, en een secundaire as leest niemand op een beamer.
        { regel: "En er is een tweede kant: hoeveel de rivier dan nog levert. Bij eens per honderd jaar is dat driekwart van een normaal jaar.",
          figuur: "droogteaanbod",
          formule: "en hoeveel de bron nog geeft",
          bron: "STOWA 2025-23 — minimale 7-daagse afvoer; de 45-daagse som en het aantal droge dagen zitten niet in onze data",
          nadruk: [0] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "T", sym: "T", zone: "tuple",
      titel: "de transitie",
      formule: "de polder, de maatregel en het weer geven de volgende polder",
      figuur: "wereldmodel_polder",
      bron: "een waterbalans in uurstappen, geklemd rond het streefpeil",
      beats: [
        // Beginnen vanuit HETZELFDE schema als bij ⟳, en dan de blokken
        // weghalen die er niet bij horen. Dan is te zien wat T precies is.
        { regel: "Haal alles weg wat niet bij de transitie hoort, en dit blijft over: de polder, de maatregel, het weer — en de volgende polder.",
          nadruk: [0, 2] },
        { regel: "Dit is het world model: deze vier leden, en de beloning hoort er niet bij. Die zegt niet wat er gebeurt maar wat je wíl.",
          nadruk: [0, 2] },
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
        ["vermeden jaarschade", "die hebben we niet", "en dat is het echte gat"],
      ],
      bron: "prijspeil 2024/25 — Kadaster en NVM, twee gemaalprojecten, STOWA",
      beats: [
        { regel: "Hier zit de prijs, en als bandbreedte — een enkel getal zou valse precisie zijn, want grondprijs verschilt regionaal een factor drie." },
        { regel: "En om af te wegen heb je de andere kant nodig: de schade die je per jaar vermijdt. Die hebben we niet, en zonder die kant is er geen som te maken.",
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
        { regel: "Zet de maatregelen in de tijd en het risico wordt een zaagtand. Uitstellen is goedkoper, wachten kost schade — dat is de som van Van Dantzig, 1956.",
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
    { sleutel: "U", sym: "x*", zone: "buiten",
      titel: "wat het model zegt",
      formule: "het goedkoopste pakket dat aan de eisen voldoet",
      rijen: [
        ["norm 30 cm",                  "€ 0,22 mln", "alleen een grotere pomp"],
        ["norm 20 cm",                  "€ 0,74 mln", "nog steeds alleen pompen"],
        ["norm 30 cm + voorraad 10 mm", "€ 1,85 mln", "pomp én peilopzet"],
        ["norm 30 cm + voorraad 15 mm", "€ 2,96 mln", "pomp én peilopzet"],
        ["norm 20 cm + voorraad 15 mm", "€ 6,31 mln", "pomp, peilopzet én bergen"],
      ],
      bron: "de pakketzoeker over eenendertig mixen, op de bui van acht dagen",
      beats: [
        // Eerst de frequentielijn, want dat is de vorm waarin waterveiligheid
        // een effect uitdrukt: hoogtes tegen hun overschrijdingsfrequentie. Pas
        // daarna wat het kost.
        { regel: "Genoeg methode. Wat zegt het model?",
          figuur: "frequentielijn",
          formule: "de waterstand tegen de terugkeertijd — 10 ha bergen, "
                   + "74 % vasthouden, +0,5 m³/s afvoeren, 20 cm peilopzet",
          bron: "gerekend over acht herhaaltijden uit de STOWA-statistiek",
          nadruk: [] },
        { regel: "Zonder maatregel houdt deze polder het tot een bui van eens per zeven jaar. De norm ligt daaronder.",
          figuur: "frequentielijn", formule: "de waterstand tegen de terugkeertijd",
          bron: "gerekend over acht herhaaltijden uit de STOWA-statistiek",
          nadruk: [0] },
        { regel: "En dit is peilopzet. Die maakt het overal precies twintig centimeter slechter — dat is wat hij kost.",
          figuur: "frequentielijn", formule: "de waterstand tegen de terugkeertijd",
          bron: "peilopzet koopt droogtevoorraad en betaalt met inundatiemarge",
          nadruk: [0, 1] },
        { regel: "De drie maatregelen die wél omlaag werken, duwen de lijn naar beneden — en dus naar rechts.",
          figuur: "frequentielijn", formule: "de waterstand tegen de terugkeertijd",
          bron: "gerekend over acht herhaaltijden uit de STOWA-statistiek",
          nadruk: [0, 1, 2, 3, 4] },
        { regel: "Kijk nu naar vasthouden en afvoeren. Bij eens per tien jaar schelen ze nog geen centimeter: achttien negen tegen achttien nul.",
          figuur: "frequentielijn", formule: "de waterstand tegen de terugkeertijd",
          bron: "gerekend over acht herhaaltijden uit de STOWA-statistiek",
          nadruk: [0, 3, 4] },
        { regel: "Maar rechts staat tweeëntwintig jaar tegen vierendertig. Dezelfde centimeter bij de ontwerpbui, en anderhalf keer zo veel bescherming.",
          figuur: "frequentielijn", formule: "de waterstand tegen de terugkeertijd",
          bron: "gerekend over acht herhaaltijden uit de STOWA-statistiek",
          nadruk: [0, 3, 4] },
        { regel: "Dáárom kijk je naar de hele lijn en niet naar één punt. Bergen verzadigt niet en haalt bij extreme buien juist meer in.",
          figuur: "frequentielijn", formule: "de waterstand tegen de terugkeertijd",
          bron: "gerekend over acht herhaaltijden uit de STOWA-statistiek",
          nadruk: [0, 1, 2, 3, 4] },

        // En dan pas de prijs.
        { regel: "Dan de vraag die daarachter zit: wat kost een centimeter?",
          figuur: "maatregelcurves",
          formule: "de piek tegen wat de maatregel kost",
          bron: "gerekend op de referentiepolder, bui van acht dagen, T=10",
          nadruk: [] },
        { regel: "Afvoeren haalt de norm voor twee ton, en gaat daarna door tot nul.",
          figuur: "maatregelcurves", formule: "de piek tegen wat de maatregel kost",
          bron: "gerekend op de referentiepolder, bui van acht dagen, T=10",
          nadruk: [0] },
        { regel: "Bergen koopt dezelfde centimeters, maar zes keer zo duur: pas bij 1,35 miljoen zit hij onder de norm.",
          figuur: "maatregelcurves", formule: "de piek tegen wat de maatregel kost",
          bron: "gerekend op de referentiepolder, bui van acht dagen, T=10",
          nadruk: [0, 1] },
        { regel: "Vasthouden haalt hem voor vier ton, maar dan stuit het op een bodem van negentien centimeter.",
          figuur: "maatregelcurves", formule: "de piek tegen wat de maatregel kost",
          bron: "gerekend op de referentiepolder, bui van acht dagen, T=10",
          nadruk: [0, 1, 2] },
        { regel: "En voorbij die bodem maakt meer geld het sléchter: de vertraagde afvoer van het ene deel valt samen met de piek van het andere.",
          figuur: "maatregelcurves", formule: "de piek tegen wat de maatregel kost",
          bron: "gerekend op de referentiepolder, bui van acht dagen, T=10",
          nadruk: [0, 1, 2] },

        // Van de vorm naar het antwoord: wat kost een eis?
        { regel: "Vraag nu om het goedkoopste pakket dat onder de norm blijft, en het antwoord is: een grotere pomp. Twee ton.",
          toon: 1 },
        { regel: "Scherp de norm aan naar twintig centimeter en het blijft pompen. Zeven ton.",
          toon: 2 },
        { regel: "Maar zet er een droogte-eis bij, en er verschijnt een tweede maatregel — en de rekening gaat maal acht.",
          toon: 3, nadruk: [2] },
        { regel: "Scherp beide aan en er komt een derde bij. Dát is wat een pakket iets anders maakt dan een optelsom.",
          toon: 5, nadruk: [4] },
        { regel: "En let op: peilopzet zit in die pakketten zonder prijs. Die bedragen zijn dus te laag.",
          toon: 5, nadruk: [2, 3, 4] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "pi", sym: "π", zone: "buiten",
      titel: "wie kiest de maatregel",
      formule: "voor elke toestand een maatregel",
      figuur: "keuze",
      bron: "de zoeker draait; de policy bestaat nog niet",
      beats: [
        { regel: "De tuple is compleet. Dan blijft er één vraag over: wie kiest de maatregel?", nadruk: [] },
        { regel: "De zoeker zoekt ín het model en geeft een punt terug: eenendertig combinaties, elk exact opgelost.", nadruk: [0] },
        { regel: "Navolgbaar, en op elke machine hetzelfde getal.", nadruk: [0] },
        { regel: "Een policy wordt getraind ín het model en geeft een functie terug.", nadruk: [0, 1] },
        { regel: "Voor elke polder een maatregel — ook voor een polder die niemand heeft doorgerekend.", nadruk: [0, 1] },
        { regel: "Bij één bui en vijf getallen is dat punt genoeg. Bij vijfenzeventig jaar en getrokken klimaat bestaat het niet meer.", nadruk: [0, 1] },
        { regel: "En omdat de zoeker exact is, kun je de policy erop toetsen: op één jaar moeten ze hetzelfde zeggen.", nadruk: [0, 1, 2] },
      ] },

  ],
};
