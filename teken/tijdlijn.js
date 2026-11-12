// ═══════════════════════════════════════════════════════════════════════════
// De tijdlijn, en de titel waarmee de talk eindigt.
// ═══════════════════════════════════════════════════════════════════════════
//
// De tijdlijn zegt waar deze talk vandaan komt: vier momenten, met de
// titelpagina van de talk van vorig jaar erboven. De titelwissel zegt waar hij
// heen gaat: de titel waarmee we binnenkwamen, en de vraag waarmee we weggaan.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  // x op de lijn, wanneer, en drie regels eronder.
  var MOMENTEN = [
    [78, "March 2025", ["white paper: agents", "in the water sector", "and the KIN report"]],
    [245, "November 2025", ["this session, last year:", "the measures, and", "the inverse question"]],
    [412, "2026", ["agents that talk with", "FEWS, WISKI, D-HYDRO", "and open standards"]],
    [579, "November 2026", ["today: packages,", "and how agents", "use the tools"]],
  ];
  var LIJN_Y = 212;

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
            '<path class="f-lijn" style="stroke-width:3" d="M20 ' + LIJN_Y + ' L640 ' + LIJN_Y + '"/>' +
            // De titelpagina hangt boven het moment waar hij bij hoort.
            '<image href="dsd-2025-titel.jpg" x="125" y="34" width="240" height="135"' +
              ' preserveAspectRatio="xMidYMid slice"/>' +
            '<rect class="f-lijn" x="125" y="34" width="240" height="135"/>' +
            '<path class="f-lijn" d="M245 169 L245 ' + (LIJN_Y - 8) + '"/>';
    MOMENTEN.slice(0, 3).forEach(function (m) { t += moment(m, false); });
    t += '</g><g class="f-deel" data-deel="1">' + moment(MOMENTEN[3], true) + '</g>';
    return t + '</svg>';
  }

  // De oude titel staat doorgestreept; de nieuwe is geen slogan maar een
  // opdracht, met de drie eisen eronder waar een antwoord aan te toetsen is.
  function titelwissel() {
    return '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
      '<g class="f-deel aan" data-deel="0">' +
      '<text class="f-tekst klein" x="12" y="30">we came in with</text>' +
      '<text class="f-tekst" text-decoration="line-through" x="12" y="58">' +
        'From robots to polders: world models in hydrology</text>' +
      '</g>' +
      '<g class="f-deel" data-deel="1">' +
      '<text class="f-tekst klein" x="12" y="110">we leave with</text>' +
      '<text class="f-tekst sterk accent" style="font-size:calc(clamp(20px, 2.1vw, 64px) * var(--px, 1))"' +
        ' x="12" y="142">Towards validation infrastructure</text>' +
      '<text class="f-tekst sterk accent" style="font-size:calc(clamp(20px, 2.1vw, 64px) * var(--px, 1))"' +
        ' x="12" y="172">for strategic water management</text>' +
      '<text class="f-tekst sterk" x="12" y="204">open rules that a professional, a citizen and a machine</text>' +
      '<text class="f-tekst sterk" x="12" y="226">can all check a plan against</text>' +
      '<path class="f-lijn" d="M12 244 L648 244"/>' +
      '<text class="f-tekst" x="12" y="270">every answer states its assumptions</text>' +
      '<text class="f-tekst" x="12" y="294">every rule says where it stops being valid</text>' +
      '<text class="f-tekst" x="12" y="318">every tool is measured against published studies</text>' +
      '</g>' +
      '</svg>';
  }

  T.tijdlijn = tijdlijn();
  T.titelwissel = titelwissel();
})(TEKEN);
