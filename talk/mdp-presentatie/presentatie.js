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
  // Delen: 0 = de transitie, 1 = de policy die de actie kiest, 2 = het exogene,
  // 3 = de beloning en de lus die de policy bijwerkt.
  function wereldmodel(v) {
    return '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet">' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <text class="f-tekst klein" x="210" y="88">de transitie van ' + v.wie + '</text>' +
      '    <rect class="f-vlak" x="210" y="96" width="250" height="78" rx="7"/>' +
      '    <text class="f-tekst sterk" x="335" y="122" text-anchor="middle">' + v.transitie + '</text>' +
      '    <text class="f-tekst klein" x="335" y="142" text-anchor="middle">geen neuraal netwerk</text>' +
      '    <text class="f-tekst klein" x="335" y="160" text-anchor="middle">' + v.hoe + '</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-accent" d="M460 135 L516 135 L516 266 L470 266"/>' +
      '    <path class="f-accent" d="M478 260 L468 266 L478 272"/>' +
      '    <rect class="f-vlak" x="210" y="240" width="250" height="52" rx="7"/>' +
      '    <text class="f-tekst sterk" x="335" y="262" text-anchor="middle">de policy</text>' +
      '    <text class="f-tekst klein" x="335" y="280" text-anchor="middle">' + v.policy + '</text>' +
      '    <path class="f-accent" d="M210 266 L160 266 L160 135 L204 135"/>' +
      '    <path class="f-accent" d="M196 129 L206 135 L196 141"/>' +
      '    <text class="f-tekst wis" x="150" y="192" text-anchor="end">a</text>' +
      '    <text class="f-tekst klein" x="150" y="212" text-anchor="end">' + v.actie1 + '</text>' +
      '    <text class="f-tekst klein" x="150" y="228" text-anchor="end">' + v.actie2 + '</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-lijn" stroke-dasharray="5 5" d="M420 44 L420 88"/>' +
      '    <path class="f-lijn" d="M414 80 L420 90 L426 80"/>' +
      '    <text class="f-tekst wis" x="405" y="58" text-anchor="end">e</text>' +
      '    <text class="f-tekst klein" x="436" y="52">' + v.exogeen1 + '</text>' +
      '    <text class="f-tekst klein" x="436" y="68">' + v.exogeen2 + '</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="3">' +
      '    <text class="f-tekst wis" x="526" y="141">s\u2032</text>' +
      '    <text class="f-tekst klein" x="526" y="163">en de beloning:</text>' +
      '    <text class="f-tekst klein" x="526" y="179">' + v.beloning1 + '</text>' +
      '    <text class="f-tekst klein" x="526" y="195">' + v.beloning2 + '</text>' +
      '    <path class="f-droog" stroke-dasharray="4 4" d="M335 292 L335 308"/>' +
      '    <path class="f-droog" d="M329 300 L335 310 L341 300"/>' +
      '    <text class="f-tekst sterk" x="335" y="328" text-anchor="middle">' + v.ppo + '</text>' +
      '  </g>' +
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
  // Delen: 0 = de kale polder, 1 = vasthouden, 2 = bergen, 3 = afvoeren.
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
         '<text class="f-tekst klein" x="' + (MX + 96) + '" y="' + (MY + 168) + '">open water</text>' +
         '</g>';

    // vasthouden: een deel van het LAND houdt zijn water dagen vast
    t += '<g class="f-deel" data-deel="1">' +
         '<path class="i-retentie" d="' + isoVlak(0.06, 0.62, 0.52, 0.95, MX, MY, S) + '"/>' +
         '<text class="f-tekst norm" x="' + (MX - 118) + '" y="' + (MY + 214) + '">vasthouden</text>' +
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

    return t + "</svg>";
  })();

  // ── drie knopen, twee koppelingen ─────────────────────────────────────────
  // Dezelfde drie gebieden, en wat verandert is alleen wat ze met elkaar doet.
  // Nat is het een ketting waar het water langs naar buiten loopt; droog staan
  // ze naast elkaar aan dezelfde eindige bron. Dat verschil is de hele reden
  // dat er twee gereedschappen zijn en niet één.
  //
  // Delen: 0 = de drie knopen, 1 = de cascade, 2 = de verdeling.
  var topdownNetwerk = (function () {
    var S = 58, DIK = 14;
    var knopen = [
      { naam: "A", mx: 138, my: 74 },
      { naam: "B", mx: 300, my: 122 },
      { naam: "C", mx: 462, my: 170 },
    ];
    // `f-hard`: wat niet aan is, is hier ONZICHTBAAR en niet gedempt. De cascade
    // en de verdeling zijn ALTERNATIEVEN op dezelfde knopen en geen lagen die
    // opstapelen, dus een spookbeeld van de andere koppeling leest als "en dit
    // gebeurt ook" - precies verkeerd. Bij de andere figuren blijft dempen wel
    // goed: daar bouwt een beat op de vorige voort.
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet"' +
            ' class="f-hard">';

    t += '<g class="f-deel aan" data-deel="0">';
    knopen.forEach(function (k) {
      t += isoPlaat(k.mx, k.my, S, DIK) +
           '<path class="i-water" d="' + isoVlak(0, 0.42, 1, 0.58, k.mx, k.my, S) + '"/>' +
           '<text class="f-tekst sterk" x="' + k.mx + '" y="' + (k.my + 34) +
             '" text-anchor="middle">' + k.naam + '</text>';
    });
    t += '</g>';

    // NAT: een ketting. Wat A wegpompt is de aanvoer van B.
    var uit = function (k) { return iso(1, 0.5, k.mx, k.my, S); };
    var in_ = function (k) { return iso(0, 0.5, k.mx, k.my, S); };
    t += '<g class="f-deel" data-deel="1">' +
         isoPijl(uit(knopen[0]), in_(knopen[1]), "i-pijl nat") +
         isoPijl(uit(knopen[1]), in_(knopen[2]), "i-pijl nat") +
         isoPijl(uit(knopen[2]), [uit(knopen[2])[0] + 74, uit(knopen[2])[1] - 26], "i-pijl nat") +
         '<text class="f-tekst klein" x="' + (uit(knopen[2])[0] + 26) + '" y="' +
           (uit(knopen[2])[1] - 36) + '">buiten</text>' +
         // de knoop die BINDT: zijn gemaal kan niet weg omdat het benedenstrooms
         // al vol staat. Niet te klein, maar geblokkeerd.
         '<circle class="i-bindend" cx="' + knopen[1].mx + '" cy="' +
           iso(0.5, 0.5, knopen[1].mx, knopen[1].my, S)[1].toFixed(1) + '" r="34"/>' +
         '<text class="f-tekst norm" x="' + knopen[1].mx + '" y="' + (knopen[1].my + 108) +
           '" text-anchor="middle">hier knelt het</text>' +
         '<text class="f-tekst klein" x="' + knopen[1].mx + '" y="' + (knopen[1].my + 124) +
           '" text-anchor="middle">geblokkeerd, niet te klein</text>' +
         '</g>';

    // DROOG: geen ketting maar een bron waar ze alle drie aan trekken.
    var bron = { mx: 190, my: 232 };
    t += '<g class="f-deel" data-deel="2">' +
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
    knopen.forEach(function (k) {
      t += isoPijl(iso(0.5, 0, bron.mx, bron.my, 46), iso(0.5, 1, k.mx, k.my, S), "i-pijl droog");
    });
    // de verdringingsreeks: vier schillen, en de onderste vallen als eerste droog
    var sx = 520, sy = 236;
    ["veiligheid", "nutsvoorziening", "hoogwaardig", "overig"].forEach(function (naam, i) {
      var droog = i >= 2;
      t += '<rect class="i-schil' + (droog ? " droog" : "") + '" x="' + sx + '" y="' +
             (sy + i * 20) + '" width="18" height="15"/>' +
           '<text class="f-tekst klein' + (droog ? " uit" : "") + '" x="' + (sx + 26) +
             '" y="' + (sy + i * 20 + 12) + '">' + naam + '</text>';
    });
    t += '<text class="f-tekst norm" x="' + sx + '" y="' + (sy - 10) + '">de verdringingsreeks</text>';
    return t + '</g></svg>';
  })();

  // ── de bui van boven ─────────────────────────────────────────────────────
  // Dezelfde plaat als hierboven, nu in beweging. Van boven zie je geen diepte,
  // dus een stijgend peil is onzichtbaar zolang het in de watergang past. Wat je
  // WEL ziet is het moment dat het eroverheen gaat: dan zwelt de watergang en
  // loopt het land onder.
  //
  // De TIJD en het PEIL komen uit de rekenkern. De breedte van de overstroming
  // is een proportionele afbeelding van de overschrijding en dus illustratief:
  // het model geeft een stand, geen inundatiecontour. Dat staat ook op het
  // scherm en in de README.
  var topdownBui = (function () {
    var MX = 300, MY = 88, S = 168, DIK = 22;
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="polder-animatie">';

    t += '<g class="p-regen">';
    [188, 226, 264, 302, 340, 378, 414].forEach(function (x, i) {
      t += '<g class="p-druppel"><path class="f-nat" d="M' + x + ' ' + (12 + (i % 3) * 6) +
           ' L' + x + ' ' + (26 + (i % 3) * 6) + '"/></g>';
    });
    t += '</g>';

    t += isoPlaat(MX, MY, S, DIK);
    // De overstroming en de watergang zijn ÉÉN vlak: van boven is de overstroming
    // niets anders dan de watergang die buiten zijn oevers komt.
    t += '<path class="i-water p-inundatie" d="' + isoVlak(0, 0.45, 1, 0.55, MX, MY, S) + '"/>';

    t += isoEllips(BERG_X, BERG_Y, BERG_R, MX, MY, S, "i-vijver") +
         '<g class="p-berging">' +
         isoEllips(BERG_X, BERG_Y, BERG_R * 0.94, MX, MY, S, "i-vijverwater") +
         '</g>' +
         '<text class="f-tekst klein" x="' +
           (iso(BERG_X, BERG_Y, MX, MY, S)[0] + 44) + '" y="' +
           (iso(BERG_X, BERG_Y, MX, MY, S)[1] - 22) + '">berging</text>';

    var gemaal = iso(1, 0.5, MX, MY, S);
    t += '<g class="p-gemaal">' +
         isoPijl(gemaal, iso(1.62, 0.5, MX, MY, S), "i-pijl nat") +
         '<text class="f-tekst klein" x="' + (gemaal[0] + 34) + '" y="' + (gemaal[1] - 12) +
           '">het gemaal</text>' +
         '</g>';

    t += '<text class="f-tekst norm" x="40" y="32">impact wateroverlast</text>';

    t += '<path class="f-lijn" d="M200 316 L460 316"/>' +
         '<text class="f-tekst klein" x="200" y="332">dag 1</text>' +
         '<text class="f-tekst klein" x="460" y="332" text-anchor="end">dag 9</text>' +
         '<g class="p-dag"><circle cx="200" cy="316" r="5" fill="var(--nadruk)"/></g>';

    return t + '</svg>';
  })();

  // ── het seizoen van boven ────────────────────────────────────────────────
  // De spiegel van `topdownBui`. Nat zwelt de watergang buiten zijn oevers;
  // droog krimpt hij erbinnen en droogt het land op. Zelfde plaat, zelfde
  // formule, k aan de andere kant van een.
  //
  // Wat dit beeld moet overbrengen staat in de twee getallen erbij: de eigen
  // buffer van deze polder is 15 mm en het tekort is 279 mm. Droogte is dus geen
  // bergingsvraag maar een aanvoervraag, en dat is de brug naar de verdeling.
  var topdownDroogte = (function () {
    var MX = 300, MY = 88, S = 168, DIK = 22;
    var BAR0 = 200, BAR1 = 460;
    // De buffer is leeg na 9,9 van de 183 dagen: een streepje op die plek maakt
    // elk bevroren frame leesbaar, want daarna verandert alleen het land nog.
    var leeg = BAR0 + (BAR1 - BAR0) * 9.9 / 183;

    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet"' +
            ' class="polder-animatie p-seizoen">';

    t += isoPlaat(MX, MY, S, DIK);
    t += '<path class="i-dorst p-dorst" d="' + isoVlak(0, 0, 1, 1, MX, MY, S) + '"/>';
    t += '<path class="i-water p-droogte" d="' + isoVlak(0, 0.45, 1, 0.55, MX, MY, S) + '"/>';

    t += isoEllips(BERG_X, BERG_Y, BERG_R, MX, MY, S, "i-vijver") +
         '<g class="p-bergingdroog">' +
         isoEllips(BERG_X, BERG_Y, BERG_R * 0.94, MX, MY, S, "i-vijverwater") +
         '</g>' +
         '<text class="f-tekst klein" x="' +
           (iso(BERG_X, BERG_Y, MX, MY, S)[0] + 44) + '" y="' +
           (iso(BERG_X, BERG_Y, MX, MY, S)[1] - 22) + '">berging</text>';

    // De inlaat, gestippeld: deze polder HEEFT er geen, en dat is het punt.
    var inlaat = iso(0, 0.5, MX, MY, S);
    t += isoPijl(iso(-0.62, 0.5, MX, MY, S), inlaat, "i-pijl leeg") +
         '<text class="f-tekst klein" x="' + (iso(-0.62, 0.5, MX, MY, S)[0] - 4) +
           '" y="' + (iso(-0.62, 0.5, MX, MY, S)[1] - 10) +
           '" text-anchor="end">zonder aanvoer</text>';

    t += '<text class="f-tekst norm" x="40" y="32">impact watertekort</text>';

    t += '<path class="f-lijn" d="M' + BAR0 + ' 316 L' + BAR1 + ' 316"/>' +
         '<path class="f-norm" d="M' + leeg.toFixed(1) + ' 308 L' + leeg.toFixed(1) + ' 324"/>' +
         '<text class="f-tekst norm" x="' + (leeg + 8).toFixed(1) + '" y="332">buffer leeg</text>' +
         '<text class="f-tekst klein" x="' + BAR0 + '" y="304">1 april</text>' +
         '<text class="f-tekst klein" x="' + BAR1 + '" y="304" text-anchor="end">1 oktober</text>' +
         '<g class="p-dag"><circle cx="' + BAR0 + '" cy="316" r="5" fill="var(--nadruk)"/></g>';

    return t + '</svg>';
  })();

  // ── wat de maatregelen doen, tegen wat ze kosten ─────────────────────────
  //
  // Eén as voor alle drie, en die as is GELD. Dat is de eerlijke vergelijker:
  // welke maatregel koopt de meeste centimeter per euro. Normaliseren op "deel
  // van wat maximaal kan" zou afvoeren plat maken, want zijn bovengrens is
  // twintig keer het gemaal en dat is een zoekgrens en geen ambitie.
  //
  // De padjes zijn GEGENEREERD met scripts/gen_maatregelcurves.py: zestig
  // punten per curve, bemonsterd langs de geldas. Regenereren zodra de kern of
  // een eenheidsprijs verandert.
  //
  // Delen: 0 = afvoeren, 1 = bergen, 2 = vasthouden met zijn optimum.
  var maatregelcurves = (function () {
    var X0 = 96, X1 = 520, Y0 = 44, Y1 = 250;
    var NORM_Y = 95.5;         // 30 cm op een as van 0 tot 40
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    t += '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X1 + ' ' + Y1 + '"/>' +
         '<path class="f-lijn" d="M' + X0 + ' ' + Y0 + ' L' + X0 + ' ' + Y1 + '"/>' +
         '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y0 - 12) + '">piek [cm]</text>' +
         '<text class="f-tekst klein" x="652" y="' + (Y0 - 12) +
           '" text-anchor="end">waarvoor hij de norm haalt</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y1 + 4) +
           '" text-anchor="end">0</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y0 + 6) +
           '" text-anchor="end">40</text>' +
         '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y1 + 20) + '">0</text>' +
         '<text class="f-tekst klein" x="' + X1 + '" y="' + (Y1 + 20) +
           '" text-anchor="end">3 miljoen euro</text>' +
         '<path class="f-norm" d="M' + X0 + ' ' + NORM_Y + ' L' + X1 + ' ' + NORM_Y + '"/>' +
         '<text class="f-tekst norm" x="' + (X0 + 6) + '" y="' + (NORM_Y - 8) + '">de norm</text>' +
         '<text class="f-tekst klein" x="' + X1 + '" y="' + (Y0 + 2) +
           '" text-anchor="end">zonder maatregel: 36 cm</text>';

    // De labels staan RECHTS van de curve-einden en niet erop. Een label op een
    // lijn is onleesbaar, en dat is precies wat er eerst stond.
    t += '<g class="f-deel aan" data-deel="0">' +
         '<path class="c-lijn nat" d="M96.0 64.7 L103.2 71.8 L110.4 78.8 L117.6 85.9 L124.7 93.0 L131.9 100.0 L139.1 107.1 L146.3 114.2 L153.5 121.2 L160.7 128.3 L167.9 133.2 L175.1 137.9 L182.2 141.1 L189.4 143.4 L196.6 145.8 L203.8 148.2 L211.0 150.5 L218.2 152.9 L225.4 155.2 L232.5 157.6 L239.7 159.9 L246.9 162.3 L254.1 164.7 L261.3 167.0 L268.5 169.4 L275.7 171.7 L282.8 174.1 L290.0 176.4 L297.2 178.8 L304.4 181.2 L311.6 183.5 L318.8 185.9 L326.0 188.2 L333.2 190.6 L340.3 192.9 L347.5 195.3 L354.7 197.6 L361.9 200.0 L369.1 202.4 L376.3 204.7 L383.5 207.1 L390.6 209.4 L397.8 211.8 L405.0 214.1 L412.2 216.5 L419.4 218.9 L426.6 221.2 L433.8 223.6 L440.9 225.9 L448.1 228.3 L455.3 230.6 L462.5 233.0 L469.7 235.4 L476.9 237.7 L484.1 240.1 L491.3 242.4 L498.4 244.8 L505.6 247.1 L512.8 249.5 L520.0 250.0"/>' +
         '<text class="f-tekst sterk nat" x="532" y="246">afvoeren</text>' +
         '<text class="f-tekst klein nat" x="532" y="262">€ 0,23 mln</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="1">' +
         '<path class="c-lijn" d="M96.0 64.7 L103.2 66.1 L110.4 67.4 L117.6 68.8 L124.7 70.1 L131.9 71.4 L139.1 72.7 L146.3 74.0 L153.5 75.2 L160.7 76.4 L167.9 77.7 L175.1 78.9 L182.2 80.0 L189.4 81.2 L196.6 82.4 L203.8 83.5 L211.0 84.6 L218.2 85.7 L225.4 86.8 L232.5 87.9 L239.7 88.9 L246.9 90.0 L254.1 91.0 L261.3 92.0 L268.5 93.0 L275.7 94.0 L282.8 95.0 L290.0 96.0 L297.2 96.9 L304.4 97.9 L311.6 98.8 L318.8 99.7 L326.0 100.7 L333.2 101.6 L340.3 102.5 L347.5 103.3 L354.7 104.2 L361.9 105.1 L369.1 105.9 L376.3 106.7 L383.5 107.6 L390.6 108.4 L397.8 109.2 L405.0 110.0 L412.2 110.8 L419.4 111.6 L426.6 112.3 L433.8 113.1 L440.9 113.9 L448.1 114.6 L455.3 115.4 L462.5 116.1 L469.7 116.8 L476.9 117.5 L484.1 118.2 L491.3 118.9 L498.4 119.6 L505.6 120.3 L512.8 121.0 L520.0 121.7"/>' +
         '<text class="f-tekst sterk" x="532" y="118">bergen</text>' +
         '<text class="f-tekst klein" x="532" y="134">€ 1,35 mln</text>' +
         '</g>';

    // Het optimum ligt BINNEN het bereik, en dat is de hele pointe: meer geld
    // maakt vasthouden daarna slechter.
    t += '<g class="f-deel" data-deel="2">' +
         '<path class="c-lijn droog" d="M96.0 64.7 L101.5 67.7 L106.9 70.7 L112.4 73.7 L117.8 76.7 L123.3 79.7 L128.8 82.7 L134.2 85.7 L139.7 88.7 L145.2 91.7 L150.6 94.7 L156.1 97.7 L161.5 100.7 L167.0 103.7 L172.5 106.7 L177.9 109.2 L183.4 110.7 L188.8 112.3 L194.3 113.8 L199.8 115.4 L205.2 116.9 L210.7 118.5 L216.2 120.0 L221.6 121.5 L227.1 123.1 L232.5 124.6 L238.0 126.2 L243.5 127.7 L248.9 129.3 L254.4 130.8 L259.9 132.4 L265.3 133.9 L270.8 135.4 L276.2 137.0 L281.7 138.5 L287.2 140.1 L292.6 141.6 L298.1 143.2 L303.5 144.7 L309.0 146.2 L314.5 147.8 L319.9 149.3 L325.4 150.9 L330.9 152.4 L336.3 152.4 L341.8 152.3 L347.2 152.1 L352.7 151.9 L358.2 151.8 L363.6 151.6 L369.1 151.5 L374.5 151.3 L380.0 151.1 L385.5 151.0 L390.9 150.8 L396.4 150.7 L401.9 150.5 L407.3 150.3 L412.8 150.2 L418.2 150.0"/>' +
         '<circle class="c-optimum" cx="336.3" cy="152.4" r="6"/>' +
         '<text class="f-tekst sterk droog" x="432" y="146">vasthouden</text>' +
         '<text class="f-tekst klein droog" x="432" y="162">€ 0,40 mln</text>' +
         '<text class="f-tekst klein" x="432" y="178">bodem 18,9 cm bij 74 %</text>' +
         '</g>';

    return t + '</svg>';
  })();

  // ── de overschrijdingsfrequentielijn ─────────────────────────────────────
  //
  // Het huisidioom van de waterveiligheid: hoogtes tegen hun
  // overschrijdingsfrequentie, met een lijn per maatregel. De x-as is
  // LOGARITMISCH in de terugkeertijd, want dat is de conventie en omdat de
  // interessante kruisingen anders allemaal op elkaar liggen.
  //
  // Op de y-as staat de stijging boven het OORSPRONKELIJKE peil, dus inclusief
  // peilopzet. Dat is de grootheid waar de inundatienorm over gaat, en het is
  // ook waarom peilopzet hier BOVEN de kale lijn uitkomt: hij eet de marge op.
  //
  // Padjes GEGENEREERD met scripts/gen_frequentielijn.py.
  //
  // Delen: 0 = de kale lijn, 1 = peilopzet (omhoog!), 2 = bergen,
  // 3 = vasthouden, 4 = afvoeren.
  var frequentielijn = (function () {
    var X0 = 96, X1 = 520, Y0 = 44, Y1 = 250;
    var NORM_Y = 188.2;
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    t += '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X1 + ' ' + Y1 + '"/>' +
         '<path class="f-lijn" d="M' + X0 + ' ' + Y0 + ' L' + X0 + ' ' + Y1 + '"/>' +
         '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y0 - 12) +
           '">waterstand [cm boven streefpeil]</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y1 + 4) +
           '" text-anchor="end">0</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y0 + 6) +
           '" text-anchor="end">100</text>' +
         '<text class="f-tekst klein" x="96" y="' + (Y1 + 20) + '" text-anchor="middle">1</text>' +
         '<text class="f-tekst klein" x="308" y="' + (Y1 + 20) + '" text-anchor="middle">10</text>' +
         '<text class="f-tekst klein" x="520" y="' + (Y1 + 20) + '" text-anchor="middle">100</text>' +
         '<text class="f-tekst klein" x="308" y="' + (Y1 + 38) +
           '" text-anchor="middle">terugkeertijd [jaar]</text>' +
         '<path class="f-norm" d="M' + X0 + ' ' + NORM_Y + ' L' + X1 + ' ' + NORM_Y + '"/>' +
         '<text class="f-tekst norm" x="' + (X0 + 6) + '" y="' + (NORM_Y + 18) +
           '">de norm: 30 cm</text>' +
         '<text class="f-tekst klein" x="' + X1 + '" y="' + (Y0 - 12) +
           '" text-anchor="end">rechts: veilig tot</text>';

    t += '<g class="f-deel aan" data-deel="0">' +
         '<path class="c-lijn" d="M96.0 229.9 L159.8 219.2 L244.2 199.0 L308.0 175.9 L371.8 152.7 L392.4 144.1 L456.2 123.8 L520.0 97.5"/>' +
         '<text class="f-tekst sterk" x="532" y="99">geen maatregel</text>' +
         '<text class="f-tekst sterk" x="654" y="99" text-anchor="end">T=7</text>' +
         '</g>';

    // Peilopzet gaat OMHOOG. Dat is geen fout in de tekening maar de prijs van
    // de maatregel: elke centimeter opzet is een centimeter minder marge.
    t += '<g class="f-deel" data-deel="1">' +
         '<path class="c-lijn slecht" d="M96.0 188.7 L159.8 178.0 L244.2 157.8 L308.0 134.7 L371.8 111.5 L392.4 102.9 L456.2 82.6 L520.0 56.3"/>' +
         '<text class="f-tekst sterk nadruk" x="532" y="58">peilopzet</text>' +
         '<text class="f-tekst sterk nadruk" x="654" y="58" text-anchor="end">T=1</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="2">' +
         '<path class="c-lijn accent" d="M96.0 233.4 L159.8 224.5 L244.2 207.5 L308.0 188.2 L371.8 168.9 L392.4 161.7 L456.2 144.8 L520.0 122.9"/>' +
         '<text class="f-tekst sterk accent" x="532" y="124">bergen</text>' +
         '<text class="f-tekst sterk accent" x="654" y="124" text-anchor="end">T=10</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="3">' +
         '<path class="c-lijn droog" d="M96.0 250.0 L159.8 243.8 L244.2 225.9 L308.0 211.0 L371.8 191.3 L392.4 183.9 L456.2 166.7 L520.0 144.3"/>' +
         '<text class="f-tekst sterk droog" x="532" y="145">vasthouden</text>' +
         '<text class="f-tekst sterk droog" x="654" y="145" text-anchor="end">T=22</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="4">' +
         '<path class="c-lijn nat" d="M96.0 247.7 L159.8 237.0 L244.2 223.6 L308.0 212.9 L371.8 202.2 L392.4 196.6 L456.2 177.2 L520.0 150.9"/>' +
         '<text class="f-tekst sterk nat" x="532" y="166">afvoeren</text>' +
         '<text class="f-tekst sterk nat" x="654" y="166" text-anchor="end">T=34</text>' +
         '</g>';

    return t + '</svg>';
  })();

  // ── twee richtingen op dezelfde vuistregel ───────────────────────────────
  //
  // Dit is wat de toolset bijzonder maakt: elke vuistregel werkt heen EN terug.
  // Geef de maatregel en je krijgt de stand; geef de gewenste stand en je krijgt
  // de maatregel. Het idioom komt uit docs/images/vuistregel-tools.svg - de
  // rode ring markeert wat je NIET weet - maar hier gekanteld naar 2,5D.
  //
  // Delen: 0 = heen (maatregel bekend, stand onbekend),
  //        1 = terug (stand gewenst, maatregel onbekend).
  var tweerichting = (function () {
    var MX = 200, MY = 92, S = 132, DIK = 18;
    var GX = 424, GB = 62, GY0 = 96, GY1 = 232;   // de peilmeter
    var H0 = 196, H1 = 140;                        // stand voor en na
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    // de polder, met de vijver van bergen als de maatregel waar het over gaat
    t += isoPlaat(MX, MY, S, DIK) +
         '<path class="i-water" d="' + isoVlak(0, 0.45, 1, 0.55, MX, MY, S) + '"/>' +
         isoEllips(BERG_X, BERG_Y, BERG_R, MX, MY, S, "i-vijver") +
         isoEllips(BERG_X, BERG_Y, BERG_R * 0.72, MX, MY, S, "i-vijverwater") +
         '<text class="f-tekst klein" x="' + MX + '" y="' + (MY + 196) +
           '" text-anchor="middle">de maatregel</text>';

    // de peilmeter: streefpeil, en de stijging daarboven
    t += '<rect class="f-vlak" x="' + GX + '" y="' + GY0 + '" width="' + GB +
           '" height="' + (GY1 - GY0) + '"/>' +
         '<rect fill="var(--nat)" opacity=".45" x="' + GX + '" y="' + H0 +
           '" width="' + GB + '" height="' + (GY1 - H0) + '"/>' +
         '<rect fill="var(--nat)" opacity=".22" x="' + GX + '" y="' + H1 +
           '" width="' + GB + '" height="' + (H0 - H1) + '"/>' +
         '<path class="f-lijn" d="M' + GX + ' ' + H0 + ' L' + (GX + GB + 8) + ' ' + H0 + '"/>' +
         '<path class="f-norm" d="M' + GX + ' ' + H1 + ' L' + (GX + GB + 8) + ' ' + H1 + '"/>' +
         '<text class="f-tekst klein" x="' + (GX + GB + 14) + '" y="' + (H0 + 4) + '">nu</text>' +
         '<text class="f-tekst klein" x="' + (GX + GB + 14) + '" y="' + (H1 + 4) + '">straks</text>' +
         '<text class="f-tekst klein" x="' + (GX + GB / 2) + '" y="' + (GY1 + 20) +
           '" text-anchor="middle">de stand</text>';

    // HEEN: de maatregel is bekend, de stand is de vraag
    t += '<g class="f-deel aan" data-deel="0">' +
         '<path class="i-pijl" d="M320 132 C 370 120, 386 120, 416 128"/>' +
         '<path class="i-pijl" d="M406 120 L418 128 L404 134"/>' +
         '<text class="f-tekst sterk" x="366" y="106" text-anchor="middle">heen</text>' +
         '<circle class="i-bindend" cx="' + (GX + GB / 2) + '" cy="' + ((H0 + H1) / 2) +
           '" r="40"/>' +
         '<text class="f-tekst klein" x="90" y="290">geef de maatregel,</text>' +
         '<text class="f-tekst sterk" x="90" y="308">en dit wordt de stand</text>' +
         '</g>';

    // TERUG: de stand is gewenst, de maatregel is de vraag
    t += '<g class="f-deel" data-deel="1">' +
         '<path class="i-pijl droog" d="M416 208 C 386 220, 370 220, 320 206"/>' +
         '<path class="i-pijl droog" d="M332 198 L318 206 L334 212"/>' +
         '<text class="f-tekst sterk droog" x="366" y="236" text-anchor="middle">terug</text>' +
         '<circle class="i-bindend" cx="' +
           iso(BERG_X, BERG_Y, MX, MY, S)[0].toFixed(1) + '" cy="' +
           iso(BERG_X, BERG_Y, MX, MY, S)[1].toFixed(1) + '" r="34"/>' +
         '<text class="f-tekst klein droog" x="380" y="290">geef de gewenste stand,</text>' +
         '<text class="f-tekst sterk droog" x="380" y="308">en dit is de maatregel</text>' +
         '</g>';

    return t + '</svg>';
  })();

  // ── de twee statistieken, als vorm ───────────────────────────────────────
  //
  // Het verschil tussen de twee IS de stap. De natte statistiek varieert de
  // GEBEURTENIS - dezelfde zomer, drie buiduren. De droge varieert het KLIMAAT
  // - hetzelfde groeiseizoen, zeven toekomsten. Padjes gegenereerd met
  // scripts/gen_statistiek.py.
  function statistiekAssen(labels, eenheid, top) {
    var X0 = 96, X1 = 520, Y0 = 44, Y1 = 250;
    var t = '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X1 + ' ' + Y1 + '"/>' +
            '<path class="f-lijn" d="M' + X0 + ' ' + Y0 + ' L' + X0 + ' ' + Y1 + '"/>' +
            '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y0 - 12) + '">' + eenheid + '</text>' +
            '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y1 + 4) +
              '" text-anchor="end">0</text>' +
            '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y0 + 6) +
              '" text-anchor="end">' + top + '</text>' +
            '<text class="f-tekst klein" x="308" y="' + (Y1 + 38) +
              '" text-anchor="middle">terugkeertijd [jaar]</text>';
    labels.forEach(function (l) {
      t += '<text class="f-tekst klein" x="' + l[0] + '" y="' + (Y1 + 20) +
           '" text-anchor="middle">' + l[1] + '</text>';
    });
    return t;
  }

  var neerslagstatistiek =
    '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
    statistiekAssen([[96, "\u00bd"], [263, "10"], [520, "1000"]], "neerslag [mm]", "150") +
    '<g class="f-deel aan" data-deel="0">' +
    '  <path class="c-lijn nat" d="M96.0 210.2 L134.7 201.9 L173.3 192.3 L224.4 180.0 L263.1 169.0 L301.8 159.4 L314.2 155.2 L352.9 144.3 L391.6 131.1 L430.2 117.5 L442.7 113.1 L481.3 98.8 L520.0 84.0"/>' +
    '  <text class="f-tekst sterk nat" x="532" y="88">4 dagen</text>' +
    '</g>' +
    '<g class="f-deel" data-deel="1">' +
    '  <path class="c-lijn" d="M96.0 228.0 L134.7 219.8 L173.3 211.5 L224.4 200.6 L263.1 190.9 L301.8 181.3 L314.2 177.2 L352.9 166.2 L391.6 152.9 L430.2 138.6 L442.7 133.8 L481.3 118.2 L520.0 101.4"/>' +
    '  <text class="f-tekst sterk" x="532" y="105">2 dagen</text>' +
    '</g>' +
    '<g class="f-deel" data-deel="2">' +
    '  <path class="c-lijn accent" d="M96.0 185.5 L134.7 174.5 L173.3 163.5 L224.4 149.7 L263.1 138.8 L301.8 127.8 L314.2 123.7 L352.9 114.0 L391.6 101.5 L430.2 89.0 L442.7 84.9 L481.3 72.4 L520.0 59.9"/>' +
    '  <text class="f-tekst sterk accent" x="532" y="64">8 dagen</text>' +
    '  <text class="f-tekst klein" x="532" y="140">dezelfde zomer,</text>' +
    '  <text class="f-tekst klein" x="532" y="156">drie buiduren</text>' +
    '</g>' +
    '</svg>';

  var droogtestatistiek =
    '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
    statistiekAssen([[96, "2"], [270, "10"], [520, "100"]], "neerslagtekort [mm]", "600") +
    '<g class="f-deel aan" data-deel="0">' +
    '  <path class="i-band" d="M96.0 200.3 L195.3 180.8 L270.4 168.6 L369.7 153.9 L444.9 143.6 L520.0 133.7 L520.0 113.2 L444.9 123.2 L369.7 134.2 L270.4 150.1 L195.3 162.8 L96.0 184.4 Z"/>' +
    '  <path class="c-lijn" d="M96.0 188.1 L195.3 166.8 L270.4 154.3 L369.7 140.1 L444.9 130.6 L520.0 122.1"/>' +
    '  <text class="f-tekst sterk" x="532" y="126">nu</text>' +
    '  <text class="f-tekst klein" x="532" y="142">21 waterschappen</text>' +
    '</g>' +
    '<g class="f-deel" data-deel="1">' +
    '  <path class="c-lijn slecht" d="M96.0 132.1 L195.3 101.9 L270.4 87.7 L369.7 74.5 L444.9 67.1 L520.0 61.4"/>' +
    '  <text class="f-tekst sterk nadruk" x="532" y="65">2100, droog</text>' +
    '  <text class="f-tekst klein nadruk" x="532" y="81">hoge uitstoot</text>' +
    '  <text class="f-tekst klein" x="532" y="188">hetzelfde seizoen,</text>' +
    '  <text class="f-tekst klein" x="532" y="204">zeven toekomsten</text>' +
    '</g>' +
    '</svg>';

  var FIGUREN = {

    polder_animatie: polderAnimatie,

    neerslagstatistiek: neerslagstatistiek,
    droogtestatistiek: droogtestatistiek,
    frequentielijn: frequentielijn,
    maatregelcurves: maatregelcurves,
    topdown_bui: topdownBui,
    topdown_droogte: topdownDroogte,
    tweerichting: tweerichting,
    topdown_polder: topdownPolder,
    topdown_netwerk: topdownNetwerk,

    // Gewone taal, geen vaktermen uit de robotica. Een hydroloog weet niet wat
    // "starre lichamen en contact" of "MuJoCo" is, en hoeft dat ook niet te
    // weten om dit schema te snappen.
    wereldmodel_robot: wereldmodel({
      wie: "de microduck",
      transitie: "de natuurkunde van lopen",
      hoe: "iemand heeft die opgeschreven",
      policy: "die heeft hij, en hij is geleerd",
      actie1: "hoe hij zijn motoren zet,",
      actie2: "vijftig keer per seconde",
      exogeen1: "de vloer, de wrijving,",
      exogeen2: "zijn batterij",
      beloning1: "vooruit komen,",
      beloning2: "en niet omvallen",
      ppo: "en zo heeft hij leren lopen",
    }),

    wereldmodel_polder: wereldmodel({
      wie: "de polder",
      transitie: "de waterbalans",
      hoe: "iemand heeft die opgeschreven",
      policy: "die hebben wij niet",
      actie1: "welke maatregel,",
      actie2: "en in welk jaar",
      exogeen1: "de bui,",
      exogeen2: "de droogte",
      beloning1: "schade voorkomen,",
      beloning2: "zo goedkoop mogelijk",
      ppo: "en die stap hebben wij nog niet gezet",
    }),

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

    // deel 0 = optimize, 1 = de policy, 2 = de toets tussen die twee
    keuze:
      '<svg viewBox="0 0 620 290" preserveAspectRatio="xMidYMid meet">' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <text class="f-tekst sterk" x="22" y="34">de zoeker</text>' +
      '    <rect class="f-vlak" x="22" y="46" width="82" height="48" rx="7"/>' +
      '    <text class="f-tekst klein" x="63" y="70" text-anchor="middle">één polder,</text><text class="f-tekst klein" x="63" y="84" text-anchor="middle">één bui</text>' +
      '    <path class="f-ink" d="M104 70 L146 70"/>' +
      '    <path class="f-ink" d="M138 64 L148 70 L138 76"/>' +
      '    <rect class="f-vlak" x="148" y="42" width="124" height="56" rx="7"/>' +
      '    <text class="f-tekst sterk" x="210" y="66" text-anchor="middle">31 combinaties</text>' +
      '    <text class="f-tekst klein" x="210" y="84" text-anchor="middle">elk exact opgelost</text>' +
      '    <path class="f-ink" d="M272 70 L314 70"/>' +
      '    <path class="f-ink" d="M306 64 L316 70 L306 76"/>' +
      '    <circle cx="334" cy="70" r="7" fill="var(--accent)"/>' +
      '    <text class="f-tekst sterk" x="356" y="66">één punt</text>' +
      '    <text class="f-tekst klein" x="356" y="84">overal hetzelfde getal</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <text class="f-tekst sterk" x="22" y="196">een policy</text>' +
      '    <rect class="f-vlak" x="22" y="208" width="82" height="48" rx="7"/>' +
      '    <text class="f-tekst klein" x="63" y="232" text-anchor="middle">alle</text><text class="f-tekst klein" x="63" y="246" text-anchor="middle">polders</text>' +
      '    <path class="f-ink" d="M104 232 L146 232"/>' +
      '    <path class="f-ink" d="M138 226 L148 232 L138 238"/>' +
      '    <rect class="f-vlak" x="148" y="204" width="124" height="56" rx="7"/>' +
      '    <text class="f-tekst sterk" x="210" y="228" text-anchor="middle">training</text>' +
      '    <text class="f-tekst klein" x="210" y="246" text-anchor="middle">in het model</text>' +
      '    <path class="f-ink" d="M272 232 L314 232"/>' +
      '    <path class="f-ink" d="M306 226 L316 232 L306 238"/>' +
      '    <path class="f-droog" d="M326 250 C 344 250, 348 214, 370 214 C 392 214, 396 230, 414 230"/>' +
      '    <text class="f-tekst sterk" x="356" y="200">een functie</text>' +
      '    <text class="f-tekst klein" x="440" y="240">ook voor een ongeziene polder</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-lijn" stroke-dasharray="4 4" d="M334 98 L334 200"/>' +
      '    <text class="f-tekst sterk" x="348" y="144">op één jaar horizon</text>' +
      '    <text class="f-tekst klein" x="348" y="162">moeten ze hetzelfde zeggen</text>' +
      '  </g>' +
      '</svg>',
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Tekenen
  // ─────────────────────────────────────────────────────────────────────────
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

    function chip(stap) {
      var b = el("button", "lid");
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

  function rijenTabel(stap) {
    var tabel = el("table", "rijen");
    var body = el("tbody");
    stap.rijen.forEach(function (rij) {
      var tr = el("tr");
      tr.appendChild(el("td", "veld", rij[0]));
      tr.appendChild(el("td", "waarde", rij[1]));
      tr.appendChild(el("td", "uitleg", rij[2]));
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
      titelEl.replaceChildren(el("div", "titelkop", beat.kop),
                              el("div", "titelonder", beat.onder));
      n.replaceChildren(titelEl);
      return;
    }

    zijdeEl.replaceChildren(
      el("div", "glyph", stap.sym),
      el("div", "stap-titel", stap.titel),
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

  function teken() {
    var post = BEATS[nu];
    kopEl.replaceChildren.apply(kopEl, Array.prototype.slice.call(kop(post.stap).childNodes));
    vulToneel(toneelEl, post.stap, post.beat);
    alleenDezeMagSpelen();
    voetEl.replaceChildren.apply(voetEl, Array.prototype.slice.call(voet(post).childNodes));
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
