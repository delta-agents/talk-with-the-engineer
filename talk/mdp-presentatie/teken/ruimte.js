// ═══════════════════════════════════════════════════════════════════════════
// De oplossingsruimte: twee maatregelen als assen, één eis als rand.
// ═══════════════════════════════════════════════════════════════════════════
//
// Elk punt in het vlak is een pakket: zoveel gemaal erbij, zoveel hectare
// vasthouden. De eis - de piek onder 18 cm - deelt het vlak in tweeën, en de
// rand daartussen is waar het goedkoopste pakket ligt: alles erboven haalt de
// eis ook en kost alleen meer.
//
// Het raster, de rand en het goedkoopste punt komen uit
// scripts/gen_oplossingsruimte.py - niet met de hand bijwerken.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  // Het vlak: x is afvoeren van 0 tot 0,6 m3/s, y is vasthouden van 0 tot 750 ha.
  var X0 = 110, X1 = 560, Y0 = 300, Y1 = 40;

  // 13 gemaalmaten maal 11 maten vasthouden: per rij van onder naar boven het
  // eerste raster-x waarop de eis gehaald wordt.
  var RASTER_X = [110, 147.5, 185, 222.5, 260, 297.5, 335, 372.5, 410, 447.5, 485, 522.5, 560];
  var RASTER_Y = [300, 274, 248, 222, 196, 170, 144, 118, 92, 66, 40];
  var EERSTE_DIE_HAALT = [10, 8, 7, 6, 5, 4, 4, 3, 2, 1, 1];

  var RAND =
    "M128.8 58.4 L147.5 74.5 L166.2 90.6 L185.0 106.7 L203.8 122.8 L222.5 139.0" +
    " L241.2 154.8 L260.0 171.0 L278.8 187.0 L297.5 203.3 L316.2 219.4 L335.0 235.2" +
    " L353.8 251.4 L364.4 260.6 L372.5 263.2 L391.2 269.3 L410.0 275.4 L428.8 281.6 L447.5 287.7" +
    " L466.2 293.9 L485.0 300.0";
  // De knik: 114 ha vasthouden en 0,34 m3/s gemaal, het goedkoopste pakket.
  var KNIK = [364.4, 260.6];
  // Tot hier ligt de rand binnen vier procent van die prijs: alleen een gemaal.
  var ALLEEN_GEMAAL = [485.0, 300.0];
  // Drie vaste gemaalmaten, en waar de inverse vraag op de rand landt.
  var PEILINGEN = [[185.0, 106.7], [260.0, 171.0], [335.0, 235.2]];

  function tik(x, y, tekst, anker) {
    return '<text class="f-tekst klein" x="' + x + '" y="' + y + '" text-anchor="' +
           anker + '">' + tekst + '</text>';
  }

  function oplossingsruimte() {
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    // ── de assen staan buiten elk deel: ze zijn het vlak zelf ──────────────
    t += '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X0 + ' ' + Y0 + ' L' + X1 + ' ' + Y0 + '"/>';
    [["0", 110], ["0.2", 260], ["0.4", 410], ["0.6", 560]].forEach(function (p) {
      t += tik(p[1], 318, p[0], "middle");
    });
    [["0", 300], ["250", 213.3], ["500", 126.7], ["750", 40]].forEach(function (p) {
      t += tik(100, p[1] + 4, p[0], "end");
    });
    t += tik(335, 336, "discharge: extra pumping capacity [m³/s] →", "middle") +
         '<text class="f-tekst klein" x="16" y="30">retain [ha of land] ↑</text>';

    // ── 0: de eis ──────────────────────────────────────────────────────────
    t += '<g class="f-deel aan" data-deel="0">' +
         '<text class="f-tekst sterk" x="644" y="30" text-anchor="end">' +
         'the requirement: peak below 18 cm</text></g>';

    // ── 1: brute force, elk punt doorgerekend ──────────────────────────────
    t += '<g class="f-deel" data-deel="1">';
    RASTER_Y.forEach(function (y, rij) {
      RASTER_X.forEach(function (x, kolom) {
        t += kolom >= EERSTE_DIE_HAALT[rij]
          ? '<circle class="f-knoop" cx="' + x + '" cy="' + y + '" r="5"/>'
          : '<circle class="f-lijn" cx="' + x + '" cy="' + y + '" r="4.5"/>';
      });
    });
    t += '<text class="f-tekst sterk" x="578" y="120">brute</text>' +
         '<text class="f-tekst sterk" x="578" y="140">force:</text>' +
         '<text class="f-tekst sterk accent" x="578" y="166">143</text>' +
         '<text class="f-tekst sterk accent" x="578" y="186">runs</text>' +
         '</g>';

    // ── 2: de rand, en wat erboven ligt ────────────────────────────────────
    t += '<g class="f-deel" data-deel="2">' +
         '<path class="c-vlak nat" d="' + RAND + ' L' + X1 + ' ' + Y0 + ' L' + X1 + ' ' + Y1 +
           ' L128.8 ' + Y1 + ' Z"/>' +
         '<path class="c-lijn accent" d="' + RAND + ' L' + X1 + ' ' + Y0 + '"/>' +
         '<text class="f-tekst klein" x="150" y="262">does not</text>' +
         '<text class="f-tekst klein" x="150" y="278">meet it</text>' +
         '</g>';

    // ── 3: één maatregel vast, en de inverse vraag naar de rest ────────────
    t += '<g class="f-deel" data-deel="3">';
    PEILINGEN.forEach(function (p) {
      t += '<path class="f-droog" stroke-dasharray="5 5" d="M' + p[0] + ' ' + Y0 + ' L' + p[0] + ' ' + (p[1] + 9) + '"/>' +
           '<path class="f-droog" d="M' + (p[0] - 6) + ' ' + (p[1] + 17) + ' L' + p[0] + ' ' + (p[1] + 7) +
             ' L' + (p[0] + 6) + ' ' + (p[1] + 17) + '"/>' +
           '<circle class="c-optimum" cx="' + p[0] + '" cy="' + p[1] + '" r="6"/>';
    });
    t += '<text class="f-tekst sterk droog" x="340" y="78">fix one measure,</text>' +
         '<text class="f-tekst sterk droog" x="340" y="98">ask what is left to do</text>' +
         '<text class="f-tekst" x="340" y="124">every answer lands on the edge</text>' +
         '</g>';

    // ── 4: de prijs op de rand ─────────────────────────────────────────────
    t += '<g class="f-deel" data-deel="4">' +
         '<path class="g-maat" style="stroke-width:7;stroke-linecap:round" d="M' + KNIK[0] + ' ' + KNIK[1] +
           ' L' + ALLEEN_GEMAAL[0] + ' ' + ALLEEN_GEMAAL[1] + '"/>' +
         '<circle class="c-optimum" cx="' + KNIK[0] + '" cy="' + KNIK[1] + '" r="7"/>' +
         '<text class="f-tekst sterk nadruk" x="384" y="222">cheapest: € 0.92 mln</text>' +
         '<text class="f-tekst nadruk" x="384" y="242">and within 4 %: this stretch</text>' +
         '</g>';

    // ── 5: waar de detailmodellen het overnemen ────────────────────────────
    t += '<g class="f-deel" data-deel="5">' +
         '<circle class="i-bindend" cx="' + KNIK[0] + '" cy="' + KNIK[1] + '" r="24"/>' +
         '<text class="f-tekst sterk" x="340" y="78">this close, the detailed models</text>' +
         '<text class="f-tekst sterk" x="340" y="98">and the experts take over</text>' +
         '<text class="f-tekst" x="340" y="124">Ribasim, D-HYDRO: prove it, tune it</text>' +
         '</g>';

    return t + '</svg>';
  }

  T.oplossingsruimte = oplossingsruimte();
})(TEKEN);
