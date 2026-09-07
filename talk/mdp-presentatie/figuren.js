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
      wie: "de microduck",
      icoon: ICOON_ROBOT,
      volgende: "de volgende stand",
      // Niet "van lopen": in zijn oefenwereld skeelert en schommelt hij ook.
      transitie: "Physics Engine",
      policy: "kiest elke stap wat hij doet",
      actie1: "hij draait zijn motoren,",
      actie2: "vijftig keer per seconde",
      exogeen1: "de vloer, de wrijving,",
      exogeen2: "zijn batterij",
      beloning1: "vooruit komen,",
      beloning2: "en niet omvallen",
      doel: "doel: leer lopen",
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
    // Delen: 1 = wat vastligt, 2 = wat beweegt, 3 = de vraag die eruit volgt.
    ribasim: kolommen(
      // ONZE kolom staat links. De plaat beantwoordt een vraag over ons werk -
      // waarom niet gewoon Ribasim - en dan hoort er eerst te staan wat wij doen
      // en daarnaast hoe Ribasim daarop aansluit. Andersom leest hij als een
      // vergelijking waarin wij de uitdager zijn.
      //
      // De naam hoort in de KOP en niet in de voetregel. Op een bevroren plaat
      // moet te zien zijn welke kolom welk model is; de spreker die "Ribasim"
      // zegt is er dan niet.
      ["het onze: van eis naar ontwerp", "vuistregels met een prijs eraan"],
      ["Ribasim: van ontwerp naar gedrag", "regelregels, tijdreeksen, kunstwerken"],
      [
        ["wat vastligt", "de bui", "de polder"],
        ["wat beweegt", "de polder zelf", "het water"],
        ["dus de vraag", "hoe moet het worden?", "wat gebeurt er?"],
      ],
      // En dan wat de twee werkelijk oplossen, in woorden die een zaal volgt.
      // Ribasim integreert een stelsel eerste-orde ODE's - du/dt = f(u, p(t), t)
      // met OrdinaryDiffEq.jl - en doet dat IMPLICIET: per tijdstap staat er een
      // gekoppeld stelsel voor alle bekkens samen, precies zodat bekkens binnen
      // die stap informatie uitwisselen. Zie ribasim.org/concept/numerics.html.
      // De twee voetregels lossen DEZELFDE vergelijking op en verschillen alleen
      // in het lid dat eruit moet komen. Dat is het idioom van de twee beats
      // hiervoor, een verdieping hoger: bij T stond de ring om de stand en bij
      // T⁻¹ om de maatregel, en hier staat hetzelfde tussen twee modellen.
      //
      // "Het hele netwerk in één keer" stond er eerst, en dat is geen verschil:
      // wij willen juist ook het hele netwerk in één keer - alleen weten we dan
      // welke maatregel er in elke knoop moet, en dat is niet wat Ribasim geeft.
      //
      // Bij ons is de transitie h[t] = klem(h[t-1] + Δ[t]): een lopende optelsom
      // met een klem, op een vaste uurstap. "Differentiaalvergelijking tegenover
      // verschilvergelijking" is precies hetzelfde onderscheid, maar dat leest
      // niemand van een scherm - en de zaal moet het in één keer volgen.
      //
      // Dat verschil is niet cosmetisch: een optelsom met een klem is per stap
      // in gesloten vorm te schrijven, en dan is de weg terug naar de maatregel
      // een rekensom in plaats van een zoektocht. Vandaar de tweede regel.
      [
        "Wij lossen de waterbalans naar de maatregel toe: een world model om te ontwerpen.",
        "Ribasim lost de waterbalans naar de standen en debieten toe: een world model voor gedrag.",
      ]
    ),

    // ── de grenzen ──────────────────────────────────────────────────────
    //
    // Alles hier staat ergens in de repo als caveat of als open punt. Op één
    // plaat bij elkaar is het een uitspraak in plaats van een verzameling
    // voetnoten, en dat is wat een zaal ervan moet meenemen.
    grenzen: lijsten(
      ["waar het houdt",
       "welke maatregel v\u00f3\u00f3r welke gaat",
       "wat een pakket kost, met een band",
       "\u00e9\u00e9n polder, \u00e9\u00e9n bui, exact",
       "duizenden keren achter elkaar"],
      ["waar het breekt",
       "een knoop is oppervlak, geen kaart",
       "peil en aanvoer hebben geen prijs",
       "de vermeden schade ontbreekt",
       "de bodemgetallen zijn indicatief"]
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
      '    <text class="f-tekst klein" x="16" y="30">iemand vraagt, in gewone taal</text>' +
      '    <rect class="f-vlak" x="16" y="42" width="196" height="62" rx="7"/>' +
      '    <text class="f-tekst sterk" x="114" y="68" text-anchor="middle">"dertig centimeter</text>' +
      '    <text class="f-tekst sterk" x="114" y="88" text-anchor="middle">lager \u2014 hoe?"</text>' +
      '    <path class="f-accent" d="M212 73 L268 73"/>' +
      '    <path class="f-accent" d="M260 67 L270 73 L260 79"/>' +
      '    <rect class="f-vlak" x="270" y="42" width="150" height="62" rx="7"/>' +
      '    <text class="f-tekst sterk accent" x="345" y="68" text-anchor="middle">de agent</text>' +
      '    <text class="f-tekst klein" x="345" y="88" text-anchor="middle">kiest en vult in</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-accent" d="M345 104 L345 148"/>' +
      '    <path class="f-accent" d="M339 140 L345 150 L351 140"/>' +
      '    <rect class="f-vlak" x="240" y="150" width="210" height="66" rx="7"/>' +
      '    <text class="f-tekst sterk" x="345" y="176" text-anchor="middle">de vuistregels</text>' +
      '    <text class="f-tekst klein" x="345" y="196" text-anchor="middle">exact, en op elke machine gelijk</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-nat" d="M450 183 L512 183"/>' +
      '    <path class="f-nat" d="M504 177 L514 183 L504 189"/>' +
      '    <rect class="f-vlak" x="514" y="150" width="130" height="66" rx="7"/>' +
      '    <text class="f-tekst sterk" x="579" y="176" text-anchor="middle">het antwoord</text>' +
      '    <text class="f-tekst klein" x="579" y="196" text-anchor="middle">met zijn aannames</text>' +
      '    <path class="f-nat" stroke-dasharray="6 5" d="M579 216 C 579 268, 114 268, 114 110"/>' +
      '    <path class="f-nat" d="M108 122 L114 108 L120 122"/>' +
      '    <text class="f-tekst klein" x="346" y="284" text-anchor="middle">en terug in gewone taal</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="3">' +
      '    <text class="f-tekst sterk nadruk" x="16" y="150">het taalmodel</text>' +
      '    <text class="f-tekst sterk nadruk" x="16" y="170">rekent niet \u2014</text>' +
      '    <text class="f-tekst sterk nadruk" x="16" y="190">het vertaalt</text>' +
      '    <text class="f-tekst klein" x="16" y="214">geen getal komt</text>' +
      '    <text class="f-tekst klein" x="16" y="232">uit het model zelf</text>' +
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
      '    <text class="f-tekst klein" x="16" y="30">de vraag</text>' +
      '    <rect class="f-vlak" x="16" y="42" width="252" height="64" rx="7"/>' +
      '    <text class="f-tekst sterk" x="36" y="82">de piek onder 18 cm</text>' +
      '    <text class="f-tekst klein" x="16" y="128">dezelfde polder van duizend hectare</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-accent" d="M268 74 L324 74"/>' +
      '    <path class="f-accent" d="M316 68 L326 74 L316 80"/>' +
      '    <rect class="f-vlak" x="326" y="42" width="318" height="64" rx="7"/>' +
      '    <text class="f-tekst sterk accent" x="346" y="70">vasthouden 114 ha</text>' +
      '    <text class="f-tekst sterk accent" x="346" y="94">en afvoeren 0,34 m\u00b3/s</text>' +
      '    <text class="f-tekst klein" x="326" y="128">\u20ac 0,92 mln \u2014 band \u20ac 0,77 tot 1,03</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-lijn" d="M16 164 L644 164"/>' +
      '    <text class="f-tekst" x="16" y="198">en binnen die band kan het ook zo:</text>' +
      '    <text class="f-tekst sterk derde" x="16" y="228">alleen een groter gemaal, 0,5 m\u00b3/s, voor vier procent meer</text>' +
      '    <text class="f-tekst sterk nadruk" x="16" y="264">het gemaal moet. De retentie is een keuze \u2014 en niet de onze</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="3">' +
      '    <path class="f-lijn" d="M16 164 L644 164"/>' +
      '    <text class="f-tekst" x="16" y="198">en dezelfde vraag bij een zwaardere bui:</text>' +
      '    <text class="f-tekst sterk derde" x="16" y="228">eens per 25 jaar \u2014 alleen een gemaal, 0,91 m\u00b3/s</text>' +
      '    <text class="f-tekst sterk accent" x="16" y="258">eens per eeuw \u2014 vasthouden 263 ha erbij, gemaal 1,02</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="4">' +
      '    <path class="f-lijn" d="M16 164 L644 164"/>' +
      '    <text class="f-tekst" x="16" y="198">en over alles wat de statistiek kan trekken:</text>' +
      '    <text class="f-tekst sterk accent" x="16" y="228">het gemaal in 212 van de 216 pakketten, vasthouden in 140</text>' +
      '    <text class="f-tekst sterk nadruk" x="16" y="264">de een moet altijd, de ander is een keuze \u2014 dat is de volgorde</text>' +
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
      '  <text class="f-tekst klein" x="62" y="20">risico</text>' +
      '  <path class="f-lijn" stroke-dasharray="7 5" d="M62 152 L596 152"/>' +
      '  <text class="f-tekst sterk" x="596" y="145" text-anchor="end">de norm</text>' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <path class="f-lijn" stroke-dasharray="4 4" d="M62 206 L596 62"/>' +
      '    <text class="f-tekst klein" x="470" y="86">zonder maatregelen:</text>' +
      '    <text class="f-tekst klein" x="470" y="102">klimaat en bodemdaling</text>' +
      '  </g>' +
      /* De maatregelnamen staan BOVEN hun sprong. Onder de sprong liepen ze door
         de discontokromme heen, en dan las "peilopzet" als een label bij γ. */
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-accent" d="M62 206 L188 172 L188 216 L316 181.5' +
      '      L316 227.5 L444 193 L444 239 L596 198"/>' +
      '    <g class="f-tekst klein">' +
      '      <text x="188" y="164" text-anchor="middle">bergen</text>' +
      '      <text x="316" y="173" text-anchor="middle">afvoeren</text>' +
      '      <text x="444" y="185" text-anchor="middle">peilopzet</text>' +
      '    </g>' +
      '  </g>' +
      /* De korting krijgt zijn eigen band ONDER de tijdas. In het vlak zelf
         kruiste hij de zaagtand en suggereerde hij hetzelfde soort grootheid. */
      '  <g class="f-deel" data-deel="2">' +
      '    <text class="f-tekst klein" x="62" y="288">uitstellen maakt de investering goedkoper</text>' +
      '    <path class="f-droog" stroke-dasharray="3 4" d="M62 300 C 230 306, 400 312, 596 314"/>' +
      '  </g>' +
      '</svg>',
  };

  // ── wat dit bestand levert ────────────────────────────────────────────────
  T.FIGUREN = FIGUREN;
})(TEKEN);
