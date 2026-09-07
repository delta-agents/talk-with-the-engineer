// ═══════════════════════════════════════════════════════════════════════════
// Het raster: dit tegenover dat, op een handvol regels.
// ═══════════════════════════════════════════════════════════════════════════
//
// Drie figuren in de deck stellen dezelfde vraag in dezelfde vorm. Een eigen
// tekening per stuk zou drie keer hetzelfde raster met andere woorden zijn.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  // ── twee kolommen naast elkaar, rij voor rij ─────────────────────────────
  //
  // Drie figuren hieronder stellen dezelfde vraag: dit tegenover dat, op een
  // handvol regels. Een eigen tekening per stuk zou drie keer hetzelfde raster
  // met andere woorden zijn, dus staat het raster hier één keer.
  //
  // Elke rij is een eigen `f-deel`, dus een beat zet ze één voor één aan of
  // alle vier tegelijk. Deel 0 is de koprij en staat altijd aan: zonder de twee
  // namen erboven zegt een rij niets.
  function kolommen(links, rechts, rijen, voet) {
    // De maten volgen `table.rijen`: labelkolom links, waarden LINKS uitgelijnd
    // onder hun kop, en een haarlijn onder elke rij. Deze plaat stond eerder met
    // gecentreerde waarden en zonder rijlijnen, en was daarmee de enige tabel in
    // de deck die er anders uitzag - terwijl `A` met zijn vier kolommen precies
    // dezelfde vorm heeft en het huisidioom wel volgt.
    var LAB = 16, L = 210, R = 430, BREED = 214;
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet">';

    // De koprij staat BUITEN elk deel, zoals de s-doos in `transitie`: zonder de
    // twee namen erboven zegt geen enkele rij iets, dus mag hij nooit wegvallen.
    t += '<g>' +
         '<text class="f-tekst sterk accent" x="' + L + '" y="40">' + links[0] + '</text>' +
         '<text class="f-tekst klein" x="' + L + '" y="60">' + links[1] + '</text>' +
         '<text class="f-tekst sterk derde" x="' + R + '" y="40">' + rechts[0] + '</text>' +
         '<text class="f-tekst klein" x="' + R + '" y="60">' + rechts[1] + '</text>' +
         '<path class="f-lijn" d="M' + LAB + ' 76 L644 76"/>' +
         '</g>';

    rijen.forEach(function (rij, i) {
      var y = 118 + i * 50;
      t += '<g class="f-deel" data-deel="' + i + '">' +
           '<text class="f-tekst klein" x="' + LAB + '" y="' + y + '">' + rij[0] + '</text>' +
           '<text class="f-tekst sterk" x="' + L + '" y="' + y + '">' + rij[1] + '</text>' +
           '<text class="f-tekst sterk" x="' + R + '" y="' + y + '">' + rij[2] + '</text>' +
           '<path class="f-lijn" d="M' + LAB + ' ' + (y + 16) + ' L644 ' + (y + 16) + '"/>' +
           '</g>';
    });

    // De voet mag meer dan een regel dragen: een conclusie van tachtig tekens is
    // op beamerafstand een regel te lang. Hij staat LINKS uitgelijnd met de rest
    // en niet gecentreerd, om dezelfde reden als de waarden.
    if (voet) {
      var yv = 118 + rijen.length * 50 + 34;
      t += '<g class="f-deel" data-deel="' + rijen.length + '">';
      [].concat(voet).forEach(function (regel, i) {
        t += '<text class="f-tekst sterk nadruk" x="' + LAB + '" y="' + (yv + i * 24) +
             '">' + regel + '</text>';
      });
      t += '</g>';
    }
    return t + "</svg>";
  }

  function lijsten(links, rechts) {
    function kolom(kop, regels, x, tint, deel) {
      var u = '<g class="f-deel" data-deel="' + deel + '">' +
              '<text class="f-tekst sterk ' + tint + '" x="' + x + '" y="34">' +
                kop + '</text>' +
              '<path class="f-lijn" d="M' + x + ' 50 L' + (x + 288) + ' 50"/>';
      regels.forEach(function (regel, i) {
        u += '<text class="f-tekst" x="' + x + '" y="' + (86 + i * 38) + '">' +
             regel + '</text>';
      });
      return u + '</g>';
    }
    return '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
           kolom(links[0], links.slice(1), 16, "accent", 0) +
           kolom(rechts[0], rechts.slice(1), 348, "derde", 1) + '</svg>';
  }

  // ── wat dit bestand levert ────────────────────────────────────────────────
  T.kolommen = kolommen;
  T.lijsten = lijsten;
})(TEKEN);
