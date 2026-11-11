// ═══════════════════════════════════════════════════════════════════════════
// De oplossingsruimte: een oppervlak waar je stap voor stap overheen loopt.
// ═══════════════════════════════════════════════════════════════════════════
//
// Twee maatregelen spannen een vlak op, en de hoogte van het oppervlak is hoe
// hoog het water dan nog komt. Zo werkt een ingenieur: één maatregel nemen,
// kijken wat hij oplevert, vragen wat er nog over is, en de volgende maatregel
// daarop maatvoeren. Elke stap loopt langs één as, dus langs één maatregel.
//
// De hoogtes, de rand en de twee routes komen uit
// scripts/gen_oplossingsruimte.py - niet met de hand bijwerken.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  // De piek in cm. Een rij per maat vasthouden (0 tot 750 ha in stappen van 75),
  // een kolom per gemaalmaat (0 tot 0,6 m3/s erbij in stappen van 0,05).
  var PIEK = [
    [36.0, 33.4, 30.8, 28.2, 25.6, 23.2, 21.5, 20.6, 19.7, 18.9, 18.0, 17.1, 16.3],
    [33.3, 30.7, 28.1, 25.5, 23.5, 21.8, 20.1, 18.8, 17.9, 17.0, 16.2, 15.3, 14.4],
    [30.6, 28.0, 25.6, 23.9, 22.1, 20.4, 18.7, 16.9, 16.1, 15.2, 14.3, 13.5, 12.6],
    [27.8, 25.9, 24.2, 22.5, 20.7, 19.0, 17.3, 15.6, 14.2, 13.4, 12.5, 11.6, 10.8],
    [26.3, 24.5, 22.8, 21.1, 19.3, 17.6, 15.9, 14.2, 12.4, 11.5, 10.7, 9.8, 8.9],
    [24.9, 23.1, 21.4, 19.7, 17.9, 16.2, 14.5, 12.8, 11.0, 9.7, 8.8, 8.0, 7.1],
    [23.5, 21.7, 20.0, 18.3, 16.5, 14.8, 13.1, 11.4, 9.6, 7.9, 7.0, 6.1, 5.3],
    [22.1, 20.3, 18.6, 16.9, 15.2, 13.4, 11.7, 10.0, 8.2, 6.5, 5.2, 4.3, 3.4],
    [20.7, 18.9, 17.2, 15.5, 13.8, 12.0, 10.3, 8.6, 6.8, 5.1, 3.4, 2.5, 1.6],
    [19.3, 17.5, 15.8, 14.1, 12.4, 10.6, 8.9, 7.2, 5.4, 3.7, 2.0, 0.6, 0.0],
    [19.0, 16.4, 14.4, 12.7, 11.0, 9.2, 7.5, 5.8, 4.0, 2.3, 0.9, 0.1, 0.0],
  ];
  var EIS = 18, PER_GEMAAL = 0.05, PER_HA = 75;

  // De rand: gemaal in m3/s en vasthouden in ha waarbij de eis precies gehaald wordt.
  var RAND = [
    [0.0250, 696.8], [0.0500, 650.4], [0.0750, 604.0], [0.1000, 557.7], [0.1250, 511.1],
    [0.1500, 464.5], [0.1750, 418.9], [0.2000, 372.1], [0.2250, 326.0], [0.2500, 279.0],
    [0.2750, 232.6], [0.3000, 186.9], [0.3250, 140.3], [0.3392, 113.7], [0.3500, 106.1],
    [0.3750, 88.6], [0.4000, 70.9], [0.4250, 53.2], [0.4500, 35.4], [0.4750, 17.7],
    [0.5000, 0.0],
  ];
  var GOEDKOOPST = [0.3392, 113.7];
  // Route A neemt eerst 225 ha vasthouden; de rest vraagt 0,279 m3/s gemaal.
  // Route B neemt eerst 0,2 m3/s gemaal; de rest vraagt 372,1 ha vasthouden.
  var A_HA = 225, A_GEMAAL = 0.279, B_GEMAAL = 0.2, B_HA = 372.1;
  // Waar de eerste stap van elke route op het raster eindigt.
  var A_RIJ = 3, B_KOLOM = 4;

  // De projectie: u is de kolom (gemaal), v de rij (vasthouden), h de piek in cm.
  // De oorsprong ligt achteraan en het oppervlak loopt af naar de kijker, dus
  // geen cel staat voor een andere.
  var MIDX = 262, MIDY = 172, BREED = 21, DIEP = 7, HOOG = 4;

  function punt(u, v, h) {
    return [MIDX + (u - v) * BREED, MIDY + (u + v) * DIEP - h * HOOG];
  }

  function knoop(u, v) { return punt(u, v, PIEK[v][u]); }

  function lijn(punten) {
    return "M" + punten.map(function (p) { return p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(" L");
  }

  // Een been van een route loopt langs één as over de knopen, en eindigt op
  // `eind` als dat tussen twee knopen ligt.
  function been(knopen, eind) {
    return lijn(knopen.map(function (k) { return knoop(k[0], k[1]); }).concat(eind ? [eind] : []));
  }

  function reeks(n) {
    return Array.apply(null, Array(n)).map(function (_, i) { return i; });
  }

  function tekst(klasse, x, y, inhoud, anker) {
    return '<text class="f-tekst ' + klasse + '" x="' + x + '" y="' + y + '"' +
           (anker ? ' text-anchor="' + anker + '"' : '') + '>' + inhoud + '</text>';
  }

  function stip(klasse, p, straal) {
    return '<circle class="' + klasse + '" cx="' + p[0].toFixed(1) + '" cy="' + p[1].toFixed(1) +
           '" r="' + straal + '"/>';
  }

  function oplossingsruimte() {
    var rijen = PIEK.length, kolommen = PIEK[0].length;
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    // ── 0: het oppervlak ───────────────────────────────────────────────────
    // Cel voor cel, van achter naar voren, elk gevuld met de achtergrond: zo
    // leest het als een oppervlak en niet als een kluwen lijnen.
    var cellen = [];
    reeks(rijen - 1).forEach(function (v) {
      reeks(kolommen - 1).forEach(function (u) { cellen.push([u, v]); });
    });
    cellen.sort(function (a, b) { return a[0] + a[1] - b[0] - b[1]; });
    function cel(c, stijl) {
      var u = c[0], v = c[1];
      return '<path style="' + stijl + '" d="' +
             lijn([knoop(u, v), knoop(u + 1, v), knoop(u + 1, v + 1), knoop(u, v + 1)]) + ' Z"/>';
    }
    t += '<g class="f-deel aan" data-deel="0">' +
         cellen.map(function (c) {
           return cel(c, "fill:var(--grond);stroke:var(--licht);stroke-width:1");
         }).join("") +
         tekst("sterk", 250, 24, "no measures: the peak is 36 cm", "end") +
         stip("f-knoop", knoop(0, 0), 5) +
         tekst("klein", 12, 124, "more") + tekst("klein", 12, 140, "retention ↙") +
         tekst("klein", 524, 196, "more") + tekst("klein", 524, 212, "pumping ↘") +
         '</g>';

    // ── 1: brute force, elke knoop doorgerekend ────────────────────────────
    t += '<g class="f-deel" data-deel="1">';
    reeks(rijen).forEach(function (v) {
      reeks(kolommen).forEach(function (u) { t += stip("f-knoop", knoop(u, v), 3.2); });
    });
    t += tekst("sterk", 12, 266, "brute force:") +
         tekst("sterk accent", 12, 288, "every node, 143 runs") +
         tekst("klein", 12, 310, "and that is two measures") +
         '</g>';

    // ── 2: de eis, als lijn over het oppervlak ─────────────────────────────
    var rand = RAND.map(function (r) { return punt(r[0] / PER_GEMAAL, r[1] / PER_HA, EIS); });
    t += '<g class="f-deel" data-deel="2">' +
         cellen.filter(function (c) {
           return Math.max(PIEK[c[1]][c[0]], PIEK[c[1]][c[0] + 1],
                           PIEK[c[1] + 1][c[0]], PIEK[c[1] + 1][c[0] + 1]) <= EIS + 0.05;
         }).map(function (c) {
           return cel(c, "fill:var(--nat);fill-opacity:.2;stroke:none");
         }).join("") +
         '<path class="c-lijn accent" style="stroke-width:3.5" d="' + lijn(rand) + '"/>' +
         tekst("sterk accent", 484, 142, "the requirement:") +
         tekst("sterk accent", 484, 162, "peak below 18 cm") +
         '</g>';

    // ── 3: stap één, een maatregel nemen en kijken wat hij geeft ───────────
    var naA = knoop(0, A_RIJ);
    t += '<g class="f-deel" data-deel="3">' +
         '<path class="f-droog" style="stroke-width:4" d="' +
           been(reeks(A_RIJ + 1).map(function (v) { return [0, v]; })) + '"/>' +
         stip("c-optimum", naA, 6) +
         tekst("sterk droog", 392, 24, "1 · retain 225 ha") +
         tekst("klein", 392, 42, "what does it give? 36 → 27.8 cm") +
         '</g>';

    // ── 4: stap twee, wat er over is en welke maatregel dat nog kan ────────
    var opRandA = punt(A_GEMAAL / PER_GEMAAL, A_HA / PER_HA, EIS);
    t += '<g class="f-deel" data-deel="4">' +
         '<path class="f-droog" style="stroke-width:4" stroke-dasharray="9 5" d="' +
           been(reeks(Math.floor(A_GEMAAL / PER_GEMAAL) + 1).map(function (u) {
             return [u, A_RIJ];
           }), opRandA) + '"/>' +
         stip("c-optimum", opRandA, 6) +
         tekst("sterk droog", 392, 68, "2 · what is left? 9.8 cm") +
         tekst("klein", 392, 86, "pumping +0.28 m³/s closes it: € 1.08 mln") +
         '</g>';

    // ── 5: dezelfde stappen in een andere volgorde ─────────────────────────
    var naB = knoop(B_KOLOM, 0);
    var opRandB = punt(B_GEMAAL / PER_GEMAAL, B_HA / PER_HA, EIS);
    t += '<g class="f-deel" data-deel="5">' +
         '<path class="c-lijn derde" style="stroke-width:4" d="' +
           been(reeks(B_KOLOM + 1).map(function (u) { return [u, 0]; })) + '"/>' +
         '<path class="c-lijn derde" style="stroke-width:4" stroke-dasharray="9 5" d="' +
           been(reeks(Math.floor(B_HA / PER_HA) + 1).map(function (v) {
             return [B_KOLOM, v];
           }), opRandB) + '"/>' +
         stip("f-knoop", naB, 5) +
         '<circle cx="' + opRandB[0].toFixed(1) + '" cy="' + opRandB[1].toFixed(1) +
           '" r="6" style="fill:var(--derde);stroke:var(--grond);stroke-width:2"/>' +
         tekst("sterk derde", 436, 270, "another order:") +
         tekst("klein", 436, 288, "pump 0.2 m³/s first, then 372 ha") +
         tekst("klein", 436, 304, "same line, another package: € 1.28 mln") +
         '</g>';

    // ── 6: het goedkoopste punt op de lijn, en wie het daar overneemt ──────
    var goedkoopst = punt(GOEDKOOPST[0] / PER_GEMAAL, GOEDKOOPST[1] / PER_HA, EIS);
    t += '<g class="f-deel" data-deel="6">' +
         '<circle class="i-bindend" cx="' + goedkoopst[0].toFixed(1) + '" cy="' +
           goedkoopst[1].toFixed(1) + '" r="15"/>' +
         stip("c-optimum", goedkoopst, 6) +
         tekst("sterk nadruk", 12, 256, "cheapest on the line:") +
         tekst("klein", 12, 274, "114 ha + 0.34 m³/s, € 0.92 mln") +
         tekst("sterk", 12, 302, "from here: the detailed") +
         tekst("sterk", 12, 322, "models and the experts") +
         '</g>';

    return t + '</svg>';
  }

  T.oplossingsruimte = oplossingsruimte();
})(TEKEN);
