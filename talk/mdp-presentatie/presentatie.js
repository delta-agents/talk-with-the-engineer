// ═══════════════════════════════════════════════════════════════════════════
// De machinerie. Hier zit geen inhoud in — die staat in inhoud.js.
// ═══════════════════════════════════════════════════════════════════════════
//
// Geen framework, geen import, geen netwerk. Een klassiek script, dus dit werkt
// ook als je het bestand dubbelklikt en ook als de zaal geen wifi heeft. Dat is
// geen zuinigheid maar de eis: een presentatie die op een netwerkfout kan
// stukvallen, is geen presentatie.
//
// De hele toestand is één getal: welke beat staat er. Alles op het scherm is
// een functie van dat getal, dus terug kunnen is gratis en er bestaat geen
// stand die je alleen met de muis kunt bereiken.

(function () {
  "use strict";

  // ─────────────────────────────────────────────────────────────────────────
  // De beats uitrollen: één platte lijst, zodat vooruit en achteruit hetzelfde
  // zijn en de voortgang een deling is.
  // ─────────────────────────────────────────────────────────────────────────
  var BEATS = [{ stap: null, beat: INHOUD.titel, index: 0, van: 1 }];

  INHOUD.stappen.forEach(function (stap) {
    stap.beats.forEach(function (beat, i) {
      BEATS.push({ stap: stap, beat: beat, index: i, van: stap.beats.length });
    });
  });

  var nu = 0;

  // Boven dit aantal beats gaan de puntjes op twee rijen.
  var PUNTEN_PER_RIJ = 14;

  // ─────────────────────────────────────────────────────────────────────────
  // Figuren. Een figuur krijgt de beat-nadruk als lijst van deelnummers; welk
  // deel bij welk nummer hoort staat in de `data-deel` van de tekening.
  // ─────────────────────────────────────────────────────────────────────────

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
      '    <text class="f-tekst klein" x="210" y="88">de transitie van ' + v.wie + '</text>' +
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
      '    <text class="f-tekst sterk" x="335" y="262" text-anchor="middle">de policy</text>' +
      '    <text class="f-tekst klein" x="335" y="280" text-anchor="middle">' + v.policy + '</text>' +
      '    <path class="f-accent" d="M210 266 L150 266 L150 135"/>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <text class="f-tekst klein" x="574" y="182">en de beloning:</text>' +
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

  // ─────────────────────────────────────────────────────────────────────────
  // De polder in beweging: de tegenhanger van de microduck-clip.
  //
  // Geen video maar een tekening die loopt, en de standen erin zijn de uitvoer
  // van de rekenkern — zie de gegenereerde keyframes in style.css. De verticale
  // maat is 3,2 px per centimeter, met het streefpeil op y=250:
  //
  //     streefpeil        0 cm   → y 250
  //     inundatienorm    30 cm   → y 154
  //     de piek          36 cm   → y 135
  //
  // Er is bewust geen land dat onderloopt. De norm gaat over de STIJGING en niet
  // over overstromen, en water dat over een dijkje klotst zou dat verwarren.
  var polderAnimatie =
    '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="polder-animatie">' +

    // de regen: druppels op een snelle klok, de groep dooft mee met de bui
    '  <g class="p-regen">' +
    '    <g class="p-druppel"><path class="f-nat" d="M188 20 L188 34"/></g>' +
    '    <g class="p-druppel"><path class="f-nat" d="M222 14 L222 28"/></g>' +
    '    <g class="p-druppel"><path class="f-nat" d="M256 24 L256 38"/></g>' +
    '    <g class="p-druppel"><path class="f-nat" d="M290 16 L290 30"/></g>' +
    '    <g class="p-druppel"><path class="f-nat" d="M326 22 L326 36"/></g>' +
    '    <g class="p-druppel"><path class="f-nat" d="M360 12 L360 26"/></g>' +
    '    <g class="p-druppel"><path class="f-nat" d="M396 26 L396 40"/></g>' +
    '  </g>' +

    // Eén oever, links. Zijn kruin ligt boven de piek, dus er loopt niets over.
    // Rechts staat GEEN oever: die ruimte is voor de labels, en met een blok
    // daar lagen de norm, de piek en het streefpeil er bovenop.
    '  <path class="f-vlak" d="M60 118 L170 118 L170 300 L60 300 Z"/>' +
    '  <text class="f-tekst klein" x="115" y="140" text-anchor="middle">land</text>' +

    // het water: een vaste kolom tot streefpeil, en daarboven het deel dat stijgt
    '  <rect fill="var(--nat)" opacity=".22" x="170" y="250" width="260" height="50"/>' +
    '  <rect class="p-water-stijging" fill="var(--nat)" opacity=".5"' +
    '        x="170" y="135" width="260" height="115"/>' +
    '  <path class="f-lijn" d="M170 300 L430 300"/>' +

    // de peilband: drie vaste lijnen, en die maken elke bevroren stand leesbaar
    '  <path class="f-droog" stroke-dasharray="3 4" d="M150 135 L440 135"/>' +
    '  <text class="f-tekst sterk" x="452" y="131">de piek: 36 cm</text>' +
    '  <path class="f-norm" d="M150 154 L440 154"/>' +
    '  <text class="f-tekst norm" x="452" y="162">inundatienorm</text>' +
    '  <text class="f-tekst klein" x="452" y="179">30 cm stijging</text>' +
    '  <path class="f-lijn" stroke-dasharray="6 5" d="M150 250 L440 250"/>' +
    '  <text class="f-tekst klein" x="452" y="254">streefpeil</text>' +

    // het gemaal: draait mee met wat de balans er werkelijk uit haalt
    '  <g class="p-gemaal">' +
    '    <path class="f-nat" d="M400 286 L516 286"/>' +
    '    <path class="f-nat" d="M508 280 L518 286 L508 292"/>' +
    '    <text class="f-tekst klein" x="452" y="306">het gemaal</text>' +
    '  </g>' +

    // de dagteller, zodat je ziet waar in de bui je bent
    '  <path class="f-lijn" d="M170 322 L430 322"/>' +
    '  <text class="f-tekst klein" x="170" y="338">dag 1</text>' +
    '  <text class="f-tekst klein" x="430" y="338" text-anchor="end">dag 9</text>' +
    '  <g class="p-dag"><circle cx="170" cy="322" r="5" fill="var(--nadruk)"/></g>' +
    '</svg>';

  // ─────────────────────────────────────────────────────────────────────────
  // Het gebied van boven, in 2,5D
  //
  // Eén axonometrische projectie voor alle platen, zodat elk vlak, elke pijl en
  // elke wand uit dezelfde formule komt. Met de hand geplaatste ruiten lopen
  // onherroepelijk uit elkaar zodra er één maat verandert.
  //
  //     schermx = midx + (x - y) · cos30 · s
  //     schermy = midy + (x + y) · sin30 · s
  //
  // `x` en `y` lopen van 0 tot 1 over de plaat; `s` is de halve diagonaal.
  var COS30 = 0.8660254, SIN30 = 0.5;

  function iso(x, y, midx, midy, s) {
    return [midx + (x - y) * COS30 * s, midy + (x + y) * SIN30 * s];
  }

  function pad(punten) {
    return "M" + punten.map(function (p) {
      return p[0].toFixed(1) + " " + p[1].toFixed(1);
    }).join(" L") + " Z";
  }

  // Een rechthoek op de plaat, als ruit op het scherm.
  function isoVlak(x0, y0, x1, y1, midx, midy, s) {
    return pad([[x0, y0], [x1, y0], [x1, y1], [x0, y1]].map(function (p) {
      return iso(p[0], p[1], midx, midy, s);
    }));
  }

  // De twee wanden die je van voren ziet, samen de dikte van de plaat. Dit is
  // het enige wat de tekening 2,5D maakt in plaats van plat.
  function isoWanden(midx, midy, s, dik) {
    var links = iso(0, 1, midx, midy, s);
    var onder = iso(1, 1, midx, midy, s);
    var rechts = iso(1, 0, midx, midy, s);
    var zak = function (p) { return [p[0], p[1] + dik]; };
    return [
      pad([links, onder, zak(onder), zak(links)]),
      pad([onder, rechts, zak(rechts), zak(onder)]),
    ];
  }

  // Een plaat: wanden, dek, en een rand. `extra` komt bovenop het dek.
  function isoPlaat(midx, midy, s, dik, klasseDek) {
    var w = isoWanden(midx, midy, s, dik);
    return '<path class="i-wand" d="' + w[0] + '"/>' +
           '<path class="i-wand donker" d="' + w[1] + '"/>' +
           '<path class="' + (klasseDek || "i-land") + '" d="' +
             isoVlak(0, 0, 1, 1, midx, midy, s) + '"/>';
  }

  // Een CIRKEL op de plaat is op het scherm een asgerichte ellips, en dat is
  // geen benadering: met M = [[c,-c],[d,d]] is M·Mt diagonaal, dus de assen van
  // de ellips liggen langs x en y met
  //
  //     rx = r · c · sqrt(2)     ry = r · d · sqrt(2)     rx/ry = cos30/sin30
  //
  // Nagemeten tegen 720 punten op de cirkel: gelijk tot op drie decimalen. Een
  // gelijkmatige `scale()` op zo'n ellips blijft dus een cirkel op de plaat, en
  // daarom is vullen en droogvallen een gewone schaling en geen matrix.
  function isoEllips(x, y, r, midx, midy, s, klasse) {
    var m = iso(x, y, midx, midy, s);
    var wortel2 = Math.SQRT2;
    return '<ellipse class="' + klasse + '" cx="' + m[0].toFixed(1) +
           '" cy="' + m[1].toFixed(1) +
           '" rx="' + (r * COS30 * s * wortel2).toFixed(1) +
           '" ry="' + (r * SIN30 * s * wortel2).toFixed(1) + '"/>';
  }

  function isoPijl(van, naar, klasse) {
    var dx = naar[0] - van[0], dy = naar[1] - van[1];
    var len = Math.sqrt(dx * dx + dy * dy) || 1;
    var ux = dx / len, uy = dy / len;
    var punt = [naar[0], naar[1]];
    var vleugel = 7;
    var a = [punt[0] - ux * vleugel - uy * vleugel * 0.6,
             punt[1] - uy * vleugel + ux * vleugel * 0.6];
    var b = [punt[0] - ux * vleugel + uy * vleugel * 0.6,
             punt[1] - uy * vleugel - ux * vleugel * 0.6];
    return '<path class="' + klasse + '" d="M' + van[0].toFixed(1) + " " + van[1].toFixed(1) +
           " L" + punt[0].toFixed(1) + " " + punt[1].toFixed(1) + '"/>' +
           '<path class="' + klasse + '" d="M' + a[0].toFixed(1) + " " + a[1].toFixed(1) +
           " L" + punt[0].toFixed(1) + " " + punt[1].toFixed(1) +
           " L" + b[0].toFixed(1) + " " + b[1].toFixed(1) + '"/>';
  }

  // ── de ene polder, en wat je eraan kunt doen ──────────────────────────────
  // Delen: 0 = de kale polder, 1 = vasthouden, 2 = bergen, 3 = afvoeren,
  // 4 = aanvoeren. Elk label staat NAAST zijn eigen ingreep en niet in de rand:
  // op een beamer moet je in één blik zien welk woord bij welk vlak hoort.
  // De vijver van bergen, in plaatcoördinaten. Rechtsvoor en aan de andere kant
  // van de watergang dan vasthouden, zodat de twee elkaar niet raken.
  var BERG_X = 0.76, BERG_Y = 0.20, BERG_R = 0.155;

  var topdownPolder = (function () {
    var MX = 300, MY = 96, S = 168, DIK = 22;
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet">';

    t += '<g class="f-deel aan" data-deel="0">' +
         isoPlaat(MX, MY, S, DIK) +
         // de strook open water: vijf procent van het oppervlak
         '<path class="i-water" d="' + isoVlak(0, 0.45, 1, 0.55, MX, MY, S) + '"/>' +
         '<text class="f-tekst klein" x="' + (MX - 128) + '" y="' + (MY + 62) + '">land</text>' +
         // Boven de watergang aan zijn bovenstroomse kant, waar hij de plaat
         // binnenkomt - daar komt straks ook de inlaat uit.
         '<text class="f-tekst klein" x="' + (MX - 60) + '" y="' + (MY + 28) + '">open water</text>' +
         '</g>';

    // vasthouden: een deel van het LAND houdt zijn water dagen vast
    t += '<g class="f-deel" data-deel="1">' +
         '<path class="i-retentie" d="' + isoVlak(0.06, 0.62, 0.52, 0.95, MX, MY, S) + '"/>' +
         '<text class="f-tekst norm" x="' + (MX - 134) + '" y="' + (MY + 96) +
           '" text-anchor="end">vasthouden</text>' +
         '</g>';

    // Bergen is een APARTE vijver en geen bredere watergang: je koopt een stuk
    // land en zet het onder water. Rechtsvoor op de plaat, diagonaal tegenover
    // vasthouden, en los van de watergang - dan is bij wateroverlast te zien dat
    // hij vult en bij watertekort dat hij droogvalt.
    var vijver = iso(BERG_X, BERG_Y, MX, MY, S);
    t += '<g class="f-deel" data-deel="2">' +
         isoEllips(BERG_X, BERG_Y, BERG_R, MX, MY, S, "i-vijver") +
         isoEllips(BERG_X, BERG_Y, BERG_R * 0.72, MX, MY, S, "i-vijverwater") +
         '<text class="f-tekst norm" x="' + (vijver[0] + 44) + '" y="' +
           (vijver[1] - 22) + '">bergen</text>' +
         '</g>';

    // afvoeren: het gemaal in de rechterhoek wordt zwaarder
    var gemaal = iso(1, 0.5, MX, MY, S);
    t += '<g class="f-deel" data-deel="3">' +
         isoPijl(gemaal, iso(1.62, 0.5, MX, MY, S), "i-pijl dik") +
         '<circle class="i-gemaal" cx="' + gemaal[0].toFixed(1) + '" cy="' + gemaal[1].toFixed(1) + '" r="11"/>' +
         '<text class="f-tekst norm" x="' + (iso(1.62, 0.5, MX, MY, S)[0] + 10) + '" y="' +
             (iso(1.62, 0.5, MX, MY, S)[1] - 6) + '">afvoeren</text>' +
         '</g>';

    // aanvoeren: water van buiten, de watergang in waar hij de plaat binnenkomt
    // De pijl komt van boven de plaat af en langs dezelfde as als het gemaal,
    // zodat inlaat en gemaal de twee uiteinden van één watergang zijn.
    var buiten = iso(-0.62, 0.5, MX, MY, S);
    t += '<g class="f-deel" data-deel="4">' +
         isoPijl(buiten, iso(0, 0.5, MX, MY, S), "i-pijl droog") +
         '<text class="f-tekst norm" x="' + (buiten[0] - 4) + '" y="' + (buiten[1] - 10) +
           '" text-anchor="end">aanvoeren</text>' +
         '</g>';

    return t + "</svg>";
  })();

  // ── de twee gezichten van hetzelfde schema ────────────────────────────────
  //
  // Het world-modelschema staat er twee keer: dezelfde tekening, een andere
  // vulling. Zonder plaatje moet de zaal die wissel uit de bijschriften halen;
  // met een plaatje in de vrije hoek is het één blik. Ze staan in DEZELFDE hoek
  // en op dezelfde hoogte, zodat er bij de wissel niets verspringt en de ene
  // tekening 1 op 1 op de andere valt.
  //
  // De foto zit in een genest `svg`: dat knipt zichzelf bij op zijn viewport,
  // dus de `viewBox` hieronder IS de uitsnede - de eend zonder het meeste van
  // de tafel eromheen.
  var ICOON_ROBOT =
    '<svg x="27" y="244" width="96" height="154" viewBox="570 190 1040 1670"' +
    ' preserveAspectRatio="xMidYMid meet">' +
    '<image href="microduck.webp" x="0" y="0" width="2160" height="2160"/>' +
    '</svg>';

  // Dezelfde plaat als bij de drie maatregelen, klein: land, watergang,
  // vasthouden en bergen. Zo herkent de zaal het beeld van drie beats terug.
  var ICOON_POLDER = (function () {
    var MX = 75, MY = 276, S = 80, DIK = 11;
    return isoPlaat(MX, MY, S, DIK) +
      '<path class="i-water" d="' + isoVlak(0, 0.45, 1, 0.55, MX, MY, S) + '"/>' +
      '<path class="i-retentie" d="' + isoVlak(0.06, 0.62, 0.52, 0.95, MX, MY, S) + '"/>' +
      isoEllips(BERG_X, BERG_Y, BERG_R, MX, MY, S, "i-vijver") +
      isoEllips(BERG_X, BERG_Y, BERG_R * 0.72, MX, MY, S, "i-vijverwater");
  })();

  // ── drie knopen, en de twee manieren waarop ze aan elkaar hangen ──────────
  //
  // Dezelfde drie gebieden, twee keer getekend. Boven hangen ze als een KETTING
  // aan elkaar: wat A wegpompt is de aanvoer van B, en de knoop in het midden
  // krijgt zijn water niet weg omdat het benedenstrooms al vol staat. Onder
  // staan ze naast elkaar aan één eindige BRON, en dan zegt de verdringingsreeks
  // wie het eerst droogvalt.
  //
  // Ze staan boven elkaar op één plaat en niet op twee beats: het verschil ís
  // het punt, en twee koppelingen die je na elkaar ziet vergelijk je niet. Dat
  // verschil is de hele reden dat er twee gereedschappen zijn en niet één.
  var topdownNetwerk = (function () {
    var S = 58, DIK = 14;

    // Dezelfde stagger in beide helften, zodat de zaal ziet dat het om dezelfde
    // drie gebieden gaat en niet om zes.
    function trio(y0) {
      return [
        { naam: "A", mx: 150, my: y0 },
        { naam: "B", mx: 312, my: y0 + 48 },
        { naam: "C", mx: 474, my: y0 + 96 },
      ];
    }
    function platen(knopen) {
      return knopen.map(function (k) {
        return isoPlaat(k.mx, k.my, S, DIK) +
          '<path class="i-water" d="' + isoVlak(0, 0.42, 1, 0.58, k.mx, k.my, S) + '"/>' +
          '<text class="f-tekst sterk" x="' + k.mx + '" y="' + (k.my + 34) +
            '" text-anchor="middle">' + k.naam + '</text>';
      }).join("");
    }
    var uit = function (k) { return iso(1, 0.5, k.mx, k.my, S); };
    var in_ = function (k) { return iso(0, 0.5, k.mx, k.my, S); };

    // Breder dan de andere platen: de twee bijschriften rechts zijn de langste
    // regels in de hele deck, en ze moeten er op hun eigen maat in passen.
    var t = '<svg viewBox="0 0 920 520" preserveAspectRatio="xMidYMid meet">';

    // ── boven: de ketting ────────────────────────────────────────────────
    var nat = trio(30);
    t += '<text class="f-tekst sterk nat" x="616" y="70">nat: een ketting</text>' +
         '<text class="f-tekst klein" x="616" y="92">wat A wegpompt, is de aanvoer van B</text>' +
         platen(nat) +
         isoPijl(uit(nat[0]), in_(nat[1]), "i-pijl nat") +
         isoPijl(uit(nat[1]), in_(nat[2]), "i-pijl nat") +
         isoPijl(uit(nat[2]), [uit(nat[2])[0] + 74, uit(nat[2])[1] - 26], "i-pijl nat") +
         '<text class="f-tekst klein" x="' + (uit(nat[2])[0] + 26) + '" y="' +
           (uit(nat[2])[1] - 36) + '">buiten</text>' +
         // De knoop in het midden krijgt zijn water niet weg omdat het
         // benedenstrooms al vol staat. Een groter gemaal helpt daar niets.
         '<circle class="i-bindend" cx="' + nat[1].mx + '" cy="' +
           iso(0.5, 0.5, nat[1].mx, nat[1].my, S)[1].toFixed(1) + '" r="34"/>' +
         '<text class="f-tekst norm" x="' + nat[1].mx + '" y="' + (nat[1].my + 108) +
           '" text-anchor="middle">mogelijk knelpunt hier</text>';

    // ── onder: de verdeling ──────────────────────────────────────────────
    var droog = trio(290);
    var bron = { mx: 150, my: 428 };
    t += '<text class="f-tekst sterk droog" x="600" y="322">droog: een verdeling</text>' +
         '<text class="f-tekst klein" x="600" y="344">ze trekken alle drie aan dezelfde bron</text>' +
         platen(droog) +
         // De bron is een WATERLICHAAM en geen polder met een watergang erdoor,
         // dus zijn dek is water. Het randje van 0,012 is geen smaak maar een
         // rekensom: de dekking is (1 - 2 · rand)^2, en dat moet boven 95 %
         // blijven - gemeten 95,3 %. Zonder randje loopt het blauw over de rand
         // en valt de omtrek van de plaat visueel weg.
         isoPlaat(bron.mx, bron.my, 46, DIK, "i-bron") +
         '<path class="i-water vol" d="' +
           isoVlak(0.012, 0.012, 0.988, 0.988, bron.mx, bron.my, 46) + '"/>' +
         '<text class="f-tekst sterk" x="' + bron.mx + '" y="' + (bron.my + 28) +
           '" text-anchor="middle">bron</text>';
    droog.forEach(function (k) {
      t += isoPijl(iso(0.5, 0, bron.mx, bron.my, 46), iso(0.5, 1, k.mx, k.my, S), "i-pijl droog");
    });
    // de verdringingsreeks: vier schillen, en de onderste vallen als eerste droog
    var sx = 600, sy = 402;
    ["veiligheid", "nutsvoorziening", "hoogwaardig", "overig"].forEach(function (naam, i) {
      var valt = i >= 2;
      t += '<rect class="i-schil' + (valt ? " droog" : "") + '" x="' + sx + '" y="' +
             (sy + i * 22) + '" width="18" height="15"/>' +
           '<text class="f-tekst klein' + (valt ? " uit" : "") + '" x="' + (sx + 26) +
             '" y="' + (sy + i * 22 + 12) + '">' + naam + '</text>';
    });
    t += '<text class="f-tekst norm" x="' + sx + '" y="' + (sy - 12) + '">de verdringingsreeks</text>';
    return t + '</svg>';
  })();

  // ── het verloop boven de twee klokken ────────────────────────────────────
  //
  // Twee compacte grafiekjes, en ze delen hun x-as met de tijdbalk eronder: de
  // dagteller die daar loopt is dus ook de leeswijzer van de grafiek erboven.
  //
  // NAT is de neerslag-afvoergrafiek die elke hydroloog kent: de neerslag hangt
  // omgekeerd aan de bovenrand, de afvoer van het land staat eronder, en tussen
  // die twee zit de VERTRAGING - de bui piekt op dag vier, de afvoer een dag
  // later. De streep is wat het gemaal aankan; wat daarboven uitkomt blijft in
  // de polder staan, en dat is precies de stijging op de plaat ernaast.
  //
  // DROOG is de spiegel, maar niet van de vertraging: droog is er geen piek om
  // op te wachten, alleen een optelsom die doorloopt. Het tekort zakt van de
  // bovenrand weg naar 279 mm, en de eigen voorraad van de polder is de lijn
  // die na tien dagen vlak wordt. Het gat ertussen moet van buiten komen, en
  // dat is de hele reden dat droogte hier een aanvoervraag heet.
  //
  // De getallen zijn GEGENEREERD met scripts/gen_verloop.py. `c-lijn nat` is
  // water dat er is, `c-lijn droog` water dat mist.
  var AFVOERCURVE =
    "M570.0 150.0 C574.8 150.0 579.6 150.0 584.4 150.0" +
    " C594.1 150.0 603.7 150.0 613.3 150.0 C623.0 150.0 632.6 150.0 642.2 145.8" +
    " C651.9 141.6 661.5 130.0 671.1 122.1 C680.7 114.1 690.4 98.6 700.0 98.0" +
    " C709.6 97.5 719.3 111.9 728.9 118.6 C738.5 125.3 748.1 135.7 757.8 138.5" +
    " C767.4 141.3 777.0 140.6 786.7 141.4 C796.3 142.3 805.9 145.7 815.6 145.7" +
    " C820.4 145.7 825.2 145.7 830.0 145.7";

  var NEERSLAG_AFVOER =
    // Boven de gemaallijn gebeuren er twee dingen NA ELKAAR, en de doorrekening
    // zegt precies wanneer het omslaat: het peil gaat door de norm van 30 cm op
    // dag 4,93 en zakt er weer onder op dag 6,38. Daarvóór en daarna loopt de
    // berging vol; ertussen staat het water op het land.
    //
    // Twee knipvormen op één en dezelfde curve, en niet twee curves: zo kan er
    // niets uit elkaar lopen. De kleuren zijn dezelfde als op de plaat ernaast -
    // de vijver die zich vult, en de watergang die buiten zijn oevers komt.
    '<clipPath id="natBerging">' +
      '<rect x="570" y="30" width="142.4" height="93.3"/>' +
      '<rect x="754.3" y="30" width="75.7" height="93.3"/>' +
    '</clipPath>' +
    '<clipPath id="natOnder"><rect x="712.4" y="30" width="41.9" height="93.3"/></clipPath>' +
    // de bovenrand waar de neerslag aan hangt, en de nullijn van de afvoer
    '<path class="f-lijn" d="M570 30 L830 30"/>' +
    '<path class="f-lijn" d="M570 150 L830 150"/>' +
    // de staafjes: millimeter per dag, van boven naar beneden
    '<rect class="i-water" x="632.4" y="30" width="19.6" height="10.1"/>' +
    '<rect class="i-water" x="661.3" y="30" width="19.6" height="48.5"/>' +
    '<rect class="i-water" x="690.2" y="30" width="19.6" height="35.0"/>' +
    '<rect class="i-water" x="719.1" y="30" width="19.6" height="10.5"/>' +
    '<rect class="i-water" x="748.0" y="30" width="19.6" height="8.1"/>' +
    '<rect class="i-water" x="776.8" y="30" width="19.6" height="5.5"/>' +
    // de afvoer van het land als vlak, en het stuk dat er niet uit kan erbovenop
    '<path class="c-vlak nat" d="' + AFVOERCURVE + ' L830 150 L570 150 Z"/>' +
    '<g clip-path="url(#natBerging)">' +
      '<path class="c-vlak berging" d="' + AFVOERCURVE + ' L830 150 L570 150 Z"/>' +
    '</g>' +
    '<g clip-path="url(#natOnder)">' +
      '<path class="c-vlak onder" d="' + AFVOERCURVE + ' L830 150 L570 150 Z"/>' +
    '</g>' +
    '<path class="f-norm" d="M570 123.3 L830 123.3"/>' +
    '<path class="c-lijn nat" d="' + AFVOERCURVE + '"/>' +
    '<text class="f-tekst klein norm" x="828" y="118" text-anchor="end">het gemaal</text>' +
    // De liniaal loopt op dezelfde klok als de dagteller op de balk eronder, en
    // over dezelfde 260 eenheden: samen zijn ze één leeswijzer.
    '<g class="p-dag"><path class="g-nu" d="M570 30 L570 150"/></g>' +
    '<text class="f-tekst klein" x="570" y="22">oplopend tekort aan afvoercapaciteit</text>';

  var TEKORT_EN_VOORRAAD =
    // Twee VLAKKEN en niet twee lijnen: vijftien millimeter tegen tweehonderd-
    // negenenzeventig is als lijn een haartje onder de bovenrand, en als vlak
    // een streepje blauw tegen een wig bruin. Dat verschil is de hele boodschap.
    '<path class="i-tekort" d="M570 282 L830 393.5 L830 288 L584 288 Z"/>' +
    '<path class="i-water vol" d="M570 282 L830 282 L830 288 L584 288 Z"/>' +
    '<path class="f-lijn" d="M570 282 L830 282"/>' +
    // het tekort loopt op over het hele groeiseizoen
    '<path class="c-lijn droog" d="M570 282 L830 393.5"/>' +
    // wat de polder zelf heeft, en dat is na tien dagen op
    '<path class="c-lijn nat" d="M570 282 L584 288 L830 288"/>' +
    '<g class="p-dag"><path class="g-nu" d="M570 282 L570 402"/></g>' +
    '<text class="f-tekst klein" x="570" y="274">groeiend tekort aan aanvoer</text>';

  // ── de polder van boven, nat en droog ────────────────────────────────────
  //
  // Twee bewegende platen op één toneel: boven wat er gebeurt als het te hard
  // regent, onder wat er gebeurt als het te lang droog blijft. Ze staan onder
  // elkaar en niet op twee beats, want een polder moet ze allebei doorkomen -
  // dat is samen de vraag, en apart zijn het twee vragen.
  //
  // Van boven zie je geen diepte, dus een stijgend peil is onzichtbaar zolang
  // het in de watergang past. Wat je WEL ziet is het moment dat het eroverheen
  // gaat: dan zwelt de watergang en loopt het land onder. Droog krimpt dezelfde
  // watergang bínnen zijn oevers en droogt het land op - één formule, k aan
  // weerszijden van een.
  //
  // De TIJD en het PEIL komen uit de rekenkern. De breedte van de overstroming
  // is een proportionele afbeelding van de overschrijding en dus illustratief:
  // het model geeft een stand, geen inundatiecontour. Dat staat ook op het
  // scherm en in de README.
  var topdownNatDroog = (function () {
    var MX = 265, S = 168, DIK = 22;
    var NAT = 40, DROOG = 300;
    // De dagteller schuift over een balk van 260 breed; die maat staat in de
    // keyframes, dus beide klokken houden hem aan.
    var BAR0 = 570, BAR1 = 830;

    function berging(my, klasse) {
      var m = iso(BERG_X, BERG_Y, MX, my, S);
      return isoEllips(BERG_X, BERG_Y, BERG_R, MX, my, S, "i-vijver") +
        '<g class="' + klasse + '">' +
        isoEllips(BERG_X, BERG_Y, BERG_R * 0.94, MX, my, S, "i-vijverwater") +
        '</g>' +
        '<text class="f-tekst klein" x="' + (m[0] + 44) + '" y="' + (m[1] - 22) + '">berging</text>';
    }

    var t = '<svg viewBox="0 0 880 520" preserveAspectRatio="xMidYMid meet"' +
            ' class="polder-animatie">';

    // ── boven: negen dagen bui ───────────────────────────────────────────
    t += '<g class="p-regen">';
    [175, 205, 235, 265, 295, 325, 355].forEach(function (x, i) {
      t += '<g class="p-druppel"><path class="f-nat" d="M' + x + ' ' + (4 + (i % 3) * 6) +
           ' L' + x + ' ' + (18 + (i % 3) * 6) + '"/></g>';
    });
    t += '</g>';

    t += isoPlaat(MX, NAT, S, DIK) +
         // De overstroming en de watergang zijn ÉÉN vlak: van boven is de
         // overstroming niets anders dan de watergang buiten zijn oevers.
         '<path class="i-water p-inundatie" d="' + isoVlak(0, 0.45, 1, 0.55, MX, NAT, S) + '"/>' +
         berging(NAT, "p-berging");

    var gemaal = iso(1, 0.5, MX, NAT, S);
    t += '<g class="p-gemaal">' +
         isoPijl(gemaal, iso(1.62, 0.5, MX, NAT, S), "i-pijl nat") +
         '<text class="f-tekst klein" x="' + (gemaal[0] + 34) + '" y="' + (gemaal[1] - 12) +
           '">het gemaal</text>' +
         '</g>';

    t += '<text class="f-tekst norm" x="16" y="28">impact wateroverlast</text>' +
         NEERSLAG_AFVOER +
         '<path class="f-lijn" d="M' + BAR0 + ' 170 L' + BAR1 + ' 170"/>' +
         '<text class="f-tekst klein" x="' + BAR0 + '" y="188">dag 1</text>' +
         '<text class="f-tekst klein" x="' + BAR1 + '" y="188" text-anchor="end">dag 9</text>' +
         '<g class="p-dag"><circle cx="' + BAR0 + '" cy="170" r="5" fill="var(--nadruk)"/></g>';

    // ── onder: een half groeiseizoen ─────────────────────────────────────
    // Eigen klok, en die staat op DEZE groep: `p-seizoen` op de hele plaat zou
    // de bui hierboven ook op de seizoensduur zetten.
    //
    // De buffer is leeg na 9,9 van de 183 dagen: een streepje op die plek maakt
    // elk bevroren frame leesbaar, want daarna verandert alleen het land nog.
    var leeg = BAR0 + (BAR1 - BAR0) * 9.9 / 183;
    t += '<g class="p-seizoen">' +
         isoPlaat(MX, DROOG, S, DIK) +
         '<path class="i-dorst p-dorst" d="' + isoVlak(0, 0, 1, 1, MX, DROOG, S) + '"/>' +
         '<path class="i-water p-droogte" d="' + isoVlak(0, 0.45, 1, 0.55, MX, DROOG, S) + '"/>' +
         berging(DROOG, "p-bergingdroog");

    // De inlaat, gestippeld: deze polder HEEFT er geen, en dat is het punt.
    var buiten = iso(-0.62, 0.5, MX, DROOG, S);
    // Het bijschrift staat RECHTS van de staart en niet links ervan: links loopt
    // het bij deze tekstmaat de plaat af.
    t += isoPijl(buiten, iso(0, 0.5, MX, DROOG, S), "i-pijl leeg") +
         '<text class="f-tekst klein" x="' + (buiten[0] + 6) + '" y="' + (buiten[1] - 12) +
           '">zonder aanvoer</text>';

    t += '<text class="f-tekst norm" x="16" y="252">impact watertekort</text>' +
         TEKORT_EN_VOORRAAD +
         '<path class="f-lijn" d="M' + BAR0 + ' 430 L' + BAR1 + ' 430"/>' +
         '<path class="f-norm" d="M' + leeg.toFixed(1) + ' 422 L' + leeg.toFixed(1) + ' 438"/>' +
         '<text class="f-tekst norm" x="' + (leeg + 8).toFixed(1) + '" y="452">buffer leeg</text>' +
         '<text class="f-tekst klein" x="' + BAR0 + '" y="416">1 april</text>' +
         '<text class="f-tekst klein" x="' + BAR1 + '" y="416" text-anchor="end">1 oktober</text>' +
         '<g class="p-dag"><circle cx="' + BAR0 + '" cy="430" r="5" fill="var(--nadruk)"/></g>' +
         '</g>';

    return t + '</svg>';
  })();

  // ── wat een eis kost ─────────────────────────────────────────────────────
  //
  // De vorm die de literatuur gebruikt: Van Dantzig (1956) en Eijgenraam zetten
  // de INVESTERING tegen het beschermingsniveau en tellen daar de resterende
  // verwachte schade bij op; het optimum ligt waar die som het laagst is. Wij
  // kunnen alleen de eerste helft tekenen - en deel 2 is precies de helft die
  // ontbreekt. Dat is wat deze figuur moet laten zien.
  //
  // Padje GEGENEREERD met scripts/gen_kostencurve.py.
  //
  // Delen: 0 = de kostencurve, 1 = de vier prijzen, 2 = de curve die mist,
  // 3 = de band waarin meerdere hele pakketten allemaal verdedigbaar zijn.
  var kostencurve = (function () {
    var X0 = 96, X1 = 520, Y0 = 44, Y1 = 250;
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    t += '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X1 + ' ' + Y1 + '"/>' +
         '<path class="f-lijn" d="M' + X0 + ' ' + Y0 + ' L' + X0 + ' ' + Y1 + '"/>' +
         '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y0 - 12) +
           '">wat het goedkoopste pakket kost [mln euro]</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y1 + 4) +
           '" text-anchor="end">0</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y0 + 6) +
           '" text-anchor="end">2</text>' +
         '<text class="f-tekst klein" x="96" y="268" text-anchor="middle">36</text>' +
         '<text class="f-tekst klein" x="194" y="268" text-anchor="middle">30</text>' +
         '<text class="f-tekst klein" x="357" y="268" text-anchor="middle">20</text>' +
         '<text class="f-tekst klein" x="520" y="268" text-anchor="middle">10</text>' +
         '<text class="f-tekst klein" x="308" y="312" text-anchor="middle">de eis: hoeveel de piek nog mag stijgen [cm]</text>' +
         '<text class="f-tekst klein" x="308" y="330" text-anchor="middle">links de zesendertig centimeter van de kale lijn hiervoor</text>';

    t += '<g class="f-deel aan" data-deel="0">' +
         '<path class="c-lijn nat" d="M96.0 250.0 L128.6 242.4 L161.2 234.8 L193.8 227.2 L226.5 219.5 L259.1 211.9 L291.7 204.3 L324.3 193.7 L356.9 174.0 L389.5 154.8 L422.2 128.2 L454.8 105.3 L487.4 82.5 L520.0 59.6"/>' +
         '</g>';

    // De vier prijzen. Ze staan als EIGEN RIJ onder de eis-as: in het vlak
    // zelf botsen ze op de curve die er straks bij komt, en onder elkaar laten
    // ze zien dat de sprongen groter worden - nul, twee ton, zeven, achttien.
    var EISEN = [[96, 250, "\u20ac 0"], [193.8, 227.2, "\u20ac 0,22"],
                 [356.9, 174.0, "\u20ac 0,74"], [520, 59.6, "\u20ac 1,85"]];
    t += '<g class="f-deel" data-deel="1">';
    for (var i = 0; i < EISEN.length; i++) {
      t += '<circle class="c-optimum" cx="' + EISEN[i][0] + '" cy="' + EISEN[i][1] + '" r="6"/>' +
           '<text class="f-tekst sterk nat" x="' + EISEN[i][0] +
             '" y="292" text-anchor="middle">' + EISEN[i][2] + '</text>';
    }
    t += '</g>';

    t += '<g class="f-deel" data-deel="2">' +
         '<path class="c-lijn slecht" d="M96 80 C 220 128, 360 200, 520 238"/>' +
         '<text class="f-tekst sterk nadruk" x="532" y="86">hier hoort de</text>' +
         '<text class="f-tekst sterk nadruk" x="532" y="104">schadecurve</text>' +
         '<text class="f-tekst klein nadruk" x="532" y="128">nog in te vullen</text>' +
         '</g>';

    // deel 3: en die som heeft geen punt maar een BODEM. Dat is de reden dat we
    // alternatieven genereren in plaats van te optimaliseren: binnen die band
    // zijn meerdere hele pakketten allemaal verdedigbaar. De band is, net als de
    // schadecurve, de VORM uit de literatuur en niet een getal van ons.
    t += '<g class="f-deel" data-deel="3">' +
         '<rect class="c-band" x="270" y="44" width="150" height="206"/>' +
         '<text class="f-tekst sterk nadruk" x="345" y="66" text-anchor="middle">niet \u00e9\u00e9n punt</text>' +
         '<text class="f-tekst sterk nadruk" x="345" y="86" text-anchor="middle">maar een band</text>' +
         '</g>';

    return t + '</svg>';
  })();

  // ── de frequentielijn, met de polder eronder ─────────────────────────────
  //
  // Twee verdiepingen: boven de overschrijdingsfrequentielijn, onder de polder
  // in 2,5D. Dan is te zien WAARMEE gerekend wordt en niet alleen wat eruit
  // komt. Peilopzet is eruit: die gaat omhoog en leidt af van de vraag die deze
  // figuur stelt, namelijk wat een maatregel je aan bescherming oplevert.
  //
  // Padjes GEGENEREERD met scripts/gen_frequentielijn.py.
  //
  // Delen: 0 = de polder, 1 = de losse runs, 2 = de kale lijn,
  // 3 = bergen, 4 = vasthouden, 5 = afvoeren.
  var frequentielijn = (function () {
    var X0 = 96, X1 = 520, Y0 = 40, Y1 = 182;
    var NORM_Y = 128.8;
    var MX = 430, MY = 212, S = 82, DIK = 13;

    var t = '<svg viewBox="0 0 700 340" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    // de assen, de norm en de onderschriften: die staan altijd
    t += '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X1 + ' ' + Y1 + '"/>' +
         '<path class="f-lijn" d="M' + X0 + ' ' + Y0 + ' L' + X0 + ' ' + Y1 + '"/>' +
         '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y0 - 12) +
           '">de piek boven streefpeil [cm]</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y1 + 4) +
           '" text-anchor="end">0</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y0 + 6) +
           '" text-anchor="end">80</text>' +
         '<text class="f-tekst klein" x="96" y="198" text-anchor="middle">1</text>' +
         '<text class="f-tekst klein" x="308" y="198" text-anchor="middle">10</text>' +
         '<text class="f-tekst klein" x="520" y="198" text-anchor="middle">100</text>' +
         '<text class="f-tekst klein" x="308" y="220" text-anchor="middle">terugkeertijd [jaar]</text>' +
         '<path class="f-norm" d="M' + X0 + ' ' + NORM_Y + ' L' + X1 + ' ' + NORM_Y + '"/>' +
         '<text class="f-tekst norm" x="' + (X0 + 6) + '" y="' + (NORM_Y - 8) +
           '">de norm: 30 cm</text>';

    // deel 0: de polder zelf, onder de grafiek - waarmee gerekend wordt
    t += '<g class="f-deel aan" data-deel="0">' +
         isoPlaat(MX, MY, S, DIK) +
         '<path class="i-water" d="' + isoVlak(0, 0.45, 1, 0.55, MX, MY, S) + '"/>' +
         '<text class="f-tekst klein" x="96" y="258">1000 ha, 5 % open water,</text>' +
         '<text class="f-tekst klein" x="96" y="276">gemaal 1,5 m\u00b3/s</text>' +
         '</g>';

    // deel 1: acht losse doorrekeningen, voordat ze een lijn zijn
    t += '<g class="f-deel" data-deel="1">' +
         '<circle class="c-run" cx="96" cy="165" r="4"/>' +
         '<circle class="c-run" cx="160" cy="155" r="4"/>' +
         '<circle class="c-run" cx="244" cy="138" r="4"/>' +
         '<circle class="c-run" cx="308" cy="118" r="4"/>' +
         '<circle class="c-run" cx="372" cy="98" r="4"/>' +
         '<circle class="c-run" cx="392" cy="91" r="4"/>' +
         '<circle class="c-run" cx="456" cy="73" r="4"/>' +
         '<circle class="c-run" cx="520" cy="51" r="4"/>' +
         '<text class="f-tekst klein" x="532" y="164">acht keer</text>' +
         '<text class="f-tekst klein" x="532" y="180">doorgerekend</text>' +
         '</g>';

    // deel 2: dezelfde acht punten, nu als lijn
    t += '<g class="f-deel" data-deel="2">' +
         '<path class="c-lijn" d="M96.0 164.7 L159.8 155.4 L244.2 138.1 L308.0 118.1 L371.8 98.2 L392.4 90.7 L456.2 73.3 L520.0 50.6"/>' +
         '<text class="f-tekst sterk" x="532" y="53">geen maatregel</text>' +
         '<text class="f-tekst sterk" x="694" y="53" text-anchor="end">T=7</text>' +
         '</g>';

    // deel 3-5: de drie lijnen. Ze BLIJVEN staan, want de vergelijking is het
    // punt van de figuur - elke lijn is de maatregel ALLEEN, niet gestapeld.
    t += '<g class="f-deel" data-deel="3">' +
         '<path class="c-lijn accent" d="M96.0 167.7 L159.8 160.0 L244.2 145.4 L308.0 128.8 L371.8 112.2 L392.4 105.9 L456.2 91.4 L520.0 72.5"/>' +
         '<text class="f-tekst sterk accent" x="532" y="75">bergen</text>' +
         '<text class="f-tekst sterk accent" x="694" y="75" text-anchor="end">T=10</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="4">' +
         '<path class="c-lijn droog" d="M96.0 182.0 L159.8 176.7 L244.2 161.2 L308.0 148.4 L371.8 131.4 L392.4 125.1 L456.2 110.2 L520.0 90.9"/>' +
         '<text class="f-tekst sterk droog" x="532" y="93">vasthouden</text>' +
         '<text class="f-tekst sterk droog" x="694" y="93" text-anchor="end">T=22</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="5">' +
         '<path class="c-lijn derde" d="M96.0 180.0 L159.8 170.8 L244.2 159.3 L308.0 150.1 L371.8 140.8 L392.4 136.0 L456.2 119.3 L520.0 96.6"/>' +
         '<text class="f-tekst sterk derde" x="532" y="113">afvoeren</text>' +
         '<text class="f-tekst sterk derde" x="694" y="113" text-anchor="end">T=34</text>' +
         '</g>';

    // deel 6-8: dezelfde maatregel op de plaat, MET zijn maat. Precies EEN van
    // deze drie staat aan terwijl de lijnen zich opstapelen: de lijn is het
    // resultaat om te vergelijken, de plaat is de ingreep die erbij hoort.
    var vijver = iso(BERG_X, BERG_Y, MX, MY, S);
    t += '<g class="f-deel" data-deel="6">' +
         isoEllips(BERG_X, BERG_Y, BERG_R, MX, MY, S, "i-vijver") +
         isoEllips(BERG_X, BERG_Y, BERG_R * 0.72, MX, MY, S, "i-vijverwater") +
         '<text class="f-tekst sterk accent" x="' + (vijver[0] + 30).toFixed(0) + '" y="' +
           (vijver[1] - 16).toFixed(0) + '">bergen</text>' +
         '<text class="f-tekst sterk accent" x="96" y="302">tien hectare erbij: 5 \u2192 6 % open water</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="7">' +
         '<path class="i-retentie" d="' + isoVlak(0.06, 0.62, 0.52, 0.95, MX, MY, S) + '"/>' +
         '<text class="f-tekst sterk droog" x="349" y="276" text-anchor="end">vasthouden</text>' +
         '<text class="f-tekst sterk droog" x="96" y="302">708 hectare land: 74 % houdt zijn water vast</text>' +
         '</g>';

    var gemaal = iso(1, 0.5, MX, MY, S), uit = iso(1.62, 0.5, MX, MY, S);
    t += '<g class="f-deel" data-deel="8">' +
         isoPijl(gemaal, uit, "i-pijl dik") +
         '<circle class="i-gemaal" cx="' + gemaal[0].toFixed(1) + '" cy="' +
           gemaal[1].toFixed(1) + '" r="9"/>' +
         '<text class="f-tekst sterk derde" x="' + (uit[0] + 10).toFixed(0) + '" y="' +
           (uit[1] - 4).toFixed(0) + '">afvoeren</text>' +
         '<text class="f-tekst sterk derde" x="96" y="302">een halve kuub erbij: gemaal 1,5 \u2192 2,0 m\u00b3/s</text>' +
         '</g>';

    return t + '</svg>';
  })();

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
    var lager = terug ? "6 cm lager" : "16 cm lager";
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
    t += '<text class="f-tekst klein" x="210" y="88">de transitie van de polder</text>' +
         '<rect class="f-vlak" x="210" y="96" width="250" height="78" rx="7"/>' +
         '<text class="f-tekst sterk" x="335" y="140" text-anchor="middle">Waterbalans Engine</text>';

    // het weer komt van boven, en dat draait niet om
    t += '<path class="f-lijn" stroke-dasharray="5 5" d="M420 44 L420 88"/>' +
         '<path class="f-lijn" d="M414 80 L420 90 L426 80"/>' +
         '<text class="f-tekst wis" x="405" y="58" text-anchor="end">e</text>' +
         '<text class="f-tekst klein" x="436" y="52">dezelfde bui,</text>' +
         '<text class="f-tekst klein" x="436" y="68">eens per tien jaar</text>';

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
         '<text class="f-tekst klein" x="138" y="138" text-anchor="end">bergen</text>' +
         '<text class="f-tekst sterk ' + (terug ? "droog" : "") +
           '" x="138" y="156" text-anchor="end">' +
           (terug ? "+10 hectare" : "+40 hectare") + '</text>' +
         '<text class="f-tekst wis" x="574" y="130">s′</text>' +
         (terug
           ? '<text class="f-tekst klein" x="574" y="150">houd waterstand</text>' +
             '<text class="f-tekst klein" x="574" y="168">onder de norm</text>'
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
           ? "Hoeveel open water is nodig om de piek onder de norm te houden?"
           : "Met 40 hectare extra open water — hoeveel lager komt de piek?") +
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
           '" text-anchor="end">zonder maatregel</text>' +
         '<path class="c-lijn ' + tint + '" d="' + KROMME + '"/>' +
         '<text class="f-tekst klein" x="85" y="258">toename waterstand ↑</text>' +
         '<text class="f-tekst klein" x="338" y="442" text-anchor="middle">toename hectare open water →</text>';

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

  // ── de twee statistieken, als vorm ───────────────────────────────────────
  //
  // Het verschil tussen de twee IS de stap. De natte statistiek varieert de
  // GEBEURTENIS - dezelfde zomer, drie buiduren. De droge varieert het KLIMAAT
  // - hetzelfde groeiseizoen, zeven toekomsten. Padjes gegenereerd met
  // scripts/gen_statistiek.py.
  // Assen met een instelbaar kader, zodat twee plots in één figuur gestapeld
  // kunnen staan. `onder` is het label onderaan de y-as, want niet elke as
  // begint bij nul.
  function statistiekAssen(kader, labels, eenheid, top, onder) {
    var X0 = 96, X1 = 520;
    var Y0 = kader[0], Y1 = kader[1];
    var t = '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X1 + ' ' + Y1 + '"/>' +
            '<path class="f-lijn" d="M' + X0 + ' ' + Y0 + ' L' + X0 + ' ' + Y1 + '"/>' +
            '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y0 - 10) + '">' + eenheid + '</text>' +
            '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y1 + 4) +
              '" text-anchor="end">' + (onder || "0") + '</text>' +
            '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y0 + 6) +
              '" text-anchor="end">' + top + '</text>';
    labels.forEach(function (l) {
      t += '<text class="f-tekst klein" x="' + l[0] + '" y="' + (Y1 + 18) +
           '" text-anchor="middle">' + l[1] + '</text>';
    });
    return t;
  }

  var neerslagstatistiek =
    '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
    statistiekAssen([44, 215], [[96, "\u00bd"], [263, "10"], [520, "1000"]],
                    "neerslag [mm]", "150") +
    '<text class="f-tekst klein" x="308" y="251" text-anchor="middle">terugkeertijd [jaar]</text>' +
    '<g class="f-deel aan" data-deel="0">' +
    '  <path class="c-lijn reeks3" d="M96.0 161.4 L134.7 152.3 L173.3 143.2 L224.4 131.8 L263.1 122.7 L301.8 113.5 L314.2 110.1 L352.9 102.1 L391.6 91.8 L430.2 81.4 L442.7 78.0 L481.3 67.6 L520.0 57.2"/>' +
    '  <text class="f-tekst sterk reeks3" x="532" y="60">8 dagen</text>' +
    '  <path class="c-lijn reeks2" d="M96.0 181.9 L134.7 175.1 L173.3 167.1 L224.4 156.9 L263.1 147.7 L301.8 139.8 L314.2 136.3 L352.9 127.2 L391.6 116.3 L430.2 105.0 L442.7 101.3 L481.3 89.5 L520.0 77.2"/>' +
    '  <text class="f-tekst sterk reeks2" x="532" y="80">4 dagen</text>' +
    '  <path class="c-lijn reeks1" d="M96.0 196.8 L134.7 189.9 L173.3 183.1 L224.4 174.0 L263.1 166.0 L301.8 158.0 L314.2 154.6 L352.9 145.5 L391.6 134.4 L430.2 122.5 L442.7 118.6 L481.3 105.6 L520.0 91.7"/>' +
    '  <text class="f-tekst sterk reeks1" x="532" y="96">2 dagen</text>' +
    '</g>' +
    '<g class="f-deel" data-deel="1">' +
    '  <text class="f-tekst klein" x="532" y="126">en per seizoen</text>' +
    '  <text class="f-tekst klein" x="532" y="142">en per regime:</text>' +
    '  <text class="f-tekst sterk droog" x="532" y="164">zomer 59 mm</text>' +
    '  <text class="f-tekst sterk droog" x="532" y="182">winter 73 mm</text>' +
    '  <text class="f-tekst klein" x="532" y="200">dezelfde bui,</text>' +
    '  <text class="f-tekst klein" x="532" y="216">eens per 10 jaar</text>' +
    '</g>' +
    // De trekking staat ONDER de grafiek en niet erin: het is een andere
    // grootheid - millimeter per dag - en hij hoort niet in het T-vlak.
    '<g class="f-deel" data-deel="2">' +
    '  <path class="f-lijn" d="M96 322 L200 322"/>' +
    '  <rect class="i-band" x="96" y="316" width="20" height="6"/>' +
    '  <rect class="i-band" x="120" y="289" width="20" height="33"/>' +
    '  <rect class="i-band" x="144" y="261" width="20" height="61"/>' +
    '  <rect class="i-band" x="168" y="312" width="20" height="10"/>' +
    '  <text class="f-tekst klein" x="96" y="336">dag 1 tot 4</text>' +
    '  <text class="f-tekst sterk" x="216" y="284">\u00e9\u00e9n trekking</text>' +
    '  <text class="f-tekst klein" x="216" y="302">gaat de balans in als</text>' +
    '  <text class="f-tekst klein" x="216" y="318">millimeter per dag</text>' +
    '</g>' +
    '</svg>';

  // Vraag EN aanbod in één figuur, gestapeld. Twee grootheden met twee
  // eenheden horen niet op één as, maar wel onder elkaar: dezelfde
  // herhaaltijd-as, twee verdiepingen.
  var droogtestatistiek =
    '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
    statistiekAssen([40, 158], [], "de vraag: neerslagtekort [mm]", "600") +
    '<g class="f-deel aan" data-deel="0">' +
    '  <path class="i-band" d="M96.0 129.5 L195.3 118.4 L270.4 111.4 L369.7 103.0 L444.9 97.0 L520.0 91.4 L520.0 79.6 L444.9 85.4 L369.7 91.6 L270.4 100.8 L195.3 108.0 L96.0 120.4 Z"/>' +
    '  <path class="c-lijn" d="M96.0 122.5 L195.3 110.4 L270.4 103.2 L369.7 95.0 L444.9 89.6 L520.0 84.7"/>' +
    '  <text class="f-tekst sterk" x="532" y="112">nu</text>' +
    '  <text class="f-tekst klein" x="532" y="128">21 waterschappen</text>' +
    '  <path class="c-lijn slecht" d="M96.0 90.5 L195.3 73.1 L270.4 65.0 L369.7 57.5 L444.9 53.2 L520.0 50.0"/>' +
    '  <text class="f-tekst sterk nadruk" x="532" y="58">2100, droog</text>' +
    '  <text class="f-tekst klein nadruk" x="532" y="74">zeven toekomsten</text>' +
    '</g>' +
    statistiekAssen([186, 296], [[96, "2"], [270, "10"], [520, "100"]],
                    "het aanbod: rivierafvoer [deel van normaal]", "1,0", "0,5") +
    '<text class="f-tekst klein" x="308" y="332" text-anchor="middle">terugkeertijd [jaar]</text>' +
    '<g class="f-deel" data-deel="1">' +
    '  <path class="c-lijn nat" d="M96.0 186.2 L195.3 198.8 L270.4 208.0 L369.7 219.4 L444.9 227.6 L520.0 235.5"/>' +
    '  <text class="f-tekst sterk nat" x="532" y="216">Rijn</text>' +
    '  <text class="f-tekst klein nat" x="532" y="232">1077 m\u00b3/s normaal</text>' +
    '  <path class="c-lijn nat" stroke-dasharray="6 4" d="M96.0 194.6 L195.3 212.2 L270.4 224.5 L369.7 239.5 L444.9 250.0 L520.0 259.9"/>' +
    '  <text class="f-tekst sterk nat" x="532" y="262">Maas</text>' +
    '  <text class="f-tekst klein nat" x="532" y="278">50 m\u00b3/s normaal</text>' +
    '</g>' +
    '</svg>';
  // ── twee richtingen op dezelfde vuistregel ───────────────────────────────
  //

  // De vulling voor de polder. Hij wordt twee keer getekend - gedempt bij ⟳ en
  // hard bij de transitie en de policy - en staat daarom één keer opgeschreven.
  var POLDER = {
    wie: "de polder",
    icoon: ICOON_POLDER,
    volgende: "de volgende polder",
    transitie: "Waterbalans Engine",
    policy: "die zou kiezen wat je doet, en wanneer",
    actie1: "welke maatregel,",
    actie2: "en in welk jaar",
    exogeen1: "de bui,",
    exogeen2: "de droogte",
    beloning1: "schade voorkomen,",
    beloning2: "en wat dat mag kosten",
    doel: "doel: klimaatbestendig, tot 2100",
  };

  // ── twee kolommen naast elkaar, rij voor rij ─────────────────────────────
  //
  // Drie figuren hieronder stellen dezelfde vraag: dit tegenover dat, op een
  // handvol regels. Een eigen tekening per stuk zou drie keer hetzelfde raster
  // met andere woorden zijn, dus staat het raster hier één keer.
  //
  // Elke rij is een eigen `f-deel`, dus een beat zet ze één voor één aan of
  // alle vier tegelijk. Deel 0 is de koprij en staat altijd aan: zonder de twee
  // namen erboven zegt een rij niets.
  function kolommen(links, rechts, rijen, voet) {
    // De maten volgen `table.rijen`: labelkolom links, waarden LINKS uitgelijnd
    // onder hun kop, en een haarlijn onder elke rij. Deze plaat stond eerder met
    // gecentreerde waarden en zonder rijlijnen, en was daarmee de enige tabel in
    // de deck die er anders uitzag - terwijl `A` met zijn vier kolommen precies
    // dezelfde vorm heeft en het huisidioom wel volgt.
    var LAB = 16, L = 210, R = 430, BREED = 214;
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet">';

    // De koprij staat BUITEN elk deel, zoals de s-doos in `transitie`: zonder de
    // twee namen erboven zegt geen enkele rij iets, dus mag hij nooit wegvallen.
    t += '<g>' +
         '<text class="f-tekst sterk accent" x="' + L + '" y="40">' + links[0] + '</text>' +
         '<text class="f-tekst klein" x="' + L + '" y="60">' + links[1] + '</text>' +
         '<text class="f-tekst sterk derde" x="' + R + '" y="40">' + rechts[0] + '</text>' +
         '<text class="f-tekst klein" x="' + R + '" y="60">' + rechts[1] + '</text>' +
         '<path class="f-lijn" d="M' + LAB + ' 76 L644 76"/>' +
         '</g>';

    rijen.forEach(function (rij, i) {
      var y = 118 + i * 50;
      t += '<g class="f-deel" data-deel="' + i + '">' +
           '<text class="f-tekst klein" x="' + LAB + '" y="' + y + '">' + rij[0] + '</text>' +
           '<text class="f-tekst sterk" x="' + L + '" y="' + y + '">' + rij[1] + '</text>' +
           '<text class="f-tekst sterk" x="' + R + '" y="' + y + '">' + rij[2] + '</text>' +
           '<path class="f-lijn" d="M' + LAB + ' ' + (y + 16) + ' L644 ' + (y + 16) + '"/>' +
           '</g>';
    });

    // De voet mag meer dan een regel dragen: een conclusie van tachtig tekens is
    // op beamerafstand een regel te lang. Hij staat LINKS uitgelijnd met de rest
    // en niet gecentreerd, om dezelfde reden als de waarden.
    if (voet) {
      var yv = 118 + rijen.length * 50 + 34;
      t += '<g class="f-deel" data-deel="' + rijen.length + '">';
      [].concat(voet).forEach(function (regel, i) {
        t += '<text class="f-tekst sterk nadruk" x="' + LAB + '" y="' + (yv + i * 24) +
             '">' + regel + '</text>';
      });
      t += '</g>';
    }
    return t + "</svg>";
  }

  function lijsten(links, rechts) {
    function kolom(kop, regels, x, tint, deel) {
      var u = '<g class="f-deel" data-deel="' + deel + '">' +
              '<text class="f-tekst sterk ' + tint + '" x="' + x + '" y="34">' +
                kop + '</text>' +
              '<path class="f-lijn" d="M' + x + ' 50 L' + (x + 288) + ' 50"/>';
      regels.forEach(function (regel, i) {
        u += '<text class="f-tekst" x="' + x + '" y="' + (86 + i * 38) + '">' +
             regel + '</text>';
      });
      return u + '</g>';
    }
    return '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
           kolom(links[0], links.slice(1), 16, "accent", 0) +
           kolom(rechts[0], rechts.slice(1), 348, "derde", 1) + '</svg>';
  }

  // ── waarom er geen gok op het scherm komt ───────────────────────────────
  //
  // De natuurkunde van een noise-cancelling koptelefoon: die dempt niets, hij
  // zet het exacte tegengestelde signaal erover. Zo werkt een gereedschap ook -
  // het houdt het taalmodel niet tegen, het legt het gerekende getal eroverheen,
  // en wat er overblijft is alleen nog dat getal.
  //
  // De derde baan is daarom geen tekenvrijheid: hij is de optelsom van de twee
  // erboven, en die is uitgerekend vlak. Zie scripts/gen_ruisonderdrukking.py.
  //
  // De streep op deel 3 is de grens van de analogie, en hij hoort erbij. Een
  // koptelefoon haalt de bromtoon weg en niet de schreeuw ernaast; zo strijkt
  // een vuistregel de gok weg en niet een verkeerd begrepen vraag. Die zit niet
  // in de ruis, dus valt er ook niets tegen weg te strepen - en daarom staat de
  // streep in alle drie de banen even hoog.
  //
  // Delen: 0 = de gok, 1 = de vuistregel eroverheen, 2 = wat overblijft,
  //        3 = wat er dwars doorheen komt.
  //
  // De golven zijn GEGENEREERD met scripts/gen_ruisonderdrukking.py - niet met
  // de hand bijwerken.
  var RUIS =
    "M16.0 59.0 L22.5 56.6 L29.1 55.0 L35.6 54.1 L42.2 54.2 L48.7 55.1 L55.2 56.7 L61.8 59.0" +
    " L68.3 61.7 L74.9 64.5 L81.4 67.2 L88.0 69.5 L94.5 71.2 L101.0 72.2 L107.6 72.4 L114.1 71.9" +
    " L120.7 70.7 L127.2 69.0 L133.8 67.1 L140.3 65.2 L146.8 63.6 L153.4 62.3 L159.9 61.7 L166.5 61.8" +
    " L173.0 62.6 L179.5 64.1 L186.1 66.1 L192.6 68.5 L199.2 71.2 L205.7 73.8 L212.2 76.3 L218.8 78.6" +
    " L225.3 80.4 L231.9 81.9 L238.4 83.1 L245.0 84.0 L251.5 84.8 L258.0 85.6 L264.6 86.5 L271.1 87.6" +
    " L277.7 89.0 L284.2 90.6 L290.8 92.4 L297.3 94.2 L303.8 95.9 L310.4 97.2 L316.9 97.9 L323.5 97.9" +
    " L330.0 97.0 L336.5 95.2 L343.1 92.4 L349.6 88.7 L356.2 84.4 L362.7 79.6 L369.2 74.7 L375.8 69.8" +
    " L382.3 65.4 L388.9 61.5 L395.4 58.5 L402.0 56.5 L408.5 55.4 L415.0 55.2 L421.6 55.8 L428.1 57.0" +
    " L434.7 58.6 L441.2 60.3 L447.8 61.9 L454.3 63.2 L460.8 64.2 L467.4 64.8 L473.9 65.0 L480.5 64.8" +
    " L487.0 64.4 L493.5 64.0 L500.1 63.7 L506.6 63.6 L513.2 63.9 L519.7 64.6 L526.2 65.6 L532.8 67.0" +
    " L539.3 68.6 L545.9 70.3 L552.4 71.9 L559.0 73.2 L565.5 74.1 L572.0 74.6 L578.6 74.6 L585.1 74.2" +
    " L591.7 73.5 L598.2 72.7 L604.8 71.9 L611.3 71.3 L617.8 71.3 L624.4 71.8 L630.9 73.1 L637.5 75.2" +
    " L644.0 78.0";

  var REGEL =
    "M16.0 161.0 L22.5 163.4 L29.1 165.0 L35.6 165.9 L42.2 165.8 L48.7 164.9 L55.2 163.3 L61.8 161.0" +
    " L68.3 158.3 L74.9 155.5 L81.4 152.8 L88.0 150.5 L94.5 148.8 L101.0 147.8 L107.6 147.6 L114.1 148.1" +
    " L120.7 149.3 L127.2 151.0 L133.8 152.9 L140.3 154.8 L146.8 156.4 L153.4 157.7 L159.9 158.3 L166.5 158.2" +
    " L173.0 157.4 L179.5 155.9 L186.1 153.9 L192.6 151.5 L199.2 148.8 L205.7 146.2 L212.2 143.7 L218.8 141.4" +
    " L225.3 139.6 L231.9 138.1 L238.4 136.9 L245.0 136.0 L251.5 135.2 L258.0 134.4 L264.6 133.5 L271.1 132.4" +
    " L277.7 131.0 L284.2 129.4 L290.8 127.6 L297.3 125.8 L303.8 124.1 L310.4 122.8 L316.9 122.1 L323.5 122.1" +
    " L330.0 123.0 L336.5 124.8 L343.1 127.6 L349.6 131.3 L356.2 135.6 L362.7 140.4 L369.2 145.3 L375.8 150.2" +
    " L382.3 154.6 L388.9 158.5 L395.4 161.5 L402.0 163.5 L408.5 164.6 L415.0 164.8 L421.6 164.2 L428.1 163.0" +
    " L434.7 161.4 L441.2 159.7 L447.8 158.1 L454.3 156.8 L460.8 155.8 L467.4 155.2 L473.9 155.0 L480.5 155.2" +
    " L487.0 155.6 L493.5 156.0 L500.1 156.3 L506.6 156.4 L513.2 156.1 L519.7 155.4 L526.2 154.4 L532.8 153.0" +
    " L539.3 151.4 L545.9 149.7 L552.4 148.1 L559.0 146.8 L565.5 145.9 L572.0 145.4 L578.6 145.4 L585.1 145.8" +
    " L591.7 146.5 L598.2 147.3 L604.8 148.1 L611.3 148.7 L617.8 148.7 L624.4 148.2 L630.9 146.9 L637.5 144.8" +
    " L644.0 142.0";

  // hun optelsom is vlak tot op 0.0e+00 eenheid - nagerekend, niet aangenomen
  var SOM = "M16 262 L644 262";

  // De streep staat in de vrije strook tussen de labels links en rechts, en
  // niet in het midden van de plaat: hij moet drie banen kruisen en geen tekst.
  var PIEK_X = 360;

  var ruisonderdrukking =
    '<svg viewBox="0 0 660 320" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
    '  <g class="f-deel aan" data-deel="0">' +
    '    <text class="f-tekst klein" x="16" y="30">wat een taalmodel alleen produceert</text>' +
    '    <text class="f-tekst klein" x="644" y="30" text-anchor="end">vloeiend, en plausibel</text>' +
    '    <path class="f-ink" d="' + RUIS + '"/>' +
    '  </g>' +
    '  <g class="f-deel" data-deel="1">' +
    '    <path class="f-accent" d="' + REGEL + '"/>' +
    '    <text class="f-tekst klein" x="16" y="196">de vuistregel eroverheen, in tegenfase</text>' +
    '    <text class="f-tekst klein" x="644" y="196" text-anchor="end">exact, en op elke machine gelijk</text>' +
    '  </g>' +
    '  <g class="f-deel" data-deel="2">' +
    '    <text class="f-tekst klein" x="16" y="240">en wat er overblijft</text>' +
    '    <text class="f-tekst klein" x="644" y="240" text-anchor="end">alleen nog het gerekende getal</text>' +
    '    <path class="f-accent" d="' + SOM + '"/>' +
    '  </g>' +
    '  <g class="f-deel" data-deel="3">' +
    '    <path class="f-piek" d="M' + PIEK_X + ' 40 L' + PIEK_X + ' 278"/>' +
    '    <path class="f-piek" d="M' + (PIEK_X - 6) + ' 270 L' + PIEK_X + ' 280 L' + (PIEK_X + 6) + ' 270"/>' +
    '    <text class="f-tekst sterk nadruk" x="16" y="306">hier valt niets tegen weg te strepen</text>' +
    '  </g>' +
    '</svg>';

  // ── twee deuren, dezelfde keuken ────────────────────────────────────────
  //
  // Dezelfde drie blokken, twee keer gelezen - en dat is met opzet het idioom
  // van `transitiePaneel`: de blokken staan op dezelfde plek, alleen de pijlen
  // draaien en de ring verspringt naar wat je NIET weet. Ook de tinten rijmen,
  // dus de heenweg is accent en de omkering bruin.
  //
  // Boven de deur die iedereen kent: u kiest van de kaart en de prijs hoort u
  // bij de kassa. Onder de deur die alleen bestaat omdat de transitie naar de
  // maatregel toe op te lossen is - daar staat de prijs vooraan, en dan pas wat
  // eromheen te krijgen is.
  //
  // De onderste deur heeft twee ingangen en niet één, en daarom wijzen zijn
  // pijlen naar binnen in plaats van allebei naar links: er is een eis EN een
  // bedrag, en het pakket ertussen is het antwoord.
  //
  // Delen: 0 = het restaurant, 1 = de dealer, 2 = wat ze delen.
  var tweeDeuren = (function () {
    var C1 = 98, C2 = 330, C3 = 562;   // de hartlijnen van de drie blokken
    var X1 = 16, X2 = 248, X3 = 480, BREED = 164;

    function blok(x, y, kop, onder, tint) {
      return '<rect class="f-vlak" x="' + x + '" y="' + y + '" width="' + BREED +
             '" height="62" rx="7"/>' +
             '<text class="f-tekst sterk" x="' + (x + BREED / 2) + '" y="' + (y + 28) +
               '" text-anchor="middle">' + kop + '</text>' +
             '<text class="f-tekst klein ' + tint + '" x="' + (x + BREED / 2) + '" y="' + (y + 50) +
               '" text-anchor="middle">' + onder + '</text>';
    }

    // De ring staat om het blok dat je niet weet, met het vraagteken erboven -
    // hetzelfde gebaar als bij ⟳ en T, maar om een blok in plaats van een letter.
    function ring(x, y, cx) {
      return '<rect class="i-bindend" x="' + (x - 6) + '" y="' + (y - 6) + '" width="' +
             (BREED + 12) + '" height="74" rx="11" fill="none"/>' +
             '<text class="f-tekst wis nadruk" x="' + cx + '" y="' + (y - 12) +
               '" text-anchor="middle">?</text>';
    }

    var t = '<svg viewBox="0 0 660 330" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    // ── boven: de deur die iedereen kent ─────────────────────────────────
    t += '<g class="f-deel aan" data-deel="0">' +
         '<text class="f-tekst sterk derde" x="16" y="26">deur 1 \u2014 het restaurant</text>' +
         blok(X1, 42, "de wens", "ik wil maatregelen", "") +
         blok(X2, 42, "het pakket", "van de kaart", "") +
         blok(X3, 42, "de prijs", "bij de kassa", "") +
         '<path class="f-accent" d="M186 73 L242 73"/>' +
         '<path class="f-accent" d="M234 67 L244 73 L234 79"/>' +
         '<path class="f-accent" d="M418 73 L474 73"/>' +
         '<path class="f-accent" d="M466 67 L476 73 L466 79"/>' +
         ring(X3, 42, C3) +
         '</g>';

    // ── onder: de deur die de omkering opent ─────────────────────────────
    t += '<g class="f-deel" data-deel="1">' +
         '<text class="f-tekst sterk accent" x="16" y="162">deur 2 \u2014 de dealer</text>' +
         blok(X1, 178, "de wens", "hoe ver wilt u komen?", "") +
         blok(X2, 178, "het pakket", "en wat voor iets meer?", "droog") +
         blok(X3, 178, "de prijs", "wat mag het kosten?", "") +
         '<path class="f-droog" d="M186 209 L242 209"/>' +
         '<path class="f-droog" d="M234 203 L244 209 L234 215"/>' +
         '<path class="f-droog" d="M474 209 L428 209"/>' +
         '<path class="f-droog" d="M436 203 L426 209 L436 215"/>' +
         ring(X2, 178, C2) +
         '</g>';

    // ── en wat er achter allebei staat ───────────────────────────────────
    t += '<g class="f-deel" data-deel="2">' +
         '<path class="f-lijn" d="M16 272 L644 272"/>' +
         '<text class="f-tekst sterk" x="16" y="300">Twee deuren, dezelfde keuken.</text>' +
         '<text class="f-tekst klein" x="16" y="322">en de tweede bestaat alleen omdat dezelfde ' +
           'vergelijking ook naar de maatregel toe op te lossen is</text>' +
         '</g>';

    return t + '</svg>';
  })();

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
    ruisonderdrukking: ruisonderdrukking,
    twee_deuren: tweeDeuren,

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

  // ──────────────────────────────────────────────────────────────────────────
  // Tekenen
  // ──────────────────────────────────────────────────────────────────────────
  var app = document.getElementById("app");

  function el(tag, klasse, tekst) {
    var n = document.createElement(tag);
    if (klasse) n.className = klasse;
    if (tekst != null) n.textContent = tekst;
    return n;
  }

  function kop(actief) {
    var n = el("div", "kop");

    var inZone = function (naam) {
      return INHOUD.stappen.filter(function (s) { return s.zone === naam; });
    };
    var voor = inZone("voor");
    var tuple = inZone("tuple");
    var buiten = inZone("buiten");
    var gezien = true;

    // De vier leden die samen het WORLD MODEL zijn krijgen een eigen tint, en R
    // een andere. Dat is de vraag uit PR 71 - is de hele tuple het world model
    // of een deel ervan - en het antwoord staat nu in de kopregel zelf.
    var WERELDMODEL = ["W", "S", "A", "E", "T"];

    function chip(stap) {
      var b = el("button", "lid " +
        (WERELDMODEL.indexOf(stap.sleutel) >= 0 ? "wm" : "doel"));
      b.appendChild(el("span", "sym", stap.sym));
      b.title = stap.titel;
      if (stap === actief) { b.classList.add("actief"); gezien = false; }
      else if (gezien) b.classList.add("gedaan");
      b.addEventListener("click", function () { naarStap(stap); });
      return b;
    }

    // Een stap in zone "voor" staat links van `M =`: hij gaat over het schema
    // zelf en niet over een lid ervan.
    voor.forEach(function (stap) {
      n.appendChild(chip(stap));
      n.appendChild(el("span", "scheiding", "⇒"));
    });

    n.appendChild(el("span", "mlabel", INHOUD.label));
    n.appendChild(el("span", "haak", INHOUD.open));

    tuple.forEach(function (stap, i) {
      if (i > 0) n.appendChild(el("span", "komma", ","));
      n.appendChild(chip(stap));
    });
    n.appendChild(el("span", "haak", INHOUD.sluit));

    buiten.forEach(function (stap, i) {
      n.appendChild(el("span", "scheiding", i === 0 ? "+" : "⇒"));
      n.appendChild(chip(stap));
    });
    return n;
  }

  function rijenTabel(stap, beat) {
    var toon = beat.toon == null ? stap.rijen.length : beat.toon;
    var nadruk = beat.nadruk || [];
    var tabel = el("table", "rijen");
    var body = el("tbody");
    stap.rijen.forEach(function (rij, i) {
      var tr = el("tr", i >= toon ? "uit" : nadruk.indexOf(i) >= 0 ? "aan nadruk" : "aan");
      tr.appendChild(el("td", "veld", rij[0]));
      tr.appendChild(el("td", "waarde", rij[1]));
      tr.appendChild(el("td", "uitleg", rij[2]));
      body.appendChild(tr);
    });
    tabel.appendChild(body);
    return tabel;
  }

  // ── Media die blijft staan ────────────────────────────────────────────────
  //
  // Een element dat uit het document wordt gehaald en er weer in gezet, begint
  // zijn CSS-animatie opnieuw en een video springt terug naar frame nul. Twee
  // beats over dezelfde bui lieten de bui dus twee keer bij dag 1 beginnen -
  // gemeten 1487 ms terug naar 184 ms - en dan hoort de zaal "en dan loopt het
  // land onder" terwijl er nog niets gebeurd is.
  //
  // Daarom draagt elk stuk media een SLEUTEL. Verandert de sleutel niet, dan
  // blijft het element staan en werken we alleen bij wat er wél verschilt: welke
  // delen oplichten, en welke rijen zichtbaar zijn.
  var media = { sleutel: null, el: null };

  function mediaSleutel(stap, beat) {
    if (beat.video) return "video:" + beat.video;
    var f = beat.figuur || stap.figuur;
    if (f) return "figuur:" + f;
    if (stap.rijen) return "rijen:" + stap.sleutel;
    return null;
  }

  function figuurBlok(naam) {
    var n = el("div", "figuur");
    n.innerHTML = FIGUREN[naam] || "";
    return n;
  }

  // Video's die zichzelf willen starten MET geluid worden door elke browser
  // geweigerd zolang er nog geen gebruikersactie op de pagina is geweest. In een
  // presentatie is die actie er meestal wel - je drukt op een pijltje om hier te
  // komen - maar niet als iemand rechtstreeks op `#W.1` binnenkomt.
  //
  // Daarom: probeer met geluid, en val bij een weigering terug op stil in plaats
  // van op stilstand. Het blokje eromheen zegt dan dat je erop kunt klikken, en
  // elke volgende toets of klik zet het geluid alsnog aan.
  var stilGevallen = [];

  function stilMarkeren(v) {
    var wrap = v.parentNode;
    if (wrap && wrap.classList.contains("videoblok")) {
      if (v.muted) wrap.setAttribute("data-stil", "");
      else wrap.removeAttribute("data-stil");
    }
  }

  function videoBlok(bron) {
    var wrap = el("div", "videoblok");
    var v = document.createElement("video");
    v.className = "video";
    v.src = bron;
    v.loop = true;
    v.playsInline = true;
    v.autoplay = true;
    v.muted = false;
    wrap.appendChild(v);
    wrap.appendChild(el("span", "geluidhint", "klik voor geluid"));
    alleVideos.push(v);

    // Pas ná het volgende frame, want dan staat het element in het document;
    // `play()` op een losse knoop is onnodig wankel.
    requestAnimationFrame(function () {
      var poging = v.play();
      if (poging && poging.catch) {
        poging.catch(function () {
          v.muted = true;
          stilMarkeren(v);
          if (stilGevallen.indexOf(v) < 0) stilGevallen.push(v);
          v.play();
        });
      }
    });
    return wrap;
  }

  // GEEN `once`: de eerste toetsaanslag kan al voorbij zijn voordat de video
  // bestaat, en dan zou het geluid nooit meer terugkomen.
  function geluidAan() {
    if (!stilGevallen.length) return;
    stilGevallen.forEach(function (v) { v.muted = false; stilMarkeren(v); });
    stilGevallen = [];
  }
  addEventListener("keydown", geluidAan);

  // Drie of VIER kolommen. De vierde bestaat voor de maatregelen, waar heen en
  // terug naast elkaar horen te staan in plaats van in aparte beats.
  function rijenTabel(stap) {
    var breed = stap.rijen.some(function (r) { return r.length > 3; });
    var tabel = el("table", "rijen" + (breed ? " vier" : ""));
    var body = el("tbody");
    stap.rijen.forEach(function (rij) {
      var tr = el("tr");
      tr.appendChild(el("td", "veld", rij[0]));
      tr.appendChild(el("td", "waarde", rij[1]));
      tr.appendChild(el("td", "uitleg", rij[2]));
      if (breed) tr.appendChild(el("td", "uitleg terug", rij[3] || ""));
      body.appendChild(tr);
    });
    tabel.appendChild(body);
    return tabel;
  }

  // Alles wat per beat verschilt maar het element niet vervangt.
  function stemAf(node, stap, beat) {
    // Geen `nadruk` betekent "het eerste deel", een LEGE `nadruk` betekent
    // "nog niets" - dat is het verschil tussen een figuur die vanzelf begint
    // en een beat die de kale assen laat staan.
    var nadruk = beat.nadruk == null ? [0] : beat.nadruk;
    Array.prototype.forEach.call(node.querySelectorAll("[data-deel]"), function (g) {
      g.classList.toggle("aan", nadruk.indexOf(Number(g.getAttribute("data-deel"))) >= 0);
    });
    var rijen = node.querySelectorAll("tr");
    if (rijen.length && stap.rijen) {
      var toon = beat.toon == null ? stap.rijen.length : beat.toon;
      Array.prototype.forEach.call(rijen, function (tr, i) {
        tr.className = i >= toon ? "uit"
          : nadruk.indexOf(i) >= 0 ? "aan nadruk" : "aan";
      });
    }
  }

  // Een `<video>` die uit de DOM wordt gehaald STOPT NIET: hij speelt
  // gedetacheerd door, en dan hoor je de clip nog terwijl er al een andere slide
  // staat. Alleen de knoop weggooien is dus niet genoeg.
  //
  // Dit stond eerst als opruimpad op de twee plekken waar media wordt
  // weggegooid, en dat bleef fout gaan: er is altijd nog een route waarlangs een
  // element blijft hangen. Nu is het een INVARIANT die `teken()` bij ELKE beat
  // afdwingt - hoogstens een video mag spelen, en alleen die op het toneel staat.
  var alleVideos = [];

  function videosOpHetToneel() {
    if (!media.el) return [];
    return media.el.tagName === "VIDEO"
      ? [media.el]
      : Array.prototype.slice.call(media.el.querySelectorAll("video"));
  }

  function alleenDezeMagSpelen() {
    var op = videosOpHetToneel();
    alleVideos.forEach(function (v) {
      if (op.indexOf(v) >= 0) return;
      v.pause();
      var i = stilGevallen.indexOf(v);
      if (i >= 0) stilGevallen.splice(i, 1);
    });
    // Wat nergens meer aan hangt hoeft ook niet meer bewaakt te worden.
    alleVideos = alleVideos.filter(function (v) {
      return op.indexOf(v) >= 0 || document.contains(v);
    });
  }

  function mediaVoor(stap, beat) {
    var sleutel = mediaSleutel(stap, beat);
    if (sleutel === null) {
      media.sleutel = null;
      media.el = null;
      return null;
    }
    if (media.sleutel !== sleutel) {
      media.sleutel = sleutel;
      media.el = beat.video ? videoBlok(beat.video)
        : (beat.figuur || stap.figuur) ? figuurBlok(beat.figuur || stap.figuur)
        : rijenTabel(stap);
    }
    stemAf(media.el, stap, beat);
    return media.el;
  }

  // Het toneel, de zijde en de romp BLIJVEN staan; alleen hun inhoud wisselt.
  // Zodra je een van die drie per beat opnieuw opbouwt, raakt de media even los
  // van het document, en dat alleen al herstart elke animatie erin.
  var zijdeEl = el("div", "zijde");
  var rompEl = el("div", "romp");
  var titelEl = el("div");
  var bronEl = el("div", "bron");

  function vulToneel(n, stap, beat) {
    n.className = "toneel" + (stap ? "" : " leeg");

    if (!stap) {
      // De titelbeat heeft geen media om te sparen, dus hier mag het simpel.
      media.sleutel = null;
      media.el = null;
      // Alleen de kop. Een ondertitel is een tweede bewering op een scherm dat
      // er nog maar één nodig heeft, en de voet zegt al waar we beginnen.
      titelEl.replaceChildren(el("div", "titelkop", beat.kop));
      n.replaceChildren(titelEl);
      return;
    }

    // `sym`, `macht` en `titel` mogen per beat wisselen, en dat is er precies
    // één keer voor: bij T staat de omkering op de tweede beat, en dan hoort er
    // T⁻¹ op het toneel. In de KOP blijft het lid gewoon T - de tuple heeft geen
    // T⁻¹, die richting is iets wat je met T dóet.
    //
    // De macht is een echte `sup` en geen ⁻¹ uit de tekenset: die twee tekens
    // dragen hun eigen spatiëring mee en staan in een cursieve schreefletter van
    // tweehonderd pixels met een gat ertussen.
    var glyph = el("div", "glyph", beat.sym || stap.sym);
    if (beat.macht) glyph.appendChild(el("sup", null, beat.macht));
    zijdeEl.replaceChildren(
      glyph,
      el("div", "stap-titel", beat.titel || stap.titel),
      el("div", "stap-formule", beat.formule || stap.formule));

    var m = mediaVoor(stap, beat);
    if (m && m.parentNode !== rompEl) rompEl.replaceChildren(m);
    else if (!m) rompEl.replaceChildren();

    var bron = beat.bron === undefined ? stap.bron : beat.bron;
    bronEl.textContent = bron || "";
    bronEl.hidden = !bron;
    if (bronEl.parentNode !== rompEl) rompEl.appendChild(bronEl);

    if (zijdeEl.parentNode !== n) n.replaceChildren(zijdeEl, rompEl);
  }

  function voet(post) {
    var n = el("div", "voet");
    n.appendChild(el("div", "regel", post.beat.regel));

    var tellers = el("div", "tellers");

    // Voorbij PUNTEN_PER_RIJ wordt een enkele rij een streepjescode. Twee rijen
    // met evenveel kolommen leest wel: een raster vult rij voor rij, dus de
    // volgorde blijft van links naar rechts en dan naar beneden.
    var kolommen = post.van > PUNTEN_PER_RIJ ? Math.ceil(post.van / 2) : post.van;
    var punten = el("div", "punten");
    punten.style.gridTemplateColumns = "repeat(" + kolommen + ", auto)";
    for (var i = 0; i < post.van; i++) {
      punten.appendChild(el("span", "punt" + (i <= post.index ? " aan" : "")));
    }
    tellers.appendChild(punten);
    tellers.appendChild(el("span", "teller", nu + " / " + (BEATS.length - 1)));
    n.appendChild(tellers);
    return n;
  }

  var kopEl = el("div", "kop");
  var toneelEl = el("div", "toneel");
  var voetEl = el("div", "voet");
  app.replaceChildren(kopEl, toneelEl, voetEl);

  // Tekst in een figuur telt in eenheden van de viewBox, dus hoe groter de
  // figuur wordt uitgetekend, hoe kleiner diezelfde tekst op het scherm staat.
  // Dit zet de omgekeerde schaal als `--px`, en `style.css` rekent daarmee terug
  // naar een vast aantal pixels. Zo leest een plaat van 880 bij 520 net zo goed
  // als een van 660 bij 340.
  function schaalFiguur() {
    var n = toneelEl.querySelector(".figuur");
    var svg = n && n.querySelector("svg");
    if (!svg || !svg.viewBox.baseVal.width) return;
    var vb = svg.viewBox.baseVal;
    var r = svg.getBoundingClientRect();
    if (!r.width || !r.height) return;
    var s = Math.min(r.width / vb.width, r.height / vb.height);
    if (s > 0) n.style.setProperty("--px", (1 / s).toFixed(4));
  }

  addEventListener("resize", schaalFiguur);

  function teken() {
    var post = BEATS[nu];
    kopEl.replaceChildren.apply(kopEl, Array.prototype.slice.call(kop(post.stap).childNodes));
    vulToneel(toneelEl, post.stap, post.beat);
    alleenDezeMagSpelen();
    voetEl.replaceChildren.apply(voetEl, Array.prototype.slice.call(voet(post).childNodes));
    schaalFiguur();
    var hash = post.stap ? post.stap.sleutel + "." + (post.index + 1) : "start";
    if (location.hash.slice(1) !== hash) history.replaceState(null, "", "#" + hash);
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Bediening. Elke stand is met het toetsenbord te bereiken, want op een
  // beamer staan de handen niet op de muis.
  // ─────────────────────────────────────────────────────────────────────────
  function ga(d) { nu = Math.min(BEATS.length - 1, Math.max(0, nu + d)); teken(); }

  function naarStap(stap) {
    for (var i = 0; i < BEATS.length; i++) {
      if (BEATS[i].stap === stap && BEATS[i].index === 0) { nu = i; teken(); return; }
    }
  }

  function naarSprong(d) {
    var hier = BEATS[nu].stap;
    var stappen = INHOUD.stappen;
    var i = stappen.indexOf(hier);
    if (d > 0) naarStap(stappen[Math.min(stappen.length - 1, i + 1)]);
    else if (i <= 0) { nu = 0; teken(); }
    else naarStap(stappen[i - 1]);
  }

  var hulp = document.getElementById("hulp");

  addEventListener("keydown", function (e) {
    var k = e.key;
    if (k === "ArrowRight" || k === " " || k === "PageDown" || k === "Enter") { ga(1); e.preventDefault(); }
    else if (k === "ArrowLeft" || k === "PageUp" || k === "Backspace") { ga(-1); e.preventDefault(); }
    else if (k === "ArrowDown") { naarSprong(1); e.preventDefault(); }
    else if (k === "ArrowUp") { naarSprong(-1); e.preventDefault(); }
    else if (k === "Home") { nu = 0; teken(); }
    else if (k === "End") { nu = BEATS.length - 1; teken(); }
    else if (k === "Escape") { if (!hulp.hidden) hulp.hidden = true; else { nu = 0; teken(); } }
    else if (k === "?" || k === "/") { hulp.hidden = !hulp.hidden; e.preventDefault(); }
    else if (k === "f") { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen(); }
    else if (k >= "1" && k <= "9") {
      var stap = INHOUD.stappen[Number(k) - 1];
      if (stap) naarStap(stap);
    }
  });

  // Klikken en tikken: rechterkant vooruit, linkerstrook terug. Alleen op het
  // TONEEL en de VOET, en niet op het hele document: een klik om het venster
  // naar voren te halen kwam anders binnen als "volgende beat", en die schoof
  // dan ongevraagd door terwijl de presentator nog niets gezegd had.
  //
  // Op de VIDEO is een klik het geluid en niet de volgende beat. Anders kun je
  // het geluid niet aanzetten zonder de slide kwijt te raken.
  addEventListener("click", function (e) {
    var blok = e.target.closest(".videoblok");
    if (blok) {
      var v = blok.querySelector("video");
      v.muted = !v.muted;
      if (!v.muted) {
        var i = stilGevallen.indexOf(v);
        if (i >= 0) stilGevallen.splice(i, 1);
      }
      stilMarkeren(v);
      v.play();
      return;
    }
    geluidAan();
    var binnen = e.target.closest(".toneel") || e.target.closest(".voet");
    if (!binnen) return;
    ga(e.clientX < innerWidth * 0.28 ? -1 : 1);
  });

  // Diep linken: #E.3 opent stap E op beat 3.
  function uitHash() {
    var h = decodeURIComponent(location.hash.slice(1));
    if (!h || h === "start") return;
    var deel = h.split(".");
    for (var i = 0; i < BEATS.length; i++) {
      var b = BEATS[i];
      if (b.stap && b.stap.sleutel === deel[0] && b.index === (Number(deel[1]) || 1) - 1) { nu = i; return; }
    }
  }

  // Een hash die verandert terwijl de pagina al open staat, laadt niets opnieuw.
  // Zonder deze regel doet een gedeelde link `#E.4` alleen iets bij een verse
  // load, en dat is precies wanneer je hem niet gebruikt.
  addEventListener("hashchange", function () { uitHash(); teken(); });

  uitHash();
  teken();
})();
