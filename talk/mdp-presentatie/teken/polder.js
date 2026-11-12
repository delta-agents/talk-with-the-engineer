// ═══════════════════════════════════════════════════════════════════════════
// De polder, getekend. Van boven in 2,5D, en in beweging.
// ═══════════════════════════════════════════════════════════════════════════
//
// Alles hier staat op dezelfde projectie uit `iso.js`, en dat is geen
// zuinigheid: de zaal ziet dezelfde polder terug bij de maatregelen, in het
// netwerk, bij nat en droog en onder de frequentielijn. Zodra één plaat zijn
// eigen ruiten plaatst, lopen ze uit elkaar bij de eerste maatverandering.
//
// De standen in de animatie komen uit de rekenkern; de keyframes staan
// gegenereerd in `gegenereerd.css`.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  var iso = T.iso,
      isoVlak = T.isoVlak,
      isoPlaat = T.isoPlaat,
      isoEllips = T.isoEllips,
      isoPijl = T.isoPijl;

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
    '  <text class="f-tekst sterk" x="452" y="131">the peak: 36 cm</text>' +
    '  <path class="f-norm" d="M150 154 L440 154"/>' +
    '  <text class="f-tekst norm" x="452" y="162">flooding standard</text>' +
    '  <text class="f-tekst klein" x="452" y="179">30 cm rise</text>' +
    '  <path class="f-lijn" stroke-dasharray="6 5" d="M150 250 L440 250"/>' +
    '  <text class="f-tekst klein" x="452" y="254">target level</text>' +

    // het gemaal: draait mee met wat de balans er werkelijk uit haalt
    '  <g class="p-gemaal">' +
    '    <path class="f-nat" d="M400 286 L516 286"/>' +
    '    <path class="f-nat" d="M508 280 L518 286 L508 292"/>' +
    '    <text class="f-tekst klein" x="452" y="306">the pumping station</text>' +
    '  </g>' +

    // de dagteller, zodat je ziet waar in de bui je bent
    '  <path class="f-lijn" d="M170 322 L430 322"/>' +
    '  <text class="f-tekst klein" x="170" y="338">day 1</text>' +
    '  <text class="f-tekst klein" x="430" y="338" text-anchor="end">day 9</text>' +
    '  <g class="p-dag"><circle cx="170" cy="322" r="5" fill="var(--nadruk)"/></g>' +
    '</svg>';


  // De vijver van bergen, in plaatcoördinaten: rechtsvoor, aan de andere kant
  // van de watergang dan vasthouden, zodat de twee elkaar niet raken.
  var BERG_X = 0.76, BERG_Y = 0.20, BERG_R = 0.155;

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

  // Dezelfde polder als in de bui, klein: land, watergang, vasthouden en
  // bergen. Zo herkent de zaal het beeld van het begin terug.
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
  // Ze staan boven elkaar op één plaat, als twee delen: eerst de ketting, dan
  // komt de verdeling eronder bij en blijft de ketting staan. Het verschil ís
  // het punt, en dat verschil is de reden dat er twee gereedschappen zijn.
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
    var t = '<svg viewBox="0 0 920 520" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
            '<g class="f-deel aan" data-deel="0">';

    // ── boven: de ketting ────────────────────────────────────────────────
    var nat = trio(30);
    t += '<text class="f-tekst sterk nat" x="616" y="70">wet: a chain</text>' +
         '<text class="f-tekst klein" x="616" y="92">what A pumps out is what B receives</text>' +
         platen(nat) +
         isoPijl(uit(nat[0]), in_(nat[1]), "i-pijl nat") +
         isoPijl(uit(nat[1]), in_(nat[2]), "i-pijl nat") +
         isoPijl(uit(nat[2]), [uit(nat[2])[0] + 74, uit(nat[2])[1] - 26], "i-pijl nat") +
         '<text class="f-tekst klein" x="' + (uit(nat[2])[0] + 26) + '" y="' +
           (uit(nat[2])[1] - 36) + '">outside</text>' +
         // De knoop in het midden krijgt zijn water niet weg omdat het
         // benedenstrooms al vol staat. Een groter gemaal helpt daar niets.
         '<circle class="i-bindend" cx="' + nat[1].mx + '" cy="' +
           iso(0.5, 0.5, nat[1].mx, nat[1].my, S)[1].toFixed(1) + '" r="34"/>' +
         '<text class="f-tekst norm" x="' + nat[1].mx + '" y="' + (nat[1].my + 108) +
           '" text-anchor="middle">possible bottleneck here</text>' +
         '</g><g class="f-deel" data-deel="1">';

    // ── onder: de verdeling ──────────────────────────────────────────────
    var droog = trio(290);
    var bron = { mx: 150, my: 428 };
    t += '<text class="f-tekst sterk droog" x="600" y="322">dry: an allocation</text>' +
         '<text class="f-tekst klein" x="600" y="344">all three draw on the same source</text>' +
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
           '" text-anchor="middle">source</text>';
    droog.forEach(function (k) {
      t += isoPijl(iso(0.5, 0, bron.mx, bron.my, 46), iso(0.5, 1, k.mx, k.my, S), "i-pijl droog");
    });
    // de verdringingsreeks: vier schillen, en de onderste vallen als eerste droog
    var sx = 600, sy = 402;
    ["safety", "utilities", "high-value use", "other"].forEach(function (naam, i) {
      var valt = i >= 2;
      t += '<rect class="i-schil' + (valt ? " droog" : "") + '" x="' + sx + '" y="' +
             (sy + i * 22) + '" width="18" height="15"/>' +
           '<text class="f-tekst klein' + (valt ? " uit" : "") + '" x="' + (sx + 26) +
             '" y="' + (sy + i * 22 + 12) + '">' + naam + '</text>';
    });
    t += '<text class="f-tekst norm" x="' + sx + '" y="' + (sy - 12) + '">the priority sequence</text>';
    return t + '</g></svg>';
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
    '<text class="f-tekst klein norm" x="574" y="117">pump</text>' +
    // De liniaal loopt op dezelfde klok als de dagteller op de balk eronder, en
    // over dezelfde 260 eenheden: samen zijn ze één leeswijzer.
    '<g class="p-dag"><path class="g-nu" d="M570 30 L570 150"/></g>' +
    '<text class="f-tekst klein" x="570" y="22">growing shortfall in discharge capacity</text>';

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
    '<text class="f-tekst klein" x="570" y="274">growing shortfall in supply</text>';


  // ── de polder van boven, nat en droog ────────────────────────────────────
  //
  // Twee bewegende platen op dezelfde projectie: wat er gebeurt als het te
  // hard regent, en wat er gebeurt als het te lang droog blijft. Ze delen één
  // tekenvlak; elke plaat knipt met zijn viewBox zijn eigen helft eruit.
  //
  // Van boven zie je geen diepte, dus een stijgend peil is onzichtbaar zolang
  // het in de watergang past. Wat je WEL ziet is het moment dat het eroverheen
  // gaat: dan zwelt de watergang en loopt het land onder. Droog krimpt dezelfde
  // watergang bínnen zijn oevers en droogt het land op.
  //
  // De TIJD en het PEIL komen uit de rekenkern. De breedte van de overstroming
  // is een proportionele afbeelding van de overschrijding en dus illustratief:
  // het model geeft een stand, geen inundatiecontour.
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
      '</g>';
  }

  function bijVijver(my, klasse, woord) {
    var m = iso(BERG_X, BERG_Y, MX, my, S);
    return '<text class="f-tekst ' + klasse + '" x="' + (m[0] + 44) + '" y="' + (m[1] - 22) + '">' + woord + '</text>';
  }

  // Nat, negen dagen bui. Deel 1 legt de drie maatregelen tegen wateroverlast
  // op dezelfde polder, elk naast de plek waar hij ingrijpt.
  var topdownNat = (function () {
    var t = '<svg viewBox="0 0 880 236" preserveAspectRatio="xMidYMid meet"' +
            ' class="polder-animatie f-hard"><g class="f-deel aan" data-deel="0">';

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

    // Het gemaal heeft hier geen bijschrift: de grafiek ernaast noemt het al.
    var gemaal = iso(1, 0.5, MX, NAT, S), uit = iso(1.62, 0.5, MX, NAT, S);
    t += '<g class="p-gemaal">' + isoPijl(gemaal, uit, "i-pijl nat") + '</g>';

    t += '<text class="f-tekst norm" x="16" y="28">impact of flooding</text>' +
         NEERSLAG_AFVOER +
         '<path class="f-lijn" d="M' + BAR0 + ' 170 L' + BAR1 + ' 170"/>' +
         '<text class="f-tekst klein" x="' + BAR0 + '" y="188">day 1</text>' +
         '<text class="f-tekst klein" x="' + BAR1 + '" y="188" text-anchor="end">day 9</text>' +
         '<g class="p-dag"><circle cx="' + BAR0 + '" cy="170" r="5" fill="var(--nadruk)"/></g>' +
         '</g>';

    t += '<g class="f-deel" data-deel="1">' +
         '<path class="i-retentie" d="' + isoVlak(0.06, 0.62, 0.52, 0.95, MX, NAT, S) + '"/>' +
         '<text class="f-tekst norm" x="' + (MX - 134) + '" y="' + (NAT + 96) +
           '" text-anchor="end">retain</text>' +
         bijVijver(NAT, "norm", "store") +
         isoPijl(gemaal, uit, "i-pijl dik") +
         '<text class="f-tekst norm" x="' + (uit[0] + 10) + '" y="' + (uit[1] + 4) + '">discharge</text>' +
         '</g>';

    return t + '</svg>';
  })();

  // Droog, een half groeiseizoen. Eigen klok, en die staat op DEZE groep:
  // `p-seizoen` op de hele plaat zou de bui ook op de seizoensduur zetten.
  //
  // De buffer is leeg na 9,9 van de 183 dagen: een streepje op die plek maakt
  // elk bevroren frame leesbaar, want daarna verandert alleen het land nog.
  var topdownDroog = (function () {
    var leeg = BAR0 + (BAR1 - BAR0) * 9.9 / 183;
    var buiten = iso(-0.62, 0.5, MX, DROOG, S);
    return '<svg viewBox="0 236 880 236" preserveAspectRatio="xMidYMid meet" class="polder-animatie">' +
      '<g class="p-seizoen">' +
      isoPlaat(MX, DROOG, S, DIK) +
      '<path class="i-dorst p-dorst" d="' + isoVlak(0, 0, 1, 1, MX, DROOG, S) + '"/>' +
      '<path class="i-water p-droogte" d="' + isoVlak(0, 0.45, 1, 0.55, MX, DROOG, S) + '"/>' +
      berging(DROOG, "p-bergingdroog") + bijVijver(DROOG, "klein", "storage") +
      // De inlaat staat gestippeld: wat er binnenkomt hangt af van wat de
      // gedeelde bron nog geeft, en die verdeelt de verdringingsreeks.
      isoPijl(buiten, iso(0, 0.5, MX, DROOG, S), "i-pijl leeg") +
      '<text class="f-tekst klein" x="' + (buiten[0] + 6) + '" y="' + (buiten[1] + 22) +
        '">supply, if the source allows</text>' +
      '<text class="f-tekst norm" x="16" y="252">impact of water shortage</text>' +
      TEKORT_EN_VOORRAAD +
      '<path class="f-lijn" d="M' + BAR0 + ' 430 L' + BAR1 + ' 430"/>' +
      '<path class="f-norm" d="M' + leeg.toFixed(1) + ' 422 L' + leeg.toFixed(1) + ' 438"/>' +
      '<text class="f-tekst norm" x="' + (leeg + 8).toFixed(1) + '" y="452">buffer empty</text>' +
      '<text class="f-tekst klein" x="' + BAR0 + '" y="416">1 April</text>' +
      '<text class="f-tekst klein" x="' + BAR1 + '" y="416" text-anchor="end">1 October</text>' +
      '<g class="p-dag"><circle cx="' + BAR0 + '" cy="430" r="5" fill="var(--nadruk)"/></g>' +
      '</g></svg>';
  })();


  // ── wat dit bestand levert ────────────────────────────────────────────────
  // De drie curven hierboven blijven binnen: ze zijn de vulling van de natte en
  // droge plaat en geen figuur op zichzelf.
  T.BERG_X = BERG_X;
  T.BERG_Y = BERG_Y;
  T.BERG_R = BERG_R;
  T.polderAnimatie = polderAnimatie;
  T.topdownNetwerk = topdownNetwerk;
  T.topdownNat = topdownNat;
  T.topdownDroog = topdownDroog;
  T.ICOON_ROBOT = ICOON_ROBOT;
  T.ICOON_POLDER = ICOON_POLDER;
})(TEKEN);
