// ═══════════════════════════════════════════════════════════════════════════
// De vijf antwoorden zoals de MCP-endpoint ze gaf, met de aanroep erboven.
// ═══════════════════════════════════════════════════════════════════════════
//
// Elk getal op het scherm komt hieruit. Er staat niets in `inhoud.js` dat met
// de hand is overgetypt: die leest deze velden, zodat een verschil tussen de
// deck en de rekenkern niet kan bestaan zonder dat dit bestand meebeweegt.
//
// Dit is een OPNAME en geen live aanroep. Een statische pagina spreekt geen
// MCP-server, en een presentatie die op een netwerkfout kan stukvallen is geen
// presentatie. Hoe je hem opnieuw opneemt staat in de README.
//
// De invoer is voor elke aanroep hetzelfde gebied en dezelfde bui, en dat is
// het punt: vijf vragen over één toestand.

var TRANSCRIPT = {
  opgenomen: "2026-09-07",
  server: "vuistregels (MCP)",

  // Het plangebied uit het MER, met het open water uit de legger van Rijnland
  // en het gemaal uit dezelfde legger. De bui is die van het rapport.
  gebied: {
    area_ha: 174,
    percentage_open_water: 7.4,
    discharge_capacity_m3_per_min: 19.94,
    rain_volume_mm: 120,
    length_event_hrs: 48,
    delta_h_available: 0.5
  },

  // Wat er uit de legger komt en niet uit een aanname. Vier knopen, en de
  // peilen die het MER noemt staan er tot op de centimeter in.
  legger: [
    { code: "PBS_OR-3.21.1.1", naam: "Gnephoek, hoofdpeilvak", ha: 193.7, zp: -2.38, wp: -2.48, gemaal: 19.94 },
    { code: "PBS_OR-3.21.2.1", naam: "inliggend laag peilvak", ha: 30.9, zp: -2.75, wp: -2.95, gemaal: 0.82 },
    { code: "PBS_OR-3.48.1.1", naam: "Vrouwgeestpolder", ha: 152.4, zp: -4.89, wp: -5.0, gemaal: 20.3 },
    { code: "PBS_OR-3.54.0.1", naam: "Bruimadeschepolder", ha: 61.7, zp: -2.3, wp: -2.38, gemaal: null }
  ],
  open_water_legger_pct: 7.4,
  open_water_rapport_pct: 7,

  // Het antwoord dat het MER zelf geeft, uit tabel 4.1 en 4.2.
  rapport: {
    randvoorwaarden: [
      "de Gnephoekpolder moet zijn eigen broek ophouden",
      "een toelaatbare maximale peilstijging van 50 cm",
      "het gebied kan een piekbui van 120 mm in 1 dag bergen"
    ],
    tabel41: [
      { post: "oppervlaktewater en plasdras", pct: 20, ha: 45, mm: 100 },
      { post: "inundeerbaar land", pct: 5, ha: 11, mm: 19 },
      { post: "groen en onverhard deel tuinen", pct: 28, ha: 63, mm: 4 }
    ],
    totaal: { pct: 53, ha: 92, mm: 123 },
    huidig_mm_bij_30cm: 21
  },

  // ── de drie losse maatregelen, elk op dezelfde vraag ────────────────────
  bergen: {
    tool: "calculate_store_given_h",
    status: "exact",
    dh_reference_m: 0.5711,
    dh_with_measure_m: 0.5,
    delta_open_water_ha: 1.952,
    area_ha_required_open_water: 14.83,
    new_area_percentage: 8.522,
    before_ha: 12.88,
    delta_percentage_points: 1.122,
    cost: 263500,
    cost_range: [234300, 449000],
    spreiding: "2 tot 7,4 ha, afhankelijk van time_of_year"
  },
  afvoeren: {
    tool: "calculate_discharge_given_h",
    status: "exact",
    extra_m3_per_sec: 0.03534,
    extra_m3_per_min: 2.12,
    totaal_m3_per_min: 22.06,
    totaal_mm_d: 18.26,
    before_m3_per_sec: 0.3323,
    cost: 67850,
    cost_range: [65730, 72090],
    spreiding: "0,035 tot 0,18 m3/s, afhankelijk van time_of_year"
  },
  vasthouden: {
    tool: "calculate_retention_given_h",
    status: "exact",
    area_polder_delayed_ha: 24.86,
    area_percentage_delayed: 15.43,
    days_to_retain: 2,
    cost: 59670,
    cost_range: [31080, 74580],
    spreiding: "25 tot 73 ha, afhankelijk van days_to_discharge",
    winter: "in de winter haalt vasthouden het doel niet alleen"
  },

  // ── het pakket: de ordening, en niet de maatvoering ─────────────────────
  pakket: {
    tool: "find_package_given_protection",
    status: "exact",
    mixes_examined: 31,
    dh_without_measure_m: 0.5711,
    best: { maatregel: "vasthouden", ha: 24.88, cost: 59720, cost_range: [31100, 74650], replacement_cost: 59720 },
    near_optimal: { maatregel: "afvoeren", m3_per_sec: 0.03534, cost: 67850, replacement_cost: 705900 },
    cost_epsilon: 0.7292,
    ranges: [
      { naam: "vasthouden", eenheid: "ha land", min: 24.88, max: 43.03, rol: "optional", bron: "prijsband", reden: null },
      { naam: "afvoeren", eenheid: "m3/s", min: 0, max: 0.03534, rol: "optional", bron: "prijsband", reden: null },
      { naam: "bergen", eenheid: "ha open water", min: 0, max: 0, rol: "absent", bron: null, reden: "buiten_prijsband" },
      { naam: "peilopzet", eenheid: "m", min: 0, max: 0, rol: "absent", bron: null, reden: "draagt_niet_bij" },
      { naam: "aanvoeren", eenheid: "m3/s inlaat", min: 0, max: 0, rol: "absent", bron: null, reden: "draagt_niet_bij" }
    ]
  },

  // ── het netwerk: twee lezingen van dezelfde vier knopen ─────────────────
  cascade_los: {
    tool: "calculate_cascade_given_excess",
    variant: "Gnephoek en Vrouwgeest lozen elk apart op de boezem",
    depth: 2,
    converged: true,
    worst_node: "Gnephoek inliggend laag peilvak",
    worst_dh_m: 1.164,
    median_dh_m: 1.044,
    lowest_dh_m: 0.664,
    coupling_effect_m: 0
  },
  cascade_via_vrouwgeest: {
    tool: "calculate_cascade_given_excess",
    variant: "Gnephoek loost via de inlaten op de Vrouwgeestpolder",
    depth: 3,
    converged: true,
    worst_node: "Vrouwgeestpolder",
    worst_dh_m: 2.774,
    median_dh_m: 1.103,
    lowest_dh_m: 0.664,
    coupling_effect_m: 2.019
  },

  // ── het onderzoek: de vraag en de hypothese ────────────────────────────
  // Het onderzoeksobject is de TOOLSET en niet de polder. Drie gebieden zijn de
  // experimentele situaties waarin die toolset wordt getest, en het antwoord op de
  // gebiedsvraag is de secundaire uitkomst, en die viel niet samen met de rapporten.
  onderzoek: {
    vraag: "Hoe benadert en gebruikt een agent onze MCP-toolset bij het beantwoorden van een gebruikersvraag?",
    primair: "inzicht in de benadering en het gebruik van de toolset",
    secundair: "het antwoord op de gebiedsvraag zelf",
    hypothese: "Een goed ontworpen toolset maakt de relevante tool vindbaar en kiesbaar — maar wat de agent er dan mee doet, hoeft niet te zijn waarvoor die tool is ontwikkeld.",
    schakels: [
      { l: "vindbaar" },
      { l: "kiesbaar" },
      { l: "gebruikt", splits: ["zoals de tool is ontworpen", "zoals de vraag het vraagt"] }
    ],
    // De keten valt in stukken, en dat is niet cosmetisch: het middenstuk is een LUS die
    // de agent doorloopt tot hij genoeg heeft om te antwoorden. Eén tool call per
    // gebruikersvraag is niet hoe dit werkt. Hoeveel rondes het per situatie werden staat
    // bij de analyse en niet hier: dat is een uitkomst.
    keten: {
      eenmaal: ["gebruikersvraag", "doel", "is er een tool?"],
      herhaald: ["toolselectie", "parameters", "tool call", "resultaat"],
      slot: ["antwoord"],
      // Geen aantallen hier: hoeveel aanroepen het werden is een UITKOMST en hoort bij
      // de analyse. In de opzet staat alleen het mechanisme.
      lus: "de agent doorloopt dit cyclisch, tot hij genoeg heeft voor een antwoord"
    },
    eerlijk: "het taalmodel rekent niet — het vertaalt"
  },

  // ── het antwoord op de onderzoeksvraag ─────────────────────────────────
  // Dezelfde vorm als de vraag in stap 1, zodat de zaal ziet dat dit hetzelfde ding is:
  // eerst wat de toolset deed, dan waar hij kraakte, en pas daarna de bonus.
  beantwoord: {
    vraag: "Hoe benadert en gebruikt een agent onze MCP-toolset bij het beantwoorden van een gebruikersvraag?",
    // Dezelfde drie schakels als bij de hypothese, nu met wat er van elk terechtkwam.
    // Zo is het antwoord letterlijk de vraag met een oordeel erop.
    schakels: [
      { l: "vindbaar", teken: "ja", maat: "twaalf tools", regel: "alle vier de groepen werden gevonden" },
      { l: "kiesbaar", teken: "ja", maat: "15 van 15", regel: "elke aanroep geldig, in drie situaties" },
      { l: "gebruikt", teken: "anders", maat: "4 van 6", regel: "cascade-aanroepen waren geen netwerk" }
    ],
    slot: "De toolset is vindbaar en kiesbaar. Maar hij wordt gebruikt zoals de vraag het vroeg, en niet altijd zoals hij is ontworpen.",
    // Geen "bonus": dit is de secundaire uitkomst, en hij is niet vleiend. Het antwoord
    // was in alle drie de gebieden náást de rapportconclusie te leggen - en in geen van
    // de drie kwam het ermee overeen.
    secundair: {
      kop: "secundaire uitkomst",
      tekst: "In alle drie de gebieden was het antwoord naast een gepubliceerde rapportconclusie te leggen — en in geen van de drie kwam het ermee overeen."
    }
  },

  // ── de toolbox: wat er beschikbaar is ──────────────────────────────────
  // Dit is het gereedschap dat in het experiment openstond, vóór er één vraag is
  // gesteld. De groepen komen later terug: in de keten van aanroepen en in de plaat
  // met gebruikt tegenover ongebruikt hebben ze dezelfde kleur.
  toolbox: {
    groepen: [
      {
        soort: "handleiding", kop: "de handleiding",
        vraag: "wat betekenen deze getallen, en hoe geef ik ze door?",
        tools: [{ naam: "read_me", wat: "bronnen, vuistregels, gebruik, terugkoppelen, pakketzoeker" }]
      },
      {
        soort: "maatregel", kop: "één maatregel, twee richtingen",
        vraag: "hoe groot moet deze maatregel zijn — of wat doet deze maatregel?",
        tools: [
          { naam: "calculate_store_given_h", wat: null },
          { naam: "calculate_store_given_area", wat: null },
          { naam: "calculate_discharge_given_h", wat: null },
          { naam: "calculate_discharge_given_discharge", wat: null },
          { naam: "calculate_retention_given_h", wat: null },
          { naam: "calculate_retention_given_area", wat: null },
          { naam: "calculate_supply_given_h", wat: null },
          { naam: "calculate_supply_given_supply", wat: null }
        ]
      },
      {
        soort: "netwerk", kop: "het systeem",
        vraag: "wat doen gebieden met elkaar — nat en droog?",
        tools: [
          { naam: "calculate_cascade_given_excess", wat: "wateroverlast op een keten van gebieden" },
          { naam: "calculate_allocation_given_shortage", wat: "de verdringingsreeks bij een tekort" }
        ]
      },
      {
        soort: "pakket", kop: "het pakket",
        vraag: "welke combinatie haalt deze bescherming, en wat kost die?",
        tools: [{ naam: "find_package_given_protection", wat: "zoekt de mix en geeft de bandbreedte erbij" }]
      }
    ],
    totaal: "twaalf tools",
    meebrengt: "Elke tool draagt een invoerschema met per veld een beschrijving en een bandbreedte, en elk antwoord draagt `status`, `assumptions`, `sensitivity` en `caveats`. De beschrijvingen van de UITVOERvelden komen niet mee: de client geeft het resultaat door als kale JSON.",
  },

  // ── de resultaten per criterium, per casus ─────────────────────────────
  // De primaire uitkomst staat bovenaan en de gebiedsvraag onderaan, want dat is de
  // rangorde van het onderzoek. `deels` is geen zachte ja: het staat er waar de
  // aanroep geldig was maar niet betekende wat de tool bedoelt.
  resultaten: {
    casussen: ["Gnephoek", "Zuidplaspolder", "Kockengen"],
    rijen: [
      { criterium: "relevante tool gevonden", waarden: ["ja", "ja", "ja"],
        noot: "handleiding eerst" },
      { criterium: "juiste tool geselecteerd", waarden: ["ja", "deels", "deels"],
        noot: "netwerk als scenariorij" },
      { criterium: "parameters correct", waarden: ["deels", "deels", "deels"],
        noot: "bui van één dag, maalstop, verbod" },
      { criterium: "tool call uitgevoerd", waarden: ["ja", "ja", "ja"], primair: true,
        noot: "vijftien van vijftien" },
      { criterium: "bruikbare uitvoer", waarden: ["ja", "deels", "deels"],
        noot: "geen resultaat per knoop" },
      { criterium: "gebiedsvraag beantwoord", waarden: ["ja", "ja", "ja"], secundair: true,
        noot: "naast de conclusie te leggen, niet gelijk" }
    ],
    slot: "Niet het antwoord maar de aanleiding: elke `~` is een plek waar het gebruik van het ontwerp afweek."
  },

  // ── de drie casussen, in dezelfde vorm ─────────────────────────────────
  // Elke casus draagt dezelfde vier blokken: de toestand die de kern in gaat, de vraag
  // zoals het rapport hem stelt, ons antwoord, en de conclusie van het rapport ernaast.
  // Dat de vorm identiek is, is het punt: dan is het verschil tussen de casussen het
  // gebied en niet de manier van kijken.
  casussen: [
    {
      naam: "Gnephoek",
      soort: "een inverse ontwerpvraag",
      plaats: "Alphen aan den Rijn · 5.500 woningen gepland",
      bron: "MER-deelrapport bodem, water en klimaat, 26 juni 2023 · toetsingsadvies Commissie m.e.r. 23 januari 2026",
      context: [
        { l: "plangebied", r: "174 ha" },
        { l: "open water", r: "7,4 % (legger Rijnland) · 7 % (rapport)" },
        { l: "gemaal", r: "19,94 m³/min, draait tijdens de bui" },
        { l: "de bui", r: "120 mm in 1 dag (convenant klimaatadaptief bouwen)" }
      ],
      vraag: "Hoeveel oppervlaktewater en inundeerbaar land heb je nodig om die bui te bergen bij maximaal 50 cm peilstijging, als de polder zijn eigen broek moet ophouden?",
      antwoord: [
        { l: "zonder maatregel", r: "57 cm" },
        { l: "bergen", r: "+1,95 ha open water → 8,5 %", nadruk: true },
        { l: "afvoeren", r: "+0,035 m³/s → 22,06 m³/min" },
        { l: "vasthouden", r: "24,86 ha land (15,4 %)" },
        { l: "goedkoopste pakket", r: "vasthouden 24,88 ha · € 59.720" }
      ],
      rapport: [
        { l: "oppervlaktewater", r: "20 % = 45 ha" },
        { l: "inundeerbaar land", r: "5 % = 11 ha" },
        { l: "samen", r: "92 ha · 123 mm berging" },
        { l: "methode", r: "statische volumesom" }
      ],
      tegenover: {
        grootheid: "hoeveel open water erbij moet",
        rapport: { getal: "45", eenheid: "ha", bij: "20 % van het plangebied, plus 11 ha inundeerbaar land" },
        kern: { getal: "+2", eenheid: "ha", bij: "van 7,4 naar 8,5 % open water" },
        duiding: "Het rapport bergt de hele bui in een volumesom. Onze toolset laat het gemaal tijdens de bui doordraaien en verdeelt de dagsom over vier afvoerdagen — vandaar een factor twintig verschil."
      },
      duiding: "Het rapport vraagt 45 hectare open water, de kern vraagt er 2 bíj. Dat verschil is de methode: 0,07 × 300 mm = 21 mm, op de millimeter — er zit geen tijd in en geen gemaal.",
      rangorde: { eerste: "vasthouden, 25 ha", bergen: "buiten prijsband", vasthouden: "goedkoopste" }
    },
    {
      naam: "Zuidplaspolder",
      soort: "een voorwaartse doorrekening",
      plaats: "gemeente Zuidplas · 8.000 woningen in het Middengebied",
      bron: "MER Zuidplaspolder, rapportage water bodem en klimaat, Sweco, versie C3, 4 november 2022",
      context: [
        { l: "plangebied", r: "1.116 ha · 12 % nat" },
        { l: "uit de legger", r: "100 peilvakken · 4.592 ha · 9,2 % open water" },
        { l: "gemaal", r: "Abraham Kroes 850 m³/min = 18 mm/dag" },
        { l: "de bui", r: "200 mm in 48 uur, mét maalstop" }
      ],
      vraag: "Hoe hoog komt het water bij de Limburgbui van juli 2021, als de Maeslantkering en de Algerakering dichtgaan en er dus een maalstop geldt?",
      antwoord: [
        { l: "maalstop", r: "152 cm", nadruk: true },
        { l: "met 18 mm/dag", r: "93 cm" },
        { l: "per deelgebied", r: "92 cm bij 20 % nat · 182 cm bij 10 %" },
        { l: "en het model meldt zelf", r: "boven een meter is dit een bovengrens" },
        { l: "wat er nodig is", r: "bergen 153 ha (forced) · € 20,7 mln" }
      ],
      rapport: [
        { l: "maximaal peil", r: "−5,64 m NAP" },
        { l: "stijging", r: "+84 cm boven bovenpeil" },
        { l: "oppervlak onder water", r: "60 %", nadruk: true },
        { l: "methode", r: "gedetailleerd, land bergt mee" }
      ],
      tegenover: {
        grootheid: "hoe hoog het water komt bij 200 mm met maalstop",
        rapport: { getal: "84", eenheid: "cm", bij: "en 60 % van het oppervlak onder water" },
        kern: { getal: "152", eenheid: "cm", bij: "als bovengrens, met een vast open-wateroppervlak" },
        duiding: "Het verschil is precies het land dat meebergt zodra het water over de kant komt. De toolset meldt dat zelf: boven een meter is dit een bovengrens en geen voorspelling."
      },
      duiding: "Een factor twee — en het model zegt zelf waarom: het rekent met een vast open-wateroppervlak. Het rapport kwantificeert precies wat er dan gebeurt: 60 % van het gebied loopt onder. Hier valideert de casus niet het getal maar het voorbehoud.",
      rangorde: { eerste: "bergen, 153 ha (forced)", bergen: "de enige die het haalt", vasthouden: "draagt niet bij" }
    },
    {
      naam: "Kockengen",
      soort: "een gemeten gebeurtenis",
      plaats: "maalgebied De Tol · polders Portengen en Kortrijk · 28 juli 2014",
      bron: "HDSR, Evaluatie wateroverlast Kockengen juli 2014, 22 september 2014",
      context: [
        { l: "maalgebied De Tol", r: "1.248,5 ha · 19 peilvakken" },
        { l: "open water", r: "9,2 % (legger HDSR)" },
        { l: "gemaal De Tol", r: "13 mm/dag in 2014 · 144 m³/min in de legger van nu" },
        { l: "de bui", r: "138 mm gemeten op 28 juli 2014" }
      ],
      vraag: "Hoe kon deze bui tot drie à vier etmalen overlast leiden, hoeveel deed het gebiedsvreemde water daaraan, en is een structurele uitbreiding van het gemaal aangewezen?",
      antwoord: [
        { l: "met de capaciteit van 2014", r: "76 cm", nadruk: true },
        { l: "met de legger van nu", r: "64 cm — de uitbreiding is 12 cm waard" },
        { l: "plus het gebiedsvreemde water", r: "82 cm → dat kostte 6 cm" },
        { l: "om op 30 cm te blijven", r: "+2,32 m³/s → van 13 naar 29 mm/dag" },
        { l: "prijs daarvan", r: "€ 4,4 mln lineair · € 8,1 mln als vervanging" }
      ],
      rapport: [
        { l: "oorzaak 1", r: "138 mm neerslag" },
        { l: "oorzaak 2", r: "40.000–80.000 m³ gebiedsvreemd water" },
        { l: "oorzaak 3", r: "ontoereikende boezem Groote Heicop" },
        { l: "over het gemaal", r: "13 mm/dag, conform landelijke normen" },
        { l: "de uitbreidingsvraag", r: "gesteld, niet beantwoord", nadruk: true }
      ],
      tegenover: {
        grootheid: "hoeveel gemaalcapaciteit het gebied nodig heeft",
        rapport: { getal: "13", eenheid: "mm/d", bij: "conform de landelijke norm; uitbreiding: vraag gesteld, niet beantwoord" },
        kern: { getal: "29", eenheid: "mm/d", bij: "om bij deze bui op 30 cm te blijven — € 4,4 mln" },
        duiding: "De evaluatie stelt de vraag of een structurele uitbreiding aangewezen is en laat hem open. Onze toolset geeft hem een maat en een prijs."
      },
      duiding: "De drie oorzaken van het rapport krijgen hier een maat: het gebiedsvreemde water is 6 van de 76 centimeter, dus echt maar tweede-orde. En de vraag die het rapport openlaat, krijgt een prijs.",
      rangorde: { eerste: "afvoeren 1,2 m³/s (forced) plus vasthouden 597 ha", bergen: "buiten prijsband", vasthouden: "optioneel, 597–1.123 ha" }
    }
  ],

  // ── de limitaties, zoals ze in deze drie casussen zijn opgelopen ────────
  // Niet een lijst zwakheden op voorraad, maar wat er in dit experiment daadwerkelijk
  // knelde. Achter elke regel staat de casus waar hij zich liet zien.
  limitaties: [
    { groep: "de bui", wat: "alleen buiduren 48, 96 en 192 uur", waar: "alle drie de situaties", hard: true },
    { groep: "de bui", wat: "20 mm neerslagverlies uit een landelijke vuistregel", waar: "Zuidplas: infiltratie stopt juist", hard: false },
    { groep: "het gebied", wat: "boven ongeveer een meter is de uitkomst een bovengrens", waar: "Zuidplas: 152 tegen 84 cm", hard: true },
    { groep: "het gebied", wat: "peilvakken worden tot één knoop gelumpt", waar: "De Tol 19, Zuidplas 100", hard: true },
    { groep: "het gebied", wat: "geen kwel of wegzijging", waar: "Zuidplas: 10 % van het gemaal", hard: false },
    { groep: "het netwerk", wat: "één uitgaande verbinding per knoop", waar: "Gnephoek splitst zijn afvoer", hard: true },
    { groep: "het netwerk", wat: "geen stuwen en geen kruinbewegingen", waar: "Kockengen: over de stuwen heen", hard: true },
    { groep: "de prijs", wat: "kosten lineair, terwijl een gemaal een trapkost is", waar: "Kockengen: 4,4 tegen 8,1 mln", hard: false },
    { groep: "de vraag", wat: "een maatregel verbieden kan niet", waar: "twee van de drie situaties", hard: true },
    { groep: "de vraag", wat: "faalmechanismen zitten er niet in", waar: "Kockengen: gemaal en stuw", hard: false }
  ],

  // ── het experiment: het aanroepen zelf als uitkomst ─────────────────────
  // Alles hieronder komt uit de sessielog van deze ene sessie, niet uit herinnering.
  experiment: {
    sessie: { start: "15:37:45", eind: "22:44:14", uren: 7.1, calls: 239, mcp: 15, datum: "7 september 2026" },
    per_casus: [
      {
        casus: "Gnephoek", calls: 85, mcp: 7, minuten: 56, mcp_blok_s: 114, venster: "17:21:32–17:23:26",
        volgorde: ["read_me", "store_given_h", "discharge_given_h", "retention_given_h",
                   "find_package_given_protection", "cascade_given_excess", "cascade_given_excess"],
        lezing: "breedte eerst: de handleiding, dan alle drie de losse maatregelen, dan het pakket, dan het netwerk"
      },
      {
        casus: "Zuidplaspolder", calls: 41, mcp: 4, minuten: 13, mcp_blok_s: 44, venster: "21:53:52–21:54:36",
        volgorde: ["cascade_given_excess", "cascade_given_excess",
                   "find_package_given_protection", "find_package_given_protection"],
        lezing: "meteen naar de twee tools die de vraag beantwoorden; geen verkenning meer"
      },
      {
        casus: "Kockengen", calls: 29, mcp: 4, minuten: 7, mcp_blok_s: 20, venster: "22:10:44–22:11:04",
        volgorde: ["cascade_given_excess", "cascade_given_excess",
                   "find_package_given_protection", "discharge_given_h"],
        lezing: "netwerk, pakket, en één losse tool om de uitkomst een prijs te geven"
      }
    ],
    gebruikt: [
      { tool: "calculate_cascade_given_excess", n: 6 },
      { tool: "find_package_given_protection", n: 4 },
      { tool: "calculate_discharge_given_h", n: 2 },
      { tool: "calculate_store_given_h", n: 1 },
      { tool: "calculate_retention_given_h", n: 1 },
      { tool: "read_me", n: 1 }
    ],
    ongebruikt: [
      { tool: "calculate_store_given_area", groep: "voorwaarts" },
      { tool: "calculate_retention_given_area", groep: "voorwaarts" },
      { tool: "calculate_discharge_given_discharge", groep: "voorwaarts" },
      { tool: "calculate_supply_given_h", groep: "droge kant" },
      { tool: "calculate_supply_given_supply", groep: "droge kant" },
      { tool: "calculate_allocation_given_shortage", groep: "droge kant" }
    ],
    bevindingen: [
      {
        kop: "de volgorde verraadt een geleerde aanpak",
        tekst: "Eerst de breedte, daarna gericht. Het MCP-blok kromp van 114 naar 44 naar 20 seconden."
      },
      {
        kop: "zes van de twaalf tools zijn nooit aangeroepen",
        tekst: "Alle voorwaartse varianten, en de hele droge kant. De omkering is wat de rapporten vragen."
      },
      {
        kop: "de cascade werd geleend als batchloper",
        tekst: "Geen `drains_to`, dezelfde polder twee keer. Dan zeggen `depth` en `coupling_effect_m` niets meer."
      },
      {
        kop: "de eenheden lieten de aanroeper rekenen",
        tekst: "Drie keer met de hand omgerekend, en die conversies staan in geen enkel `assumptions`."
      }
    ],
    // Alle zes de cascade-aanroepen, genummerd op volgorde en gegroepeerd per casus.
    // Geen tijdstippen: de volgorde is wat iets zegt, het uur niet. De naam staat in elke
    // knoop, want daaraan is te zien wat de aanroep bedoelt - bij de laatste vier draagt
    // hij een scenario in plaats van een gebied.
    zes: [
      {
        casus: "Gnephoek",
        aanroepen: [
          {
            nr: 1, bui: "120 mm", vorm: "graaf",
            intentie: "de vier peilvakken zoals ze in de legger liggen: Gnephoek loost op de boezem, Bruimadesche op Vrouwgeest",
            tel: "4 knopen · 2× drains_to · 4 oppervlakken",
            knopen: [
              { id: "inl", label: "inliggend laag", maat: "30,9 ha · 0,0137 m³/s", kol: 0, rij: 0 },
              { id: "hoo", label: "hoofdpeilvak", maat: "193,7 ha · 0,3323 m³/s", kol: 1, rij: 0 },
              { id: "bru", label: "Bruimadesche", maat: "61,7 ha · 0,0926 m³/s", kol: 0, rij: 1 },
              { id: "vro", label: "Vrouwgeest", maat: "152,4 ha · 0,3383 m³/s", kol: 1, rij: 1 }
            ],
            pijlen: [["inl", "hoo"], ["bru", "vro"]],
            uitkomst: { veld: "coupling_effect_m", waarde: "0", dus: "anders verbinden" }
          },
          {
            nr: 2, bui: "120 mm", vorm: "graaf",
            intentie: "en nu de andere lezing: Gnephoek leidt zijn water via de inlaten naar Vrouwgeest — wat kost die splitsing benedenstrooms?",
            tel: "4 knopen · 3× drains_to · 4 oppervlakken",
            knopen: [
              { id: "inl", label: "inliggend laag", maat: "30,9 ha · 0,0137 m³/s", kol: 0, rij: 0 },
              { id: "hoo", label: "hoofdpeilvak", maat: "193,7 ha · 0,3323 m³/s", kol: 1, rij: 0 },
              { id: "bru", label: "Bruimadesche", maat: "61,7 ha · 0,0926 m³/s", kol: 0, rij: 1 },
              { id: "vro", label: "Vrouwgeest", maat: "152,4 ha · 0,3383 m³/s", kol: 2, rij: 0.5 }
            ],
            pijlen: [["inl", "hoo"], ["hoo", "vro"], ["bru", "vro"]],
            uitkomst: { veld: "coupling_effect_m", waarde: "2,02 m", dus: "de tool als netwerk", slot: true }
          }
        ]
      },
      {
        casus: "Zuidplaspolder",
        aanroepen: [
          {
            nr: 1, bui: "200 mm", vorm: "kolom", smal: true,
            intentie: "wat doet de Limburgbui in elk van de zeven deelgebieden uit tabel 6-1, met de maalstop van het MER?",
            tel: "7 knopen · 0× drains_to · 7 oppervlakken",
            knopen: [
              { id: "a", label: "de Watertuin", maat: "133 ha · 20 % nat", kol: 0, rij: 0, los: true },
              { id: "b", label: "Kreekrug", maat: "162 ha · 20 % nat", kol: 1, rij: 0, los: true },
              { id: "c", label: "Bedrijven", maat: "87 ha · 10 % nat", kol: 2, rij: 0, los: true },
              { id: "d", label: "Bos", maat: "128 ha · 10 % nat", kol: 3, rij: 0, los: true },
              { id: "e", label: "Energielandschap", maat: "77 ha · 10 % nat", kol: 0, rij: 1, los: true },
              { id: "f", label: "Groene schakel", maat: "236 ha · 10 % nat", kol: 1, rij: 1, los: true },
              { id: "g", label: "Lintbebouwing", maat: "54 ha · 10 % nat", kol: 2, rij: 1, los: true }
            ],
            pijlen: [],
            uitkomst: { veld: "worst · lowest", waarde: "2 waarden op 7 gebieden", dus: "twee knopen is genoeg" }
          },
          {
            nr: 2, bui: "200 mm", vorm: "kolom", breed: 264,
            intentie: "hetzelfde plangebied met en zonder maalstop, om te zien wat die maalstop in centimeters kost",
            tel: "2 knopen · 0× drains_to · 1 oppervlak",
            knopen: [
              { id: "a", label: "plangebied met maalstop", maat: "1.116 ha · 0 m³/s", kol: 0, rij: 0, los: true, zelfde: true },
              { id: "b", label: "plangebied met 18 mm per dag", maat: "1.116 ha · 2,325 m³/s", kol: 0, rij: 1, los: true, zelfde: true }
            ],
            pijlen: [],
            uitkomst: { veld: "worst · lowest", waarde: "152 tegen 93 cm", dus: "de knoop wordt een scenario", slot: true }
          }
        ]
      },
      {
        casus: "Kockengen",
        aanroepen: [
          {
            nr: 1, bui: "138 mm", vorm: "kolom",
            intentie: "de gemeten bui van 28 juli 2014 op het gemaal van toen en op dat van de legger van nu",
            tel: "2 knopen · 0× drains_to · 1 oppervlak",
            knopen: [
              { id: "a", label: "De Tol · capaciteit 2014", maat: "1.248,5 ha · 1,879 m³/s", kol: 0, rij: 0, los: true, zelfde: true },
              { id: "b", label: "De Tol · legger van nu", maat: "1.248,5 ha · 2,4 m³/s", kol: 0, rij: 1, los: true, zelfde: true }
            ],
            pijlen: [],
            uitkomst: { veld: "worst · lowest", waarde: "76 tegen 64 cm", dus: "en nu 2014 met het gebiedsvreemde water erbij" }
          },
          {
            nr: 2, bui: "144,4 mm", vorm: "kolom", breed: 264,
            intentie: "de tool kent geen inlaat, dus de 80.000 m³ gebiedsvreemd water gaat erin als 6,4 mm extra neerslag: dezelfde toestand, een grotere bui",
            tel: "1 knoop · 0× drains_to",
            knopen: [
              { id: "a", label: "De Tol 2014 plus gebiedsvreemd water", maat: "1.248,5 ha · 1,879 m³/s", kol: 0, rij: 0, los: true }
            ],
            pijlen: [],
            uitkomst: { veld: "worst_dh_m", waarde: "82 cm", dus: "6 cm meer dan aanroep 1 — als bui, niet als inlaat", slot: true }
          }
        ]
      }
    ],

    aanbevelingen: [
      { wat: "gelijktijdig scenario\u2019s doorrekenen", waarom: "dan hoeft het netwerk niet als batchloper geleend te worden", voor: true },
      { wat: "dezelfde eenheden op elke knoop", waarom: "mm/dag en m³/min erbij, zodat de aanroeper niet zelf omrekent", voor: true },
      { wat: "een maatregel kunnen uitsluiten", waarom: "een verbod is nu niet te zeggen, alleen achteraf terug te lezen", voor: true },
      { wat: "het neerslagverlies als schakelaar", waarom: "`apply_summer_loss` bestaat in de kern, niet in de tool" },
      { wat: "een buiduur van 24 uur toestaan", waarom: "bij een opgegeven volume, en het patroonveld dan weigeren" },
      { wat: "eigen conversies terugmelden", waarom: "wat de aanroeper zelf omrekende staat in geen enkel `assumptions`" },
      { wat: "houden wat werkt", waarom: "read_me vooraf, een bandbreedte per invoerveld, `why_it_matters` bij elke aanname, en de caveat die zijn eigen bereik afbakent", houden: true }
    ]
  },

  // ── de externe vergunning: STOWA 2018-68 op dezelfde polder ─────────────
  // Onderzoeksvraag van dat rapport: welke modelfunctionaliteiten zijn minimaal vereist om
  // de inundatie van juli 2014 in polder De Tol te simuleren? Onze vraag, gepubliceerd.
  stowa2018: {
    bron: "STOWA 2018-68 — Wat is minimaal nodig om een gebied hydrologisch goed te modelleren? Voorbeeldstudie: polder De Tol, juli 2014",
    rijen: [
      { functie: "neerslag-afvoermodel", oordeel: "cruciaal", wij: "hebben we — Tabel 39", goed: true },
      { functie: "volledige ondiepwatervergelijkingen", oordeel: "gewenst, geen minimumvereiste", wij: "hoeven we dus niet", goed: true },
      { functie: "rioolstelsel", oordeel: "alleen binnen de dorpskern", wij: "buiten onze vraag", goed: true },
      { functie: "accurate peilgrenzen", oordeel: "cruciaal", wij: "wij lumpen 19 peilvakken tot één knoop", goed: false },
      { functie: "kruinbewegingen van stuwen", oordeel: "cruciaal voor de duur", wij: "wij hebben geen stuwen", goed: false }
    ],
    bovenal: "de simulatie is een orde van grootte gevoeliger voor de keuze van het radarneerslagproduct dan voor al deze modelkeuzes samen"
  },

};
