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
          nadruk: [0, 1, 2] },

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
          bron: "", nadruk: [0, 1, 2] },

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
      figuur: "wereldmodel_polder",
      bron: "een waterbalans in uurstappen, geklemd rond het streefpeil",
      beats: [
        // Beginnen vanuit HETZELFDE schema als bij ⟳, en dan de blokken
        // weghalen die er niet bij horen. Dan is te zien wat T precies is.
        { regel: "Haal alles weg wat niet bij de transitie hoort, en dit blijft over: de maatregel en het weer gaan erin, de volgende polder komt eruit.",
          nadruk: [0] },
        { regel: "Dit is het world model — deze vier leden. De beloning hoort er niet bij: die zegt niet wat er gebeurt maar wat je wíl.",
          nadruk: [0] },
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
    // De uitkomsten. De rest van de deck legt de METHODE uit; hier staat wat
    // het model zégt. Van boven naar onder opgebouwd: eerst waarmee gerekend
    // wordt, dan de losse runs, dan de lijn, dan de maatregelen erin.
    { sleutel: "U", sym: "x*", zone: "buiten",
      titel: "wat het model zegt",
      formule: "de waterstand tegen de terugkeertijd",
      figuur: "frequentielijn",
      bron: "acht herhaaltijden uit de STOWA-statistiek, op de referentiepolder",
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
          bron: "de referentiepolder met één maatregel erop, elke keer opnieuw",
          nadruk: [0, 2, 3, 6] },
        { regel: "Vasthouden, ook alleen: driekwart van het land houdt zijn water dagen vast. Tweeëntwintig jaar.",
          bron: "de referentiepolder met één maatregel erop, elke keer opnieuw",
          nadruk: [0, 2, 3, 4, 7] },
        { regel: "En afvoeren, een halve kuub erbij: vierendertig. Dat scheelt met vasthouden geen centimeter bij de ontwerpbui, en twaalf jaar rechts.",
          bron: "de referentiepolder met één maatregel erop, elke keer opnieuw",
          nadruk: [0, 2, 3, 4, 5, 8] },

        // En dan de prijs, in de vorm die de literatuur gebruikt.
        { regel: "Dan de andere vraag: wat kost een eis? De as begint links bij de zesendertig centimeter van de kale lijn — niets doen — en loopt naar rechts naar strenger.",
          figuur: "kostencurve",
          formule: "de investering tegen het beschermingsniveau",
          bron: "de pakketzoeker over eenendertig mixen, per eis opnieuw",
          nadruk: [0] },
        { regel: "De norm van nu kost twee ton. Tien centimeter strenger kost er zeven — de curve loopt steiler dan lineair.",
          figuur: "kostencurve",
          formule: "de investering tegen het beschermingsniveau",
          bron: "de pakketzoeker over eenendertig mixen, per eis opnieuw",
          nadruk: [0, 1] },
        { regel: "Maar waar stop je? Daarvoor heb je de andere curve nodig: de schade die je ermee vermijdt.",
          figuur: "kostencurve",
          formule: "en de helft die ontbreekt",
          bron: "Van Dantzig 1956 en Eijgenraam tellen die twee op",
          nadruk: [0, 1, 2] },
        // En het antwoord is geen punt. De bodem van die som is vlak, en dat is
        // precies waarom we alternatieven genereren in plaats van optimaliseren.
        { regel: "Die som heeft geen punt maar een bodem: in een band zijn meerdere pakketten verdedigbaar. Daarom zoeken we alternatieven, geen optimum.",
          figuur: "kostencurve",
          formule: "en waarom het antwoord een band is",
          bron: "de vorm komt uit de literatuur; waar die band precies ligt weten wij niet",
          nadruk: [0, 1, 2, 3] },
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
      formule: "het blok dat bij de transitie nog leeg stond",
      figuur: "wereldmodel_polder",
      bron: "de zoeker draait; de policy bestaat nog niet",
      beats: [
        { regel: "Bij de transitie hebben we dit blok bewust leeg gelaten.",
          nadruk: [0] },
        { regel: "Nu zetten we het aan. Dit is de policy: het ding dat kiest — en de vraag van deze talk is of wij die nodig hebben.",
          nadruk: [0, 1] },
        { regel: "Want de zoeker kán al kiezen: eenendertig combinaties, exact opgelost, en op elke machine hetzelfde getal.",
          nadruk: [0, 1] },
        { regel: "Naar een ongezien gebied generaliseren is dus geen argument. Draai de zoeker daar gewoon opnieuw — hij is snel genoeg.",
          nadruk: [0, 1] },
        { regel: "Het argument zit in de tijd. De zoeker geeft een plán: bouw dit, in dat jaar.",
          nadruk: [0, 1] },
        { regel: "Maar volgend jaar weet je meer. Een nieuwe meting, een herzien klimaatscenario, een kade die het niet hield.",
          nadruk: [0, 1] },
        { regel: "Een plan zegt niet wat je met die informatie doet. Een policy is een plan dat kan antwoorden — dat is adaptief deltamanagement, in één woord.",
          nadruk: [0, 1, 2] },
        { regel: "En omdat de zoeker exact is, kun je die policy erop toetsen: op één jaar horizon moeten ze hetzelfde zeggen.",
          nadruk: [0, 1, 2] },
      ] },

  ],
};
