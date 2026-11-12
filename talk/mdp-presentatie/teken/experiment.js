// ═══════════════════════════════════════════════════════════════════════════
// Het experiment: drie polders, één agent, twaalf tools.
// ═══════════════════════════════════════════════════════════════════════════
//
// Drie platen. De opzet zegt wat er in ging: een gebied met een gepubliceerd
// rapport, de vraag van dat rapport, en een agent met de gereedschapskist. Het
// tempo zegt hoe de agent zocht: per gebied de aanroepen op volgorde, en hoe
// lang hij ermee bezig was. De grens zegt wat we daaruit leren: waar de agent
// staat tussen alles doorrekenen en haast, en waar we hem willen hebben.
//
// Alles komt uit de sessielog van het experiment in talk/mdp-usecases.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  // Per gebied: de kaart met zijn breedte, hoogte en de hoogte zonder legenda, een regel over het
  // gebied, het doel van de studie, en de vraag die hij beantwoordt.
  var GEBIEDEN = [
    ["Gnephoek", "kaart-gnephoek.svg", [980, 1022, 920], "Alphen · 5,500 new homes",
     "objective: size the open water", ["how much keeps the rise", "below 50 cm?"]],
    ["Zuidplaspolder", "kaart-zuidplas.svg", [1000, 1271, 1170], "Zuidplas · 8,000 new homes",
     "objective: test a pumping stop", ["how high does the water", "come if pumps must stop?"]],
    ["Kockengen", "kaart-detol.svg", [1000, 1147, 1050], "De Tol · 28 July 2014",
     "objective: evaluate a real flood", ["was the pumping station", "too small?"]],
  ];
  var KOLOM = 216;

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

  // Boven de drie gebieden naast elkaar; onder gaat elke vraag naar de agent,
  // die de tools aanroept en een antwoord geeft dat naast dat van de studie komt.
  function opzet() {
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet">' +
            '<g class="f-deel aan" data-deel="0">';
    GEBIEDEN.forEach(function (g, i) {
      var x = 12 + i * KOLOM, midden = x + (KOLOM - 12) / 2;
      t += '<svg x="' + x + '" y="4" width="' + (KOLOM - 12) + '" height="104" viewBox="0 0 ' + g[2][0] + ' ' + g[2][2] + '"' +
             ' preserveAspectRatio="xMidYMid meet"><image href="' + g[1] + '" width="' + g[2][0] +
             '" height="' + g[2][1] + '"/></svg>' +
           '<text class="f-tekst sterk" x="' + x + '" y="132">' + g[0] + '</text>' +
           '<text class="f-tekst klein" x="' + x + '" y="150">' + g[3] + '</text>' +
           '<text class="f-tekst klein" x="' + x + '" y="168">' + g[4] + '</text>' +
           g[5].map(function (regel, j) {
             return '<text class="f-tekst sterk nadruk" x="' + x + '" y="' + (190 + j * 18) + '">' + regel + '</text>';
           }).join("") +
           pijl("f-accent", midden, 220, 330 + (i - 1) * 40, 254);
    });
    t += doos(12, 256, 190, "twelve tools", "rules of thumb") +
         pijl("f-accent", 258, 280, 204, 280) +
         pijl("f-nat", 204, 296, 258, 296) +
         doos(260, 256, 140, "an agent", "a language model", "accent") +
         pijl("f-nat", 402, 287, 456, 287) +
         doos(458, 256, 190, "its answer", "next to the study’s") +
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

  // De grens: een lijn van alles doorrekenen naar het eerste antwoord dat past.
  // De agent staat vandaag dicht bij de haast; wat we willen ligt ertussen.
  var AS_Y = 150;

  function regels(x, y, kop, tint, lijst) {
    return '<text class="f-tekst sterk ' + tint + '" x="' + x + '" y="' + y + '">' + kop + '</text>' +
           lijst.map(function (r, i) {
             return '<text class="f-tekst" x="' + x + '" y="' + (y + 28 + i * 24) + '">' + r + '</text>';
           }).join("");
  }

  function grens() {
    return '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
      '<g class="f-deel aan" data-deel="0">' +
      '<path class="f-lijn" style="stroke-width:3" d="M60 ' + AS_Y + ' L600 ' + AS_Y + '"/>' +
      '<circle class="f-knoop" cx="60" cy="' + AS_Y + '" r="7"/>' +
      '<circle class="f-knoop" cx="600" cy="' + AS_Y + '" r="7"/>' +
      '<text class="f-tekst sterk" x="40" y="' + (AS_Y - 24) + '">brute force</text>' +
      '<text class="f-tekst klein" x="40" y="' + (AS_Y + 32) + '">every tool, every node</text>' +
      '<text class="f-tekst sterk" x="620" y="' + (AS_Y - 24) + '" text-anchor="end">rushing</text>' +
      '<text class="f-tekst klein" x="620" y="' + (AS_Y + 32) + '" text-anchor="end">the first answer that fits</text>' +
      '</g>' +
      '<g class="f-deel" data-deel="1">' +
      pijl("f-nadruk", 540, 62, 540, AS_Y - 12) +
      '<text class="f-tekst sterk nadruk" x="540" y="52" text-anchor="middle">the agent, today</text>' +
      '<circle cx="540" cy="' + AS_Y + '" r="9" style="fill:var(--nadruk);stroke:var(--grond);stroke-width:2"/>' +
      regels(12, 236, "what we see", "nadruk",
             ["tools used in ways we did not design", "not very thorough", "settles for a solution quickly"]) +
      '</g>' +
      '<g class="f-deel" data-deel="2">' +
      '<rect x="220" y="' + (AS_Y - 14) + '" width="200" height="28" rx="14"' +
        ' style="fill:var(--accent);fill-opacity:.18;stroke:var(--accent);stroke-width:2.5"/>' +
      '<text class="f-tekst sterk accent" x="320" y="' + (AS_Y - 24) + '" text-anchor="middle">what we want</text>' +
      regels(360, 236, "in between", "accent",
             ["what does a measure give?", "what is left?", "what can still do it?"]) +
      '</g>' +
      '</svg>';
  }

  T.experimentOpzet = opzet();
  T.experimentTempo = tempo();
  T.experimentGrens = grens();
})(TEKEN);
