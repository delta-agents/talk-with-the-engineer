// ═══════════════════════════════════════════════════════════════════════════
// Het schema: het world model, en de transitie in twee richtingen.
// ═══════════════════════════════════════════════════════════════════════════
//
// De twee grote tekeningen van de talk staan hier, en ze staan hier SAMEN omdat
// ze elkaars maten dragen: de transitiepanelen hebben dezelfde viewBox als
// `wereldmodel`, zodat de ene tekening één op één op de andere valt en er bij de
// wissel niets verspringt.
//
// `POLDER` is de vulling van het schema voor onze kant. Hij staat één keer
// opgeschreven en wordt twee keer getekend — gedempt bij ⟳, hard bij π.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  var ICOON_POLDER = T.ICOON_POLDER;

  // ── twee richtingen op dezelfde vuistregel ───────────────────────────────
  //

  // Het schema van een world model: ÉÉN tekening, twee vullingen.
  //
  // Dat is geen zuinigheid maar de claim van de talk. Het schema blijft staan
  // en alleen wat erin staat wisselt van de microduck naar de polder; twee
  // losse SVG's zouden uit elkaar kunnen lopen en dan is die claim niet meer
  // waar te maken op het scherm.
  //
  // De symbolen op de pijlen zijn dezelfde als de leden van de tuple erna:
  // wie dit schema begrijpt, kent `a`, `e` en `s′` al voordat ze een eigen stap
  // krijgen.
  //
  // De lus loopt RECHTHOEKIG om de twee dozen heen: de maatregel gaat links
  // omhoog naar binnen, de volgende toestand komt rechts naar buiten en zakt
  // daar weer af naar wie kiest. Zo kruist geen lijn een letter - eerder liep
  // de teruglus dwars door "de volgende polder" en door de beloning, en de
  // pijl naar de maatregel dwars door zijn eigen label.
  //
  // Wat bij welk deel hoort, is niet cosmetisch. Deel 0 is de VOLLEDIGE
  // transitie: de maatregel is een INGANG en moet dus blijven staan als de
  // policy weg is. De policy trekt alleen de lijnen door en sluit de lus.
  //
  // Delen: 0 = de transitie met alles wat erin en eruit gaat,
  // 1 = de policy en de lus die hem sluit, 2 = de beloning en het leren,
  // 3 = de ring om het weer, 4 = de ring om de maatregel.
  //
  // Die twee ringen zetten de tekening op het standpunt van de strateeg. Het
  // idioom is dat van `transitiePaneel`: een ring markeert wat je NIET weet. Hier
  // zijn het twee soorten niet-weten, en daarom twee delen die apart aangaan -
  // het weer kun je niet kiezen, de maatregel wel maar je weet niet hoe hij
  // uitpakt. Ze staan om de LETTER en niet om het bijschrift, want het gaat om
  // het lid van de transitie en niet om het voorbeeld eronder.
  //
  // `hard` maakt de delen die uit staan onzichtbaar in plaats van gedempt.
  // Dat is wat je wilt op de beat die zegt "dit hoort er níet bij".
  function wereldmodel(v, hard) {
    // Het kader is aan beide kanten ruimer dan de tekening: links loopt het
    // bijschrift bij de maatregel end-anchored van x=138 af naar buiten, rechts
    // staat "en wat dat mag kosten" tegen de rand. Marge is hier goedkoper dan
    // een regel die op één schermmaat net wel en op een andere net niet past.
    return '<svg viewBox="-30 0 790 418" preserveAspectRatio="xMidYMid meet"' +
        (hard ? ' class="f-hard"' : '') + '>' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <text class="f-tekst klein" x="210" y="88">the transition of ' + v.wie + '</text>' +
      '    <rect class="f-vlak" x="210" y="96" width="250" height="78" rx="7"/>' +
      // De naam staat midden in de doos, en hij is in beide vullingen even lang
      // opgebouwd: wat er draait, en waarmee. Dat is het hele punt van de wissel.
      '    <text class="f-tekst sterk" x="335" y="140" text-anchor="middle">' +
        v.transitie + '</text>' +
      // de maatregel gaat erin, links
      '    <path class="f-accent" d="M150 135 L204 135"/>' +
      '    <path class="f-accent" d="M196 129 L206 135 L196 141"/>' +
      '    <text class="f-tekst wis" x="138" y="118" text-anchor="end">a</text>' +
      '    <text class="f-tekst klein" x="138" y="138" text-anchor="end">' + v.actie1 + '</text>' +
      '    <text class="f-tekst klein" x="138" y="154" text-anchor="end">' + v.actie2 + '</text>' +
      // het weer komt van boven
      '    <path class="f-lijn" stroke-dasharray="5 5" d="M420 44 L420 88"/>' +
      '    <path class="f-lijn" d="M414 80 L420 90 L426 80"/>' +
      '    <text class="f-tekst wis" x="405" y="58" text-anchor="end">e</text>' +
      '    <text class="f-tekst klein" x="436" y="52">' + v.exogeen1 + '</text>' +
      '    <text class="f-tekst klein" x="436" y="68">' + v.exogeen2 + '</text>' +
      // en de volgende toestand komt eruit, rechts
      '    <path class="f-accent" d="M460 135 L560 135"/>' +
      '    <path class="f-accent" d="M552 129 L562 135 L552 141"/>' +
      '    <text class="f-tekst wis" x="574" y="130">s′</text>' +
      '    <text class="f-tekst klein" x="574" y="150">' + v.volgende + '</text>' +
      '  </g>' +
      // De lus takt AF van de pijl van de volgende toestand - vandaar het
      // knooppunt - zakt af langs de doos en gaat er links weer omhoog in.
      '  <g class="f-deel" data-deel="1">' +
      '    <circle class="f-knoop" cx="512" cy="135" r="3.5"/>' +
      '    <path class="f-accent" d="M512 135 L512 266 L466 266"/>' +
      '    <path class="f-accent" d="M474 260 L464 266 L474 272"/>' +
      '    <rect class="f-vlak" x="210" y="240" width="250" height="52" rx="7"/>' +
      '    <text class="f-tekst sterk" x="335" y="262" text-anchor="middle">the policy</text>' +
      '    <text class="f-tekst klein" x="335" y="280" text-anchor="middle">' + v.policy + '</text>' +
      '    <path class="f-accent" d="M210 266 L150 266 L150 135"/>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <text class="f-tekst klein" x="574" y="182">and the reward:</text>' +
      '    <text class="f-tekst klein" x="574" y="198">' + v.beloning1 + '</text>' +
      '    <text class="f-tekst klein" x="574" y="214">' + v.beloning2 + '</text>' +
      '    <path class="f-droog" stroke-dasharray="4 4" d="M335 292 L335 308"/>' +
      '    <path class="f-droog" d="M329 300 L335 310 L341 300"/>' +
      '    <text class="f-tekst sterk" x="335" y="328" text-anchor="middle">' + v.doel + '</text>' +
      '  </g>' +
      // De ringen. Middelpunt en straal staan om de letter zelf: `e` staat met
      // zijn anker rechts op (405, 58) en `a` op (138, 118), dus het teken zit
      // links van die x en boven die y.
      '  <g class="f-deel" data-deel="3">' +
      '    <circle class="i-bindend" cx="400" cy="52" r="15"/>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="4">' +
      '    <circle class="i-bindend" cx="133" cy="112" r="15"/>' +
      '  </g>' +
      // Het plaatje in de vrije hoek staat BUITEN elk deel: het zegt waar dit
      // schema over gaat, en dat geldt op elke beat.
      (v.icoon || "") +
      '</svg>';
  }

  // ── de transitie, en dezelfde transitie achterstevoren ───────────────────
  //
  // Twee platen uit één bouwer, want ze moeten tot op de eenheid over elkaar
  // vallen: alleen de PIJLEN draaien om, en de ring verspringt van het ene
  // onbekende naar het andere. Twee losse tekeningen zouden dat niet volhouden.
  //
  // Boven het schema met een uitgerekend voorbeeld erin, onder dezelfde kromme
  // twee keer gelezen. Heen loop je van de x-as omhoog naar de y-as: geef de
  // maatregel, lees de stand. Terug loop je van de y-as naar rechts en omlaag:
  // geef de stand, lees de maatregel. Dat de tweede richting kán, is de hele
  // reden dat dit model bestaat.
  //
  // Er stond eerder "de rode ring staat om wat je niet weet" onder de plaat.
  // Met de getallen erbij is die zin overbodig: op de ene beat staat er een maat
  // bij de maatregel en een vraagteken bij de stand, op de andere andersom.
  //
  // De kromme en de twee lezingen zijn GEGENEREERD met
  // scripts/gen_tweerichting.py - niet met de hand bijwerken.
  var KROMME =
    "M85.0 282.1 L97.7 286.9 L110.3 291.4 L123.0 295.5 L135.7 299.4" +
    " L148.4 303.0 L161.1 306.4 L173.7 309.6 L186.4 312.6 L199.1 315.4" +
    " L211.8 318.0 L224.4 320.5 L237.1 322.9 L249.8 325.1 L262.4 327.2" +
    " L275.1 329.3 L287.8 331.2 L300.5 333.0 L313.1 334.8 L325.8 336.4" +
    " L338.5 338.0 L351.2 339.5 L363.9 341.0 L376.5 342.4 L389.2 343.7" +
    " L401.9 345.0 L414.6 346.2 L427.2 347.4 L439.9 348.6 L452.6 349.7" +
    " L465.2 350.7 L477.9 351.7 L490.6 352.7 L503.3 353.7 L516.0 354.6" +
    " L528.6 355.5 L541.3 356.3 L554.0 357.2 L566.6 358.0 L579.3 358.8" +
    " L592.0 359.5";
  var KAAL_Y = 282.1;   // de piek zonder maatregel

  function transitiePaneel(terug) {
    var tint = terug ? "droog" : "nat";
    var pijl = terug ? "f-droog" : "f-accent";
    // de twee uitgerekende lezingen: waar de knik ligt, en hoeveel lager dat is
    var kx = terug ? 148.2 : 338.5;
    var ky = terug ? 303.0 : 338.0;
    var lager = terug ? "6 cm lower" : "16 cm lower";
    // Vet staat op het ANTWOORD, en dat is aan elke kant een ander getal: heen
    // vraag je om de verlaging, terug om de maatvoering.
    var vet = terug ? "sterk droog" : "";
    var mager = terug ? "" : "nat";

    // De viewBox is even BREED als die van `wereldmodel`, en dat is de reden dat
    // het schema hieronder op precies dezelfde plek staat als bij ⟳ en π: beide
    // platen worden op hun breedte uitgetekend, dus dezelfde eenheid is
    // dezelfde pixel. Hoger mag hij wel zijn - deze beats dragen geen bronregel,
    // dus er is ruimte onder, en die gaat naar lucht om de vraag heen.
    var t = '<svg viewBox="-30 0 790 460" preserveAspectRatio="xMidYMid meet">';

    // ── boven: het schema, met de maten van `wereldmodel` ────────────────
    t += '<text class="f-tekst klein" x="210" y="88">the transition of the polder</text>' +
         '<rect class="f-vlak" x="210" y="96" width="250" height="78" rx="7"/>' +
         '<text class="f-tekst sterk" x="335" y="140" text-anchor="middle">Water Balance Engine</text>';

    // het weer komt van boven, en dat draait niet om
    t += '<path class="f-lijn" stroke-dasharray="5 5" d="M420 44 L420 88"/>' +
         '<path class="f-lijn" d="M414 80 L420 90 L426 80"/>' +
         '<text class="f-tekst wis" x="405" y="58" text-anchor="end">e</text>' +
         '<text class="f-tekst klein" x="436" y="52">the same storm,</text>' +
         '<text class="f-tekst klein" x="436" y="68">once in ten years</text>';

    // Links de maatregel, rechts de stand. Heen wijzen beide pijlen naar rechts;
    // terug wijzen ze allebei naar links, want dan is de maatregel het antwoord
    // en de stand de vraag.
    t += terug
      ? '<path class="' + pijl + '" d="M204 135 L152 135"/>' +
        '<path class="' + pijl + '" d="M160 129 L150 135 L160 141"/>' +
        '<path class="' + pijl + '" d="M560 135 L466 135"/>' +
        '<path class="' + pijl + '" d="M474 129 L464 135 L474 141"/>'
      : '<path class="' + pijl + '" d="M150 135 L204 135"/>' +
        '<path class="' + pijl + '" d="M196 129 L206 135 L196 141"/>' +
        '<path class="' + pijl + '" d="M460 135 L560 135"/>' +
        '<path class="' + pijl + '" d="M552 129 L562 135 L552 141"/>';

    t += '<text class="f-tekst wis" x="138" y="118" text-anchor="end">a</text>' +
         '<text class="f-tekst klein" x="138" y="138" text-anchor="end">store</text>' +
         '<text class="f-tekst sterk ' + (terug ? "droog" : "") +
           '" x="138" y="156" text-anchor="end">' +
           (terug ? "+10 hectares" : "+40 hectares") + '</text>' +
         '<text class="f-tekst wis" x="574" y="130">s′</text>' +
         (terug
           ? '<text class="f-tekst klein" x="574" y="150">keep the level</text>' +
             '<text class="f-tekst klein" x="574" y="168">below the standard</text>'
           : '<text class="f-tekst klein" x="574" y="150">ΔH</text>');

    // De ring staat om het lid dat je NIET weet, met het vraagteken aan de
    // buitenkant ernaast. De ring om `a` staat op dezelfde plek als die bij ⟳.
    t += terug
      ? '<circle class="i-bindend" cx="133" cy="112" r="15"/>' +
        '<text class="f-tekst wis nadruk" x="108" y="107" text-anchor="end">?</text>'
      : '<circle class="i-bindend" cx="582" cy="123" r="16"/>' +
        '<text class="f-tekst wis nadruk" x="606" y="118">?</text>';

    // ── de vraag, gecentreerd op de plaat ────────────────────────────────
    // De zin van de rekenkern zelf - de docstring van `calculate_store_given_area`
    // en van `calculate_store_given_h` - met deze maat ingevuld.
    t += '<text class="f-tekst sterk" x="365" y="224" text-anchor="middle">' +
         (terug
           ? "How much open water keeps the peak below the standard?"
           : "With 40 hectares of extra open water — how much lower is the peak?") +
         '</text>';

    // ── onder: dezelfde kromme, twee keer gelezen ────────────────────────
    // Het kader staat op 85..592, en dat is geen willekeur: op het scherm valt
    // het samen met de statistiekplaat bij E, die van 96 tot 520 loopt in een
    // viewBox van 660. De astitels staan waar ze daar ook staan.
    t += '<path class="f-lijn" d="M85 408 L592 408"/>' +
         '<path class="f-lijn" d="M85 268 L85 408"/>' +
         // de stand zonder maatregel: het gaat niet om dat getal maar om hoever
         // de kromme er onder duikt
         '<path class="f-lijn" stroke-dasharray="4 5" d="M85 ' + KAAL_Y +
           ' L592 ' + KAAL_Y + '"/>' +
         '<text class="f-tekst klein" x="588" y="' + (KAAL_Y - 8) +
           '" text-anchor="end">without a measure</text>' +
         '<path class="c-lijn ' + tint + '" d="' + KROMME + '"/>' +
         '<text class="f-tekst klein" x="85" y="258">rise in water level ↑</text>' +
         '<text class="f-tekst klein" x="338" y="442" text-anchor="middle">extra hectares of open water →</text>';

    // de lezing: heen van de x-as omhoog, terug van de y-as naar rechts
    t += '<path class="' + pijl + '" stroke-dasharray="6 4" d="' +
           (terug
             ? "M85 " + ky + " L" + kx + " " + ky + " L" + kx + " 408"
             : "M" + kx + " 408 L" + kx + " " + ky + " L85 " + ky) + '"/>' +
         '<circle class="c-optimum" cx="' + kx + '" cy="' + ky + '" r="6"/>' +
         '<text class="f-tekst ' + vet + '" x="' + kx +
           '" y="426" text-anchor="middle">' + (terug ? "10 ha" : "40 ha") + '</text>' +
         '<text class="f-tekst ' + mager + '" x="77" y="' + (ky + 5) +
           '" text-anchor="end">' + (terug ? "30 cm" : "20 cm") + '</text>';

    // En waar het werkelijk om gaat: hoeveel LAGER dat is. De maatlat staat
    // rechts van de aflezing, tussen de kale stand en de gehaalde stand.
    // Eindstreepjes en geen pijlpunten: bij zes centimeter is de maatlat maar
    // twintig eenheden lang, en dan lopen twee pijlpunten door elkaar heen.
    var mx = kx + 30;
    t += '<path class="g-maat" d="M' + mx + ' ' + KAAL_Y + ' L' + mx + ' ' + ky + '"/>' +
         '<path class="g-maat" d="M' + (mx - 6) + ' ' + KAAL_Y + ' L' + (mx + 6) +
           ' ' + KAAL_Y + '"/>' +
         '<path class="g-maat" d="M' + (mx - 6) + ' ' + ky + ' L' + (mx + 6) +
           ' ' + ky + '"/>' +
         '<text class="f-tekst ' + (terug ? "norm" : "sterk norm") + '" x="' +
           (mx + 10) + '" y="' + ((KAAL_Y + ky) / 2 + 5) + '">' + lager + '</text>';

    return t + "</svg>";
  }



  // De vulling voor de polder. Hij wordt twee keer getekend - gedempt bij ⟳ en
  // hard bij de transitie en de policy - en staat daarom één keer opgeschreven.
  var POLDER = {
    wie: "the polder",
    icoon: ICOON_POLDER,
    volgende: "the next polder",
    transitie: "Water Balance Engine",
    policy: "would choose what you do, and when",
    actie1: "which measure,",
    actie2: "and in which year",
    exogeen1: "the storm,",
    exogeen2: "the drought",
    beloning1: "preventing damage,",
    beloning2: "and what that may cost",
    doel: "goal: climate-proof, until 2100",
  };

  // ── wat dit bestand levert ────────────────────────────────────────────────
  T.wereldmodel = wereldmodel;
  T.transitiePaneel = transitiePaneel;
  T.POLDER = POLDER;
})(TEKEN);
