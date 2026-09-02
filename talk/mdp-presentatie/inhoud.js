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
  titel: {
    kop: "De polder als Markov Decision Process",
    onder: "vijf leden, een discontofactor, en dan de vraag wie de maatregel kiest",
    regel: "Dit is één object. We lopen het lid voor lid af.",
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
        // Twee beats video. Het element blijft hetzelfde zolang de bron gelijk
        // is, dus het fragment loopt door en herstart niet bij de tweede zin.
        { regel: "Dit is een microduck: vijfentwintig centimeter, veertien motoren, vierhonderd dollar.",
          video: "Microduck Sim 2 Real.mp4",
          formule: "links de simulatie, rechts de vloer" },
        { regel: "Niemand heeft die gang geprogrammeerd. Hij is geleerd — en niet rechts, maar links.",
          video: "Microduck Sim 2 Real.mp4",
          formule: "links de simulatie, rechts de vloer" },

        { regel: "Een world model is drie dingen: een toestand, een actie, en een transitie die zegt wat er daarna gebeurt.",
          nadruk: [0] },
        { regel: "En let op wat die transitie bij de microduck ís: geen neuraal netwerk, maar natuurkunde die iemand heeft opgeschreven.",
          nadruk: [0] },
        { regel: "De actie zijn veertien gewrichtsdoelen, vijftig keer per seconde. Die kiest hij zelf niet — dat doet zijn policy.",
          nadruk: [0, 1] },
        { regel: "Wat hij ook niet kiest: de vloer, de wrijving, de spanning van zijn batterij.",
          nadruk: [0, 1, 2] },
        { regel: "Dan zegt de beloning wat goed is, en PPO werkt de policy bij tot hij loopt. Twee uur op één videokaart.",
          nadruk: [0, 1, 2, 3] },

        // De tegenhanger van de clip: geen robot die loopt maar een waterbalans
        // die loopt. Dezelfde twee zetten als hierboven — eerst het ding zelf,
        // dan het schema eromheen.
        { regel: "Zo ziet onze transitie eruit als je hem laat lopen. Acht dagen regen, eens per tien jaar.",
          figuur: "topdown_bui",
          formule: "dezelfde polder, dezelfde bui, van boven",
          bron: "peil en tijd uit de rekenkern; de breedte van de overstroming is illustratief" },
        { regel: "Het gemaal draait, en toch gaat de stijging over de norm heen — en dan loopt het land onder.",
          figuur: "topdown_bui",
          formule: "dezelfde polder, dezelfde bui, van boven",
          bron: "peil en tijd uit de rekenkern; de breedte van de overstroming is illustratief" },

        // Van de doorsnede naar het gebied van boven. Hier gaat het niet meer
        // over de stand maar over wat je eraan kunt doen, en dat is ruimtelijk.
        { regel: "Vandaar dat er maatregelen bestaan. Kijk er van boven op: land, en een strook open water.",
          figuur: "topdown_polder",
          formule: "dezelfde polder, van boven",
          bron: "vier vuistregels op één gebied",
          nadruk: [0] },
        { regel: "Vasthouden: een deel van het land laat zijn water dagen later los. Niet lineair — voorbij een optimum valt het samen met de piek.",
          figuur: "topdown_polder", formule: "dezelfde polder, van boven",
          bron: "vier vuistregels op één gebied", nadruk: [0, 1] },
        { regel: "Bergen: land wórdt open water. De eerste hectares doen het meeste, daarna verzadigt het.",
          figuur: "topdown_polder", formule: "dezelfde polder, van boven",
          bron: "vier vuistregels op één gebied", nadruk: [0, 1, 2] },
        { regel: "Afvoeren: een zwaarder gemaal. Recht in effect, en recht in prijs.",
          figuur: "topdown_polder", formule: "dezelfde polder, van boven",
          bron: "vier vuistregels op één gebied", nadruk: [0, 1, 2, 3] },

        // Drie knopen, twee koppelingen. Dezelfde gebieden; alleen wat ze met
        // elkaar doet verschilt, en dáárom zijn het twee gereedschappen.
        { regel: "Maar een polder staat niet alleen. Neem er drie.",
          figuur: "topdown_netwerk",
          formule: "dezelfde drie gebieden, twee koppelingen",
          bron: "nat is een ketting, droog is een verdeling",
          nadruk: [0] },
        { regel: "Nat loopt het water langs een boom naar buiten: wat A wegpompt, is de aanvoer van B.",
          figuur: "topdown_netwerk", formule: "dezelfde drie gebieden, twee koppelingen",
          bron: "nat is een ketting, droog is een verdeling", nadruk: [0, 1] },
        { regel: "En dan is de vraag niet welk gemaal te klein is, maar welk gemaal geblokkeerd staat. Bovenstrooms bijbouwen helpt daar niet.",
          figuur: "topdown_netwerk", formule: "dezelfde drie gebieden, twee koppelingen",
          bron: "nat is een ketting, droog is een verdeling", nadruk: [0, 1] },
        { regel: "Droog is het omgekeerd: ze staan naast elkaar en trekken alle drie aan dezelfde eindige bron.",
          figuur: "topdown_netwerk", formule: "dezelfde drie gebieden, twee koppelingen",
          bron: "nat is een ketting, droog is een verdeling", nadruk: [0, 2] },
        { regel: "Geen volgorde lost dat op. Er moet verdeeld worden, en de wet zegt in welke orde dat gaat.",
          figuur: "topdown_netwerk", formule: "dezelfde drie gebieden, twee koppelingen",
          bron: "nat is een ketting, droog is een verdeling", nadruk: [0, 2] },

        // De wissel. Zelfde tekening als bij de robot, andere vulling.
        { regel: "Zet dat in hetzelfde schema.",
          figuur: "wereldmodel_polder", nadruk: [0, 1, 2, 3] },
        { regel: "Het schema blijft staan. Alleen de getallen zijn andere getallen.",
          figuur: "wereldmodel_polder", nadruk: [0, 1, 2, 3] },
        { regel: "Robotica schrijft zijn transitie dus óók op. En heeft daar de tweede stap al op gezet.",
          figuur: "wereldmodel_polder", nadruk: [0, 1, 2, 3] },
        { regel: "Wij hebben die transitie. De rest van deze talk gaat over wat er dan nog ontbreekt.",
          figuur: "wereldmodel_polder", nadruk: [0, 1, 2, 3] },
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
      ],
      bron: "de referentiepolder van de vuistregels",
      beats: [
        { regel: "Acht getallen. Meer heeft dit model niet nodig om een polder door te rekenen.",
          toon: 8 },
        { regel: "Twee ervan vormen samen de peilband: hoe hoog het streefpeil staat, en hoe diep het gemaal doormaalt.",
          nadruk: [4, 5] },
        { regel: "De toestand is onveranderlijk — een maatregel levert een nieuwe polder op en verandert deze niet." },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "A", sym: "A", zone: "tuple",
      titel: "de maatregel",
      formule: "welke maatregel, en hoeveel",
      rijen: [
        ["vasthouden", "€ 2.400",    "per hectare land"],
        ["bergen",     "€ 135.000",  "per hectare open water"],
        ["afvoeren",   "€ 1,92 mln", "per kubieke meter per seconde"],
        ["aanvoeren",  "geen prijs", "kost verdringing"],
        ["peilopzet",  "geen prijs", "kost drooglegging"],
      ],
      bron: "prijspeil 2024/25 — grondprijzen Kadaster en NVM, twee gemaalprojecten, STOWA",
      beats: [
        { regel: "Vijf maatregelen, en elke maatregel raakt precies één van die acht getallen.",
          toon: 5 },
        { regel: "Drie hebben een prijs in euro's, onderbouwd met Nederlandse projecten.",
          nadruk: [0, 1, 2] },
        { regel: "Twee hebben er geen. Dat is geen ontbrekend getal maar een andere eenheid.",
          nadruk: [3, 4] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "E", sym: "E", zone: "tuple",
      titel: "het weer",
      formule: "getrokken uit een statistiek, niet gekozen",
      rijen: [
        ["vier dagen regen, eens per tien jaar",  "59 mm",  "zomerbui over het gebied"],
        ["dezelfde bui, eens per honderd jaar",   "87 mm",  "zomerbui over het gebied"],
        ["Aa en Maas, eens per tien jaar",        "279 mm", "neerslagtekort, huidig klimaat"],
        ["diezelfde regio in 2100",               "473 mm", "droog scenario, hoge uitstoot"],
        ["Hunze en Aa's, eens per tien jaar",     "237 mm", "het laagste van de eenentwintig"],
        ["Scheldestromen, eens per tien jaar",    "291 mm", "het hoogste — 23 procent hoger"],
      ],
      bron: "STOWA 2019 voor de bui · STOWA 2025-23 voor de droogte, per waterschap en per klimaatscenario",
      beats: [
        { regel: "Het weer kiest niemand. Dit is het enige lid waar wij niet aan de knoppen zitten.",
          toon: 0 },
        { regel: "Maar het is ook geen scenario — het is een statistiek, en die hebben we voor beide kanten.",
          toon: 0 },
        { regel: "Nat: herhaaltijd, duur, seizoen en patroon. Vier dagen zomerregen, eens per tien jaar, is 59 millimeter.",
          toon: 2, nadruk: [0] },
        { regel: "Droog: het neerslagtekort over een groeiseizoen. In Aa en Maas gaat dat van 279 naar 473 millimeter.",
          toon: 4, nadruk: [2, 3] },
        { regel: "En het verschilt per regio: tussen het noorden en het zuiden zit drieëntwintig procent.",
          toon: 6, nadruk: [4, 5] },
        { regel: "Twee klokken dus: de bui duurt uren, de droogte een groeiseizoen. Eén peilband deelt ze." },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "T", sym: "T", zone: "tuple",
      titel: "de transitie",
      formule: "de polder, de maatregel en het weer geven de volgende polder",
      figuur: "transitie",
      bron: "een waterbalans in uurstappen, geklemd rond het streefpeil",
      beats: [
        { regel: "Een maatregel geeft een nieuwe polder: hetzelfde type eruit als erin.", nadruk: [0] },
        { regel: "Dáárom kun je hem herhalen. Dat is het verschil tussen een voorspelling en een wereld.", nadruk: [0] },
        { regel: "De waterbalans rekent de bui in uurstappen door, en snel genoeg om duizenden werelden af te tasten.", nadruk: [0, 1] },
        { regel: "De klem ís het peilbeheer: het gemaal stopt op streefpeil, de inlaat ook. Eén routine, klem gespiegeld.", nadruk: [0, 1] },
        // De doorsnede hoort hier: dit is de enige stap waar de peilband zelf
        // het argument is, en van boven is een band niet te zien.
        { regel: "In doorsnede is dat deze band. Omhoog is wateroverlast, omlaag watertekort, en het is één meter.",
          figuur: "polder_animatie",
          formule: "de peilband, met dezelfde bui erop",
          bron: "de standen komen uit de rekenkern zelf" },
        { regel: "Geef mij de polder, de maatregel en het weer, en de volgende polder staat vast. Alle onzekerheid zit in het weer.", nadruk: [0, 1, 2] },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "R", sym: "R", zone: "tuple",
      titel: "de beloning",
      formule: "wat het kost, tegen de schade die je niet meer hebt",
      rijen: [
        ["kosten van de maatregel",      "€",          "eenmalig, contant gemaakt"],
        ["vermeden schade",              "€ per jaar", "de verwachte jaarschade daalt"],
        ["maatregelen zonder prijs",     "2 van de 5", "verdringing en drooglegging"],
        ["hier komt bergen erbij",       "€ 0,14 mln", "per centimeter drooglegging"],
        ["hier verdwijnt afvoeren",      "€ 1,5 mln",  "per centimeter drooglegging"],
      ],
      bron: "de omslagprijzen zijn gerekend, niet gekozen",
      beats: [
        { regel: "Wat maakt het ene pad beter dan het andere? Kosten nu, tegen schade die je niet meer hebt.",
          toon: 2 },
        { regel: "En hier wordt het oncomfortabel: twee van de vijf maatregelen hebben geen prijs in euro's.",
          toon: 3, nadruk: [2] },
        { regel: "Dus noemen we geen beloning, maar de prijs waarop het antwoord kantelt.",
          toon: 5, nadruk: [3, 4] },
        { regel: "En de norm blijft een eis. Geef je hem een strafterm, dan heb je stil een prijs voor een overstroming gekozen.",
          toon: 5 },
      ] },

    // ───────────────────────────────────────────────────────────────────────
    { sleutel: "g", sym: "γ", zone: "buiten",
      titel: "de tijd",
      formule: "wat een euro over vijftig jaar nog weegt",
      figuur: "zaagtand",
      bron: "de vorm is het punt; de discontovoet ligt nog niet vast",
      beats: [
        { regel: "Tot hier was er geen tijd. Eén bui, één antwoord.", nadruk: [] },
        { regel: "Doe je niets, dan loopt het risico op door klimaat en bodemdaling — dwars door de norm heen.", nadruk: [0] },
        { regel: "Zet de maatregelen in de tijd en het wordt een zaagtand die eronder blijft.", nadruk: [0, 1] },
        { regel: "En omdat een euro later lichter weegt, is er een beste moment om te bouwen: zelden nu, zelden nooit.", nadruk: [0, 1, 2] },
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
