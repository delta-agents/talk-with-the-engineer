// ═══════════════════════════════════════════════════════════════════════════
// Het experiment: drie polders, één agent, twaalf tools.
// ═══════════════════════════════════════════════════════════════════════════
//
// Twee platen. De opzet zegt wat er in ging: een gebied met een gepubliceerd
// rapport, de vraag van dat rapport, en een agent met de gereedschapskist. Het
// tempo zegt hoe de agent zocht: per gebied de aanroepen op volgorde, en hoe
// lang hij ermee bezig was.
//
// Alles komt uit de sessielog van het experiment in talk/mdp-usecases.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  // gebied, jaar van het rapport, en de vraag in een paar woorden.
  var GEBIEDEN = [
    ["Gnephoek", "study of 2023", "how much open water?"],
    ["Zuidplaspolder", "study of 2022", "how high will it come?"],
    ["Kockengen", "the storm of 2014", "was the pump too small?"],
  ];

  function pijl(klasse, x0, y0, x1, y1) {
    var naar = Math.atan2(y1 - y0, x1 - x0), a = 0.5, l = 10;
    return '<path class="' + klasse + '" d="M' + x0 + ' ' + y0 + ' L' + x1 + ' ' + y1 + '"/>' +
           '<path class="' + klasse + '" d="M' + (x1 - l * Math.cos(naar - a)).toFixed(1) + ' ' +
             (y1 - l * Math.sin(naar - a)).toFixed(1) + ' L' + x1 + ' ' + y1 + ' L' +
             (x1 - l * Math.cos(naar + a)).toFixed(1) + ' ' + (y1 - l * Math.sin(naar + a)).toFixed(1) + '"/>';
  }

  function doos(x, y, breed, kop, onder, tint) {
    return '<rect class="f-vlak" x="' + x + '" y="' + y + '" width="' + breed + '" height="62" rx="7"/>' +
           '<text class="f-tekst sterk ' + (tint || "") + '" x="' + (x + breed / 2) + '" y="' + (y + 27) +
             '" text-anchor="middle">' + kop + '</text>' +
           '<text class="f-tekst klein" x="' + (x + breed / 2) + '" y="' + (y + 46) +
             '" text-anchor="middle">' + onder + '</text>';
  }

  function opzet() {
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet">' +
            '<g class="f-deel aan" data-deel="0">';
    GEBIEDEN.forEach(function (g, i) {
      var y = 36 + i * 92;
      t += '<rect class="f-vlak" x="12" y="' + y + '" width="206" height="76" rx="7"/>' +
           '<text class="f-tekst sterk" x="26" y="' + (y + 26) + '">' + g[0] + '</text>' +
           '<text class="f-tekst klein" x="26" y="' + (y + 45) + '">' + g[1] + '</text>' +
           '<text class="f-tekst klein nadruk" x="26" y="' + (y + 63) + '">' + g[2] + '</text>' +
           pijl("f-accent", 218, y + 38, 284, 150 + (i - 1) * 16);
    });
    t += doos(286, 119, 140, "an agent", "a language model", "accent") +
         pijl("f-accent", 356, 181, 356, 222) +
         pijl("f-nat", 372, 224, 372, 183) +
         doos(276, 224, 160, "twelve tools", "rules of thumb") +
         pijl("f-nat", 426, 150, 484, 150) +
         doos(486, 119, 162, "its answer", "next to the study’s") +
         '</g>';
    return t + '</svg>';
  }

  // De aanroepen per gebied, op volgorde, als letters: de handleiding, bergen,
  // afvoeren en vasthouden terug, de pakketzoeker, en de keten van gebieden.
  var SOORT = {
    m: ["manual", "var(--grijs)"],
    b: ["store", "var(--accent)"],
    a: ["discharge", "var(--accent)"],
    v: ["retain", "var(--accent)"],
    p: ["package", "var(--derde)"],
    k: ["chain", "var(--nadruk)"],
  };
  var VERLOOP = [
    ["Gnephoek", "mbavpkk", 114],
    ["Zuidplaspolder", "kkpp", 44],
    ["Kockengen", "kkpa", 20],
  ];
  var CHIP = 60, CHIP_X = 150, BREED_PER_SECONDE = 3.3;

  function tempo() {
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
            '<g class="f-deel aan" data-deel="0">' +
            '<text class="f-tekst klein" x="' + CHIP_X + '" y="26">the calls, in order</text>' +
            '<text class="f-tekst klein" x="648" y="26" text-anchor="end">time in the tools</text>';
    VERLOOP.forEach(function (rij, i) {
      var y = 46 + i * 78;
      t += '<text class="f-tekst sterk" x="12" y="' + (y + 22) + '">' + rij[0] + '</text>';
      rij[1].split("").forEach(function (letter, j) {
        var s = SOORT[letter], x = CHIP_X + j * (CHIP + 6);
        t += '<rect x="' + x + '" y="' + y + '" width="' + CHIP + '" height="32" rx="6" fill="none"' +
               ' stroke="' + s[1] + '" stroke-width="2.5"/>' +
             '<text class="f-tekst klein" style="fill:' + s[1] + '" x="' + (x + CHIP / 2) + '" y="' +
               (y + 21) + '" text-anchor="middle">' + s[0] + '</text>';
      });
      // De balk eronder is de tijd, op dezelfde schaal voor alle drie.
      t += '<rect class="i-band" x="' + CHIP_X + '" y="' + (y + 42) + '" width="' +
             (rij[2] * BREED_PER_SECONDE).toFixed(0) + '" height="8" rx="4" style="opacity:.45"/>' +
           '<text class="f-tekst sterk" x="648" y="' + (y + 22) + '" text-anchor="end">' + rij[2] + ' s</text>';
    });
    t += '</g>' +
         '<g class="f-deel" data-deel="1">' +
         '<text class="f-tekst sterk nadruk" x="12" y="296">broad the first time, then straight to an answer</text>' +
         '<text class="f-tekst sterk nadruk" x="12" y="320">not brute force — but not thorough either</text>' +
         '</g>';
    return t + '</svg>';
  }

  T.experimentOpzet = opzet();
  T.experimentTempo = tempo();
})(TEKEN);
