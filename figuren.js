// ═══════════════════════════════════════════════════════════════════════════
// De registratie: welke naam uit inhoud.js hoort bij welke plaat.
// ═══════════════════════════════════════════════════════════════════════════
//
// Een figuur krijgt de beat-nadruk als lijst van deelnummers; welk deel bij welk
// nummer hoort staat in de `data-deel` van de tekening. Dat contract loopt van
// `inhoud.js` (`nadruk: [0, 1]`) via `stemAf` in `motor.js` naar de groepen
// hieronder, en het is nergens afgedwongen — een index zonder deel licht niets
// op en zegt er niets over. De nummering staat daarom bij elke plaat in
// commentaar, en dat commentaar is de enige plek waar hij staat.
//
// De platen die uit een bouwer komen staan in `teken/`. Wat hieronder inline
// staat, staat inline omdat het niets deelt: één tekening, één keer gebruikt.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  var polderAnimatie = T.polderAnimatie,
      neerslagstatistiek = T.neerslagstatistiek,
      droogtestatistiek = T.droogtestatistiek,
      frequentielijn = T.frequentielijn,
      kostencurve = T.kostencurve,
      topdownNatDroog = T.topdownNatDroog,
      topdownPolder = T.topdownPolder,
      topdownNetwerk = T.topdownNetwerk,
      transitiePaneel = T.transitiePaneel,
      wereldmodel = T.wereldmodel,
      ICOON_ROBOT = T.ICOON_ROBOT,
      POLDER = T.POLDER,
      kolommen = T.kolommen,
      lijsten = T.lijsten;

  var FIGUREN = {

    polder_animatie: polderAnimatie,

    oplossingsruimte: T.oplossingsruimte,
    gereedschap: T.gereedschap,
    gereedschap_gebruik: T.gereedschapGebruik,
    experiment_opzet: T.experimentOpzet,
    experiment_tempo: T.experimentTempo,
    tijdlijn: T.tijdlijn,
    titelwissel: T.titelwissel,

    neerslagstatistiek: neerslagstatistiek,
    droogtestatistiek: droogtestatistiek,
    frequentielijn: frequentielijn,
    kostencurve: kostencurve,
    topdown_nat_droog: topdownNatDroog,
    transitie_heen: transitiePaneel(false),
    transitie_terug: transitiePaneel(true),
    topdown_polder: topdownPolder,
    topdown_netwerk: topdownNetwerk,

    // Gewone taal, geen vaktermen uit de robotica. Een hydroloog weet niet wat
    // "starre lichamen en contact" of "MuJoCo" is, en hoeft dat ook niet te
    // weten om dit schema te snappen.
    wereldmodel_robot: wereldmodel({
      wie: "the microduck",
      icoon: ICOON_ROBOT,
      volgende: "the next state",
      // Niet "van lopen": in zijn oefenwereld skeelert en schommelt hij ook.
      transitie: "Physics Engine",
      policy: "chooses what it does at every step",
      actie1: "it turns its motors,",
      actie2: "fifty times a second",
      exogeen1: "the floor, the friction,",
      exogeen2: "its battery",
      beloning1: "moving forward,",
      beloning2: "and not falling over",
      doel: "goal: learn to walk",
    }),

    wereldmodel_polder: wereldmodel(POLDER),
    // Dezelfde vulling, maar de delen die uit staan zijn onzichtbaar in plaats
    // van gedempt. Eén vulling, twee weergaven - anders lopen ze uit elkaar.
    wereldmodel_polder_hard: wereldmodel(POLDER, true),

    // deel 0 = de gesloten lus, 1 = de doorrekening, 2 = wat exogeen is.
    // De s-doos staat BUITEN elk deel: hij is het onderwerp van alle drie de
    // beats, dus hij mag nooit wegvallen.
    transitie:
      '<svg viewBox="0 0 620 290" preserveAspectRatio="xMidYMid meet">' +
      '  <rect class="f-vlak" x="150" y="96" width="136" height="58" rx="7"/>' +
      '  <text class="f-tekst wis" x="218" y="122" text-anchor="middle">s</text>' +
      '  <text class="f-tekst klein" x="218" y="141" text-anchor="middle">de polder</text>' +
      /* Omlaag is apply, naar rechts is simulate, en de lus komt links als een
         boog terug. Eerder liep de retourpijl langs de vier randen van het vlak
         en las hij als een kader om de hele tekening in plaats van als een pijl. */
      '  <g class="f-deel aan" data-deel="0">' +
      '    <path class="f-accent" d="M218 154 L218 202"/>' +
      '    <path class="f-accent" d="M212 194 L218 204 L224 194"/>' +
      '    <text class="f-tekst klein" x="232" y="184">een maatregel</text>' +
      '    <rect class="f-vlak" x="150" y="204" width="136" height="58" rx="7"/>' +
      '    <text class="f-tekst wis" x="218" y="230" text-anchor="middle">s′</text>' +
      '    <text class="f-tekst klein" x="218" y="249" text-anchor="middle">zelfde type</text>' +
      '    <path class="f-accent" stroke-dasharray="6 5"' +
      '          d="M150 233 C 92 233, 92 125, 144 125"/>' +
      '    <path class="f-accent" d="M136 119 L146 125 L136 131"/>' +
      '    <text class="f-tekst sterk" x="80" y="174" text-anchor="end">terug te</text>' +
      '    <text class="f-tekst sterk" x="80" y="192" text-anchor="end">voeren</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-nat" d="M286 125 L352 125"/>' +
      '    <path class="f-nat" d="M344 119 L354 125 L344 131"/>' +
      '    <rect class="f-vlak" x="354" y="96" width="140" height="58" rx="7"/>' +
      '    <text class="f-tekst sterk" x="424" y="122" text-anchor="middle">de waterbalans</text>' +
      '    <text class="f-tekst klein" x="424" y="141" text-anchor="middle">in uurstappen</text>' +
      '    <path class="f-nat" d="M424 154 L424 176"/>' +
      '    <path class="f-nat" d="M418 168 L424 178 L430 168"/>' +
      '    <text class="f-tekst wis" x="424" y="200" text-anchor="middle">Δh</text>' +
      '    <text class="f-tekst klein" x="424" y="220" text-anchor="middle">een piekstand,</text>' +
      '    <text class="f-tekst klein" x="424" y="236" text-anchor="middle">geen toestand</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-lijn" stroke-dasharray="5 5" d="M218 42 L218 90"/>' +
      '    <path class="f-lijn" d="M212 82 L218 92 L224 82"/>' +
      '    <text class="f-tekst sterk" x="238" y="52">het weer — getrokken, niet gekozen</text>' +
      '    <text class="f-tekst klein" x="238" y="70">bui: uren · droogte: een groeiseizoen</text>' +
      '  </g>' +
      '</svg>',

    // ── tegenover een model met een andere onbekende ─────────────────────
    //
    // De vraag die bij dit publiek als eerste komt. Het antwoord is niet "wij
    // zijn beter" of "wij zijn sneller" maar: er ligt iets anders vast. Zet je
    // de polder vast en laat je het water bewegen, dan kun je vragen wat er
    // gebeurt. Zet je de bui vast en laat je de polder bewegen, dan kun je
    // vragen hoe de polder moet worden.
    //
    // De koppen noemen de RICHTING en niet een werkwoord. "Doorrekenen" zegt
    // niets - elk model rekent - en het laat open waaróp dan. Van ontwerp naar
    // gedrag tegenover van eis naar ontwerp zegt in vier woorden wat je erin
    // stopt en wat eruit komt, ook als je Ribasim niet kent.
    //
    // Delen: 0 = wat vastligt, 1 = wat beweegt, 2 = de vraag die eruit volgt.
    ribasim: kolommen(
      // ONZE kolom staat links. De plaat beantwoordt een vraag over ons werk -
      // waarom niet gewoon Ribasim - en dan hoort er eerst te staan wat wij doen
      // en daarnaast hoe Ribasim daarop aansluit. Andersom leest hij als een
      // vergelijking waarin wij de uitdager zijn.
      //
      // De naam hoort in de KOP en niet in de voetregel. Op een bevroren plaat
      // moet te zien zijn welke kolom welk model is; de spreker die "Ribasim"
      // zegt is er dan niet.
      ["ours: requirement \u2192 design", "rules of thumb with a price tag"],
      ["Ribasim: design \u2192 behaviour", "control rules, time series, structures"],
      [
        ["what is fixed", "the storm", "the polder"],
        ["what moves", "the polder itself", "the water"],
        ["so the question", "what should it become?", "what will happen?"],
      ]
    ),

    // ── wat een world model is ──────────────────────────────────────────
    //
    // De definitie rust op de ROL: dezelfde vraag, aan een andere wereld
    // gesteld. De herkomst staat alleen in de kop van elke kolom, want daar
    // verschillen ze en dat is niet wat het een world model maakt.
    //
    // Delen: 0 = de vraag, 1 = het antwoord, 2 = waarvoor.
    wereldmodel_rol: kolommen(
      ["in robotics", "a physics engine, or learned"],
      ["in a polder", "a water balance, written down"],
      [
        ["you ask", "what if I do this?", "what if we build this?"],
        ["it answers", "the next state", "the next polder"],
        ["you use it", "to try before the floor", "to try before the polder"],
      ]
    ),

    // ── grof voor fijn ──────────────────────────────────────────────────
    //
    // De volgorde waarin de twee soorten model elkaar aanvullen. Elke kolom
    // eindigt op de vraag die dat model beantwoordt.
    grof_fijn: lijsten(
      ["first: coarse and wide",
       "rules of thumb, thousands of runs",
       "every measure, in both directions",
       "tells you where to look"],
      ["then: fine and local",
       "Ribasim, D-HYDRO, wflow",
       "one design, the real geometry",
       "tells you whether it holds"]
    ),

    // ── de agent in het werk ────────────────────────────────────────────
    //
    // Wie verkent en wie beslist, zonder en met de agent ervoor. De rijen
    // staan tegenover elkaar: dezelfde drie momenten, twee keer.
    werkwijze: lijsten(
      ["today",
       "every question goes to the expert",
       "each \u201cwhat if\u201d waits its turn",
       "the real question surfaces late"],
      ["with the agent in front",
       "the asker explores, within limits",
       "each \u201cwhat if\u201d is one sentence",
       "the expert gets the sharp question"]
    ),

    // ── drie polders tegenover hun rapport ──────────────────────────────
    //
    // Per gebied één grootheid, met de rapportconclusie links en het antwoord
    // van de toolset rechts. De getallen komen uit de casusdeck.
    //
    // Delen: 0 = Gnephoek, 1 = Zuidplaspolder, 2 = Kockengen, 3 = de uitkomst.
    casussen: kolommen(
      ["the published study", "three polders, three reports"],
      ["our toolset", "the same question, asked by an agent"],
      [
        ["Gnephoek", "45 ha of open water", "2 ha more"],
        ["Zuidplaspolder", "84 cm rise", "152 cm rise"],
        ["Kockengen", "pump: 13 mm/day", "needed: 29 mm/day"],
      ],
      [
        "Next to a published study three times, equal to it in none.",
      ]
    ),

    // ── het slot ────────────────────────────────────────────────────────
    slot: lijsten(
      ["to take home",
       "try it in simulation first",
       "coarse and both ways, then detail",
       "agent translates, rules calculate"],
      ["what happens next",
       "two students: the 2026 drought",
       "Dec 2026: Digishape, the evaluation",
       "open source: come and break it"]
    ),

    // ── de grenzen ──────────────────────────────────────────────────────
    //
    // Alles hier staat ergens in de repo als caveat of als open punt. Op één
    // plaat bij elkaar is het een uitspraak in plaats van een verzameling
    // voetnoten, en dat is wat een zaal ervan moet meenemen.
    grenzen: lijsten(
      ["where it holds",
       "which measure comes before which",
       "what a package costs, with a band",
       "one polder, one storm, exactly",
       "thousands of times in a row"],
      ["where it breaks",
       "a node is an area, not a map",
       "level and supply have no price",
       "the avoided damage is missing",
       "the soil numbers are indicative"]
    ),

    // ── wat de agent doet ───────────────────────────────────────────────
    //
    // De eerlijke uitspraak staat onderaan en niet als bijzin: het taalmodel
    // rekent niet. Het kiest een vuistregel, vult hem, en leest terug wat er
    // uit komt - inclusief de aannames, want die staan in het antwoord van de
    // tool en niet in het hoofd van het model.
    //
    // Delen: 0 = de vraag en de agent, 1 = de vuistregels eronder,
    //        2 = het antwoord terug, 3 = wat het model NIET doet.
    agent:
      '<svg viewBox="0 0 660 320" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <text class="f-tekst klein" x="16" y="30">someone asks, in plain language</text>' +
      '    <rect class="f-vlak" x="16" y="42" width="196" height="62" rx="7"/>' +
      '    <text class="f-tekst sterk" x="114" y="68" text-anchor="middle">"thirty centimetres</text>' +
      '    <text class="f-tekst sterk" x="114" y="88" text-anchor="middle">lower \u2014 how?"</text>' +
      '    <path class="f-accent" d="M212 73 L268 73"/>' +
      '    <path class="f-accent" d="M260 67 L270 73 L260 79"/>' +
      '    <rect class="f-vlak" x="270" y="42" width="150" height="62" rx="7"/>' +
      '    <text class="f-tekst sterk accent" x="345" y="68" text-anchor="middle">the agent</text>' +
      '    <text class="f-tekst klein" x="345" y="88" text-anchor="middle">picks and fills in</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-accent" d="M345 104 L345 148"/>' +
      '    <path class="f-accent" d="M339 140 L345 150 L351 140"/>' +
      '    <rect class="f-vlak" x="240" y="150" width="210" height="66" rx="7"/>' +
      '    <text class="f-tekst sterk" x="345" y="176" text-anchor="middle">the rules of thumb</text>' +
      '    <text class="f-tekst klein" x="345" y="196" text-anchor="middle">exact, the same on every machine</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-nat" d="M450 183 L512 183"/>' +
      '    <path class="f-nat" d="M504 177 L514 183 L504 189"/>' +
      '    <rect class="f-vlak" x="514" y="150" width="130" height="66" rx="7"/>' +
      '    <text class="f-tekst sterk" x="579" y="176" text-anchor="middle">the answer</text>' +
      '    <text class="f-tekst klein" x="579" y="196" text-anchor="middle">with its assumptions</text>' +
      '    <path class="f-nat" stroke-dasharray="6 5" d="M579 216 C 579 268, 114 268, 114 110"/>' +
      '    <path class="f-nat" d="M108 122 L114 108 L120 122"/>' +
      '    <text class="f-tekst klein" x="346" y="284" text-anchor="middle">and back in plain language</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="3">' +
      '    <text class="f-tekst sterk nadruk" x="446" y="52">the language model</text>' +
      '    <text class="f-tekst sterk nadruk" x="446" y="72">does not calculate \u2014</text>' +
      '    <text class="f-tekst sterk nadruk" x="446" y="92">it translates</text>' +
      '    <text class="f-tekst klein" x="446" y="114">its mistakes are in the</text>' +
      '    <text class="f-tekst klein" x="446" y="130">question it passes on</text>' +
      '  </g>' +
      '</svg>',

    // ── de pakketvraag, met wat er terugkomt ────────────────────────────
    //
    // De opmaat en de nazit van de live demo, op dezelfde polder als de rest
    // van de deck. De vraag is er ÉÉN - achttien centimeter - want twee eisen
    // erbij verklaren kost meer tijd dan het antwoord waard is.
    //
    // Wat de zaal moet vasthouden staat op deel 2: binnen de band werkt ook een
    // heel ander pakket. Het gemaal zit in elk even goed pakket, de retentie in
    // sommige - en welke van die twee je kiest, is niet aan ons.
    //
    // Delen 3 en 4 lopen de andere kant op: dezelfde eis, een andere bedreiging.
    // Ze delen de onderste helft met deel 2 en niet met elkaar, want in `f-hard`
    // zijn de delen alternatieven - de beat wisselt de inhoud van dat vlak en
    // stapelt hem niet. De getallen komen uit `scripts/gen_voorkeursvolgorde.py`.
    pakketvraag:
      '<svg viewBox="0 0 660 300" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <text class="f-tekst klein" x="16" y="30">the question</text>' +
      '    <rect class="f-vlak" x="16" y="42" width="252" height="64" rx="7"/>' +
      '    <text class="f-tekst sterk" x="36" y="82">the peak below 18 cm</text>' +
      '    <text class="f-tekst klein" x="16" y="128">the same polder of a thousand hectares</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-accent" d="M268 74 L324 74"/>' +
      '    <path class="f-accent" d="M316 68 L326 74 L316 80"/>' +
      '    <rect class="f-vlak" x="326" y="42" width="318" height="64" rx="7"/>' +
      '    <text class="f-tekst sterk accent" x="346" y="70">retain 114 ha</text>' +
      '    <text class="f-tekst sterk accent" x="346" y="94">and discharge 0.34 m\u00b3/s</text>' +
      '    <text class="f-tekst klein" x="326" y="128">\u20ac 0.92 mln \u2014 band \u20ac 0.77 to 1.03</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-lijn" d="M16 164 L644 164"/>' +
      '    <text class="f-tekst" x="16" y="198">and inside that band this works too:</text>' +
      '    <text class="f-tekst sterk derde" x="16" y="228">a bigger pumping station alone, 0.5 m\u00b3/s, for four percent more</text>' +
      '    <text class="f-tekst sterk nadruk" x="16" y="264">the pump is a must. Retention is a choice \u2014 and not ours</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="3">' +
      '    <path class="f-lijn" d="M16 164 L644 164"/>' +
      '    <text class="f-tekst" x="16" y="198">and the same question for a heavier storm:</text>' +
      '    <text class="f-tekst sterk derde" x="16" y="228">once in 25 years \u2014 a pumping station alone, 0.91 m\u00b3/s</text>' +
      '    <text class="f-tekst sterk accent" x="16" y="258">once a century \u2014 retain 263 ha as well, pump 1.02</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="4">' +
      '    <path class="f-lijn" d="M16 164 L644 164"/>' +
      '    <text class="f-tekst" x="16" y="198">and across everything the statistics can draw:</text>' +
      '    <text class="f-tekst sterk accent" x="16" y="228">the pump in 212 of the 216 packages, retention in 140</text>' +
      '    <text class="f-tekst sterk nadruk" x="16" y="264">one is a must, the other a choice \u2014 that is the ordering</text>' +
      '  </g>' +
      '</svg>',

    // deel 0 = het risico zonder maatregelen, 1 = de zaagtand, 2 = de korting.
    // De as en de norm staan buiten de delen: de norm is de eis waar het hele
    // plaatje over gaat, en die hoort er vanaf de eerste beat te staan.
    zaagtand:
      '<svg viewBox="0 0 620 320" preserveAspectRatio="xMidYMid meet">' +
      '  <path class="f-lijn" d="M62 250 L596 250"/>' +
      '  <path class="f-lijn" d="M62 28 L62 250"/>' +
      '  <text class="f-tekst klein" x="62" y="266">2026</text>' +
      '  <text class="f-tekst klein" x="596" y="266" text-anchor="end">2100</text>' +
      '  <text class="f-tekst klein" x="62" y="20">risk</text>' +
      '  <path class="f-lijn" stroke-dasharray="7 5" d="M62 152 L596 152"/>' +
      '  <text class="f-tekst sterk" x="596" y="145" text-anchor="end">the standard</text>' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <path class="f-lijn" stroke-dasharray="4 4" d="M62 206 L596 62"/>' +
      '    <text class="f-tekst klein" x="470" y="86">without measures:</text>' +
      '    <text class="f-tekst klein" x="470" y="102">climate and subsidence</text>' +
      '  </g>' +
      /* De maatregelnamen staan BOVEN hun sprong. Onder de sprong liepen ze door
         de discontokromme heen, en dan las "peilopzet" als een label bij γ. */
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-accent" d="M62 206 L188 172 L188 216 L316 181.5' +
      '      L316 227.5 L444 193 L444 239 L596 198"/>' +
      '    <g class="f-tekst klein">' +
      '      <text x="188" y="164" text-anchor="middle">store</text>' +
      '      <text x="316" y="173" text-anchor="middle">discharge</text>' +
      '      <text x="444" y="185" text-anchor="middle">raised level</text>' +
      '    </g>' +
      '  </g>' +
      /* De korting krijgt zijn eigen band ONDER de tijdas. In het vlak zelf
         kruiste hij de zaagtand en suggereerde hij hetzelfde soort grootheid. */
      '  <g class="f-deel" data-deel="2">' +
      '    <text class="f-tekst klein" x="62" y="288">postponing makes the investment cheaper</text>' +
      '    <path class="f-droog" stroke-dasharray="3 4" d="M62 300 C 230 306, 400 312, 596 314"/>' +
      '  </g>' +
      '</svg>',
  };

  // ── wat dit bestand levert ────────────────────────────────────────────────
  T.FIGUREN = FIGUREN;
})(TEKEN);
