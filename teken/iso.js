// ═══════════════════════════════════════════════════════════════════════════
// De projectie. Elk vlak, elke wand en elke pijl op een plaat komt hieruit.
// ═══════════════════════════════════════════════════════════════════════════
//
// Dit bestand kent de presentatie niet en de polder niet. Het levert de
// primitieven waarmee de platen in `polder.js` en `curven.js` getekend worden,
// en dat is de reden dat het als eerste geladen wordt.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

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

  // ── wat dit bestand levert ────────────────────────────────────────────────
  T.COS30 = COS30;
  T.SIN30 = SIN30;
  T.iso = iso;
  T.pad = pad;
  T.isoVlak = isoVlak;
  T.isoWanden = isoWanden;
  T.isoPlaat = isoPlaat;
  T.isoEllips = isoEllips;
  T.isoPijl = isoPijl;
})(TEKEN);
