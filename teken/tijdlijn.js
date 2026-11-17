// ═══════════════════════════════════════════════════════════════════════════
// De tijdlijn, en de titel waarmee de talk eindigt.
// ═══════════════════════════════════════════════════════════════════════════
//
// De tijdlijn zegt waar deze talk vandaan komt: vier momenten, met boven de
// eerste twee een plaatje van wat er toen stond. De titelwissel zegt waar hij
// heen gaat: de titel waarmee we binnenkwamen, en de richting erna.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  // x op de lijn, wanneer, en de regels eronder.
  var MOMENTEN = [
    [78, "March 2025", ["white paper: agents", "in the water sector"]],
    [245, "November 2025", ["Hydrology Software", "Days 2025", "the inverse question"]],
    [412, "2026", ["agents that talk with", "FEWS, WISKI, D-HYDRO"]],
    [579, "November 2026", ["Hydrology Software", "Days 2026"]],
  ];
  var LIJN_Y = 212;

  // Een plaatje hangt boven het moment waar het bij hoort, met een lijntje naar
  // de tijdlijn. Twee naast elkaar passen alleen op deze breedte.
  var PLATEN = [[78, "delta-agents-site.jpg"], [245, "dsd-2025-titel.jpg"]];
  var PLAAT_B = 150, PLAAT_H = 84, PLAAT_Y = 66;

  function plaat(p) {
    var x = p[0] - PLAAT_B / 2, maten = ' x="' + x + '" y="' + PLAAT_Y +
            '" width="' + PLAAT_B + '" height="' + PLAAT_H + '"';
    return '<image href="' + p[1] + '"' + maten + ' preserveAspectRatio="xMidYMid slice"/>' +
           '<rect class="f-lijn"' + maten + '/>' +
           '<path class="f-lijn" d="M' + p[0] + ' ' + (PLAAT_Y + PLAAT_H) +
             ' L' + p[0] + ' ' + (LIJN_Y - 8) + '"/>';
  }

  function moment(m, vandaag) {
    var t = '<circle class="' + (vandaag ? "c-optimum" : "f-knoop") + '" cx="' + m[0] + '" cy="' + LIJN_Y + '" r="7"/>' +
            '<text class="f-tekst sterk' + (vandaag ? " droog" : "") + '" x="' + m[0] + '" y="' + (LIJN_Y + 30) +
              '" text-anchor="middle">' + m[1] + '</text>';
    m[2].forEach(function (regel, i) {
      t += '<text class="f-tekst klein" x="' + m[0] + '" y="' + (LIJN_Y + 52 + i * 18) +
           '" text-anchor="middle">' + regel + '</text>';
    });
    return t;
  }

  function tijdlijn() {
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet">' +
            '<g class="f-deel aan" data-deel="0">' +
            '<path class="f-lijn" style="stroke-width:3" d="M20 ' + LIJN_Y + ' L640 ' + LIJN_Y + '"/>';
    PLATEN.forEach(function (p) { t += plaat(p); });
    MOMENTEN.slice(0, 3).forEach(function (m) { t += moment(m, false); });
    t += '</g><g class="f-deel" data-deel="1">' + moment(MOMENTEN[3], true) + '</g>';
    return t + '</svg>';
  }

  // De titel waarmee we binnenkwamen blijft staan; eronder komt de richting
  // waar we heen gaan, en dat is de enige bewering op deze plaat.
  var GROOT = ' style="font-size:calc(clamp(20px, 2.1vw, 64px) * var(--px, 1))"';

  function titelwissel() {
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
      '<g class="f-deel aan" data-deel="0">' +
      '<text class="f-tekst klein" x="12" y="70">we came in with</text>' +
      '<text class="f-tekst" x="12" y="100">From robots to polders: world models in hydrology</text>' +
      '</g>' +
      '<g class="f-deel" data-deel="1">' +
      '<text class="f-tekst klein" x="12" y="172">we leave with</text>';
    ["Towards agent-native modelling",
     "and validation infrastructure",
     "for strategic water management"].forEach(function (regel, i) {
      t += '<text class="f-tekst sterk accent"' + GROOT + ' x="12" y="' + (214 + i * 34) +
           '">' + regel + '</text>';
    });
    return t + '</g></svg>';
  }

  T.tijdlijn = tijdlijn();
  T.titelwissel = titelwissel();
})(TEKEN);
