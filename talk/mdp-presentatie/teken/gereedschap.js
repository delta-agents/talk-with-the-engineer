// ═══════════════════════════════════════════════════════════════════════════
// Het gereedschap: de twaalf tools, en wat een agent ermee deed.
// ═══════════════════════════════════════════════════════════════════════════
//
// Eén tekening, twee vullingen. Kaal is hij de gereedschapskist: vier
// maatregelen, elk in twee richtingen, en vier tools voor wat groter is dan één
// maatregel. Met `gebruik` erbij is hij de uitkomst van het experiment: wat is
// opgepakt, hoe vaak, en wat is blijven liggen.
//
// De telling komt uit de sessielog van het experiment in talk/mdp-usecases.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  var BREED = 150, STAP = 162, LINKS = 12;

  // naam, ondertitel, en het icoon op een raster van 64.
  var MAATREGELEN = [
    ["retain", "on the land",
     '<path d="M4 46 H60"/><path d="M14 46 V34"/><path d="M14 34 q-6 -2 -6 -8 q6 0 6 8 q0 -10 8 -12 q0 8 -8 12"/>' +
     '<path d="M44 14 q-8 12 -8 18 a8 8 0 0 0 16 0 q0 -6 -8 -18 Z"/><path d="M30 54 H50" stroke-dasharray="4 4"/>'],
    ["store", "in open water",
     '<path d="M6 22 L14 46 H50 L58 22"/><path d="M12 34 q5 -4 10 0 t10 0 t10 0 t10 0"/>'],
    ["discharge", "a pumping station",
     '<path d="M8 50 V28 L20 18 L32 28 V50 Z"/><circle cx="20" cy="38" r="5"/><path d="M32 36 H54"/>' +
     '<path d="M47 29 L54 36 L47 43"/><path d="M4 50 H60"/>'],
    ["supply", "an inlet, in drought",
     '<path d="M6 32 H36"/><path d="M29 25 L36 32 L29 39"/><path d="M40 20 V44 H58"/><path d="M44 38 q4 -3 7 0 t7 0"/>'],
  ];
  var GROTER = ["areas in a chain", "sharing a shortage", "package finder", "the manual"];

  // Het experiment: per maatregel [terug, heen], en dan de vier grotere tools.
  var GEBRUIK = { richtingen: [[1, 0], [1, 0], [2, 0], [0, 0]], groter: [6, 0, 4, 1] };

  // Een tool is een pil. Zonder telling is hij neutraal; met telling is hij
  // opgepakt (omlijnd, met het aantal) of blijven liggen (gedempt).
  function pil(x, y, hoog, tekst, aantal) {
    var kaal = aantal == null, gepakt = aantal > 0;
    var t = '<g' + (kaal || gepakt ? '' : ' opacity=".38"') + '>' +
            '<rect class="f-vlak" x="' + x + '" y="' + y + '" width="' + BREED + '" height="' + hoog +
              '" rx="6"' + (gepakt ? ' style="stroke:var(--accent);stroke-width:2.5"' : '') + '/>' +
            '<text class="f-tekst' + (hoog > 30 ? ' sterk' : ' klein') + '" x="' + (x + 12) + '" y="' +
              (y + hoog / 2 + 5) + '">' + tekst + '</text>';
    if (gepakt) {
      t += '<circle class="f-knoop" cx="' + (x + BREED - 4) + '" cy="' + (y + 2) + '" r="12"/>' +
           '<text class="f-tekst sterk" style="fill:var(--grond)" x="' + (x + BREED - 4) + '" y="' +
             (y + 7) + '" text-anchor="middle">' + aantal + '</text>';
    }
    return t + '</g>';
  }

  function gereedschap(gebruik) {
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
            '<g class="f-deel aan" data-deel="0">';

    MAATREGELEN.forEach(function (m, i) {
      var x = LINKS + i * STAP;
      var tel = gebruik ? gebruik.richtingen[i] : [null, null];
      t += '<svg x="' + x + '" y="14" width="44" height="44" viewBox="0 0 64 64" fill="none"' +
             ' stroke="var(--accent)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">' +
             m[2] + '</svg>' +
           '<text class="f-tekst sterk" x="' + (x + 54) + '" y="34">' + m[0] + '</text>' +
           '<text class="f-tekst klein" x="' + (x + 54) + '" y="52">' + m[1] + '</text>' +
           pil(x, 78, 30, "level → how much?", tel[0]) +
           pil(x, 120, 30, "this much → level?", tel[1]);
    });

    t += '<path class="f-lijn" d="M' + LINKS + ' 176 L648 176"/>';
    GROTER.forEach(function (naam, i) {
      t += pil(LINKS + i * STAP, 196, 44, naam, gebruik ? gebruik.groter[i] : null);
    });
    t += '</g>';

    // De ene regel die het gebruik samenvat, als eigen deel: eerst kijken, dan lezen.
    if (gebruik) {
      t += '<g class="f-deel" data-deel="1">' +
           '<text class="f-tekst sterk nadruk" x="' + LINKS + '" y="284">' +
           'six of the twelve tools were never picked up</text>' +
           '<text class="f-tekst sterk nadruk" x="' + LINKS + '" y="308">' +
           'the chain tool six times — four of them without a chain</text>' +
           '</g>';
    }
    return t + '</svg>';
  }

  T.gereedschap = gereedschap(null);
  T.gereedschapGebruik = gereedschap(GEBRUIK);
})(TEKEN);
