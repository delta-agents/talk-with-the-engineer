// ═══════════════════════════════════════════════════════════════════════════
// De curven: wat een maatregel oplevert, wat een eis kost, en het weer als vorm.
// ═══════════════════════════════════════════════════════════════════════════
//
// Elk padje in dit bestand is GEGENEREERD uit de rekenkern — zie het commentaar
// boven de figuur voor het script dat het levert, en de README voor hoe je het
// opnieuw draait. Met de hand bijwerken is precies de manier waarop de deck iets
// gaat beweren dat de kern niet meer zegt.
//
// De frequentielijn draagt de polder op de onderste verdieping en leent daarom
// de projectie en de bergingsvijver van `polder.js`.

window.TEKEN = window.TEKEN || {};

(function (T) {
  "use strict";

  var iso = T.iso,
      isoVlak = T.isoVlak,
      isoPlaat = T.isoPlaat,
      isoEllips = T.isoEllips,
      isoPijl = T.isoPijl,
      BERG_X = T.BERG_X,
      BERG_Y = T.BERG_Y,
      BERG_R = T.BERG_R;

  // ── wat een eis kost ─────────────────────────────────────────────────────
  //
  // De vorm die de literatuur gebruikt: Van Dantzig (1956) en Eijgenraam zetten
  // de INVESTERING tegen het beschermingsniveau en tellen daar de resterende
  // verwachte schade bij op; het optimum ligt waar die som het laagst is. Wij
  // kunnen alleen de eerste helft tekenen - en deel 2 is precies de helft die
  // ontbreekt. Dat is wat deze figuur moet laten zien.
  //
  // Padje GEGENEREERD met scripts/gen_kostencurve.py.
  //
  // Delen: 0 = de kostencurve, 1 = de vier prijzen, 2 = de curve die mist,
  // 3 = de band waarin meerdere hele pakketten allemaal verdedigbaar zijn.
  var kostencurve = (function () {
    var X0 = 96, X1 = 520, Y0 = 44, Y1 = 250;
    var t = '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    t += '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X1 + ' ' + Y1 + '"/>' +
         '<path class="f-lijn" d="M' + X0 + ' ' + Y0 + ' L' + X0 + ' ' + Y1 + '"/>' +
         '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y0 - 12) +
           '">cost of the cheapest package [million euros]</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y1 + 4) +
           '" text-anchor="end">0</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y0 + 6) +
           '" text-anchor="end">2</text>' +
         '<text class="f-tekst klein" x="96" y="268" text-anchor="middle">36</text>' +
         '<text class="f-tekst klein" x="194" y="268" text-anchor="middle">30</text>' +
         '<text class="f-tekst klein" x="357" y="268" text-anchor="middle">20</text>' +
         '<text class="f-tekst klein" x="520" y="268" text-anchor="middle">10</text>' +
         '<text class="f-tekst klein" x="308" y="312" text-anchor="middle">the requirement: how far the peak may still rise [cm]</text>' +
         '<text class="f-tekst klein" x="308" y="330" text-anchor="middle">on the left the thirty-six centimetres of the bare curve</text>';

    t += '<g class="f-deel aan" data-deel="0">' +
         '<path class="c-lijn nat" d="M96.0 250.0 L128.6 242.4 L161.2 234.8 L193.8 227.2 L226.5 219.5 L259.1 211.9 L291.7 204.3 L324.3 193.7 L356.9 174.0 L389.5 154.8 L422.2 128.2 L454.8 105.3 L487.4 82.5 L520.0 59.6"/>' +
         '</g>';

    // De vier prijzen. Ze staan als EIGEN RIJ onder de eis-as: in het vlak
    // zelf botsen ze op de curve die er straks bij komt, en onder elkaar laten
    // ze zien dat de sprongen groter worden - nul, twee ton, zeven, achttien.
    var EISEN = [[96, 250, "\u20ac 0"], [193.8, 227.2, "\u20ac 0.22"],
                 [356.9, 174.0, "\u20ac 0.74"], [520, 59.6, "\u20ac 1.85"]];
    t += '<g class="f-deel" data-deel="1">';
    for (var i = 0; i < EISEN.length; i++) {
      t += '<circle class="c-optimum" cx="' + EISEN[i][0] + '" cy="' + EISEN[i][1] + '" r="6"/>' +
           '<text class="f-tekst sterk nat" x="' + EISEN[i][0] +
             '" y="292" text-anchor="middle">' + EISEN[i][2] + '</text>';
    }
    t += '</g>';

    t += '<g class="f-deel" data-deel="2">' +
         '<path class="c-lijn slecht" d="M96 80 C 220 128, 360 200, 520 238"/>' +
         '<text class="f-tekst sterk nadruk" x="532" y="86">here belongs the</text>' +
         '<text class="f-tekst sterk nadruk" x="532" y="104">damage curve,</text>' +
         '<text class="f-tekst klein nadruk" x="532" y="128">still to be filled in</text>' +
         '</g>';

    // deel 3: en die som heeft geen punt maar een BODEM. Dat is de reden dat we
    // alternatieven genereren in plaats van te optimaliseren: binnen die band
    // zijn meerdere hele pakketten allemaal verdedigbaar. De band is, net als de
    // schadecurve, de VORM uit de literatuur en niet een getal van ons.
    t += '<g class="f-deel" data-deel="3">' +
         '<rect class="c-band" x="270" y="44" width="150" height="206"/>' +
         '<text class="f-tekst sterk nadruk" x="345" y="66" text-anchor="middle">not one point</text>' +
         '<text class="f-tekst sterk nadruk" x="345" y="86" text-anchor="middle">but a band</text>' +
         '</g>';

    return t + '</svg>';
  })();


  // ── de frequentielijn, met de polder eronder ─────────────────────────────
  //
  // Twee verdiepingen: boven de overschrijdingsfrequentielijn, onder de polder
  // in 2,5D. Dan is te zien WAARMEE gerekend wordt en niet alleen wat eruit
  // komt. Peilopzet is eruit: die gaat omhoog en leidt af van de vraag die deze
  // figuur stelt, namelijk wat een maatregel je aan bescherming oplevert.
  //
  // Padjes GEGENEREERD met scripts/gen_frequentielijn.py.
  //
  // Delen: 0 = de polder, 1 = de losse runs, 2 = de kale lijn,
  // 3 = bergen, 4 = vasthouden, 5 = afvoeren.
  var frequentielijn = (function () {
    var X0 = 96, X1 = 520, Y0 = 40, Y1 = 182;
    var NORM_Y = 128.8;
    var MX = 430, MY = 212, S = 82, DIK = 13;

    var t = '<svg viewBox="0 0 700 340" preserveAspectRatio="xMidYMid meet" class="f-hard">';

    // de assen, de norm en de onderschriften: die staan altijd
    t += '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X1 + ' ' + Y1 + '"/>' +
         '<path class="f-lijn" d="M' + X0 + ' ' + Y0 + ' L' + X0 + ' ' + Y1 + '"/>' +
         '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y0 - 12) +
           '">the peak above target level [cm]</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y1 + 4) +
           '" text-anchor="end">0</text>' +
         '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y0 + 6) +
           '" text-anchor="end">80</text>' +
         '<text class="f-tekst klein" x="96" y="198" text-anchor="middle">1</text>' +
         '<text class="f-tekst klein" x="308" y="198" text-anchor="middle">10</text>' +
         '<text class="f-tekst klein" x="520" y="198" text-anchor="middle">100</text>' +
         '<text class="f-tekst klein" x="308" y="220" text-anchor="middle">return period [years]</text>' +
         '<path class="f-norm" d="M' + X0 + ' ' + NORM_Y + ' L' + X1 + ' ' + NORM_Y + '"/>' +
         '<text class="f-tekst norm" x="' + (X0 + 6) + '" y="' + (NORM_Y - 8) +
           '">the standard: 30 cm</text>';

    // deel 0: de polder zelf, onder de grafiek - waarmee gerekend wordt
    t += '<g class="f-deel aan" data-deel="0">' +
         isoPlaat(MX, MY, S, DIK) +
         '<path class="i-water" d="' + isoVlak(0, 0.45, 1, 0.55, MX, MY, S) + '"/>' +
         '<text class="f-tekst klein" x="96" y="258">1000 ha, 5 % open water,</text>' +
         '<text class="f-tekst klein" x="96" y="276">pumping station 1.5 m\u00b3/s</text>' +
         '</g>';

    // deel 1: acht losse doorrekeningen, voordat ze een lijn zijn
    t += '<g class="f-deel" data-deel="1">' +
         '<circle class="c-run" cx="96" cy="165" r="4"/>' +
         '<circle class="c-run" cx="160" cy="155" r="4"/>' +
         '<circle class="c-run" cx="244" cy="138" r="4"/>' +
         '<circle class="c-run" cx="308" cy="118" r="4"/>' +
         '<circle class="c-run" cx="372" cy="98" r="4"/>' +
         '<circle class="c-run" cx="392" cy="91" r="4"/>' +
         '<circle class="c-run" cx="456" cy="73" r="4"/>' +
         '<circle class="c-run" cx="520" cy="51" r="4"/>' +
         '<text class="f-tekst klein" x="532" y="164">run</text>' +
         '<text class="f-tekst klein" x="532" y="180">eight times</text>' +
         '</g>';

    // deel 2: dezelfde acht punten, nu als lijn
    t += '<g class="f-deel" data-deel="2">' +
         '<path class="c-lijn" d="M96.0 164.7 L159.8 155.4 L244.2 138.1 L308.0 118.1 L371.8 98.2 L392.4 90.7 L456.2 73.3 L520.0 50.6"/>' +
         '<text class="f-tekst sterk" x="532" y="53">no measure</text>' +
         '<text class="f-tekst sterk" x="694" y="53" text-anchor="end">T=7</text>' +
         '</g>';

    // deel 3-5: de drie lijnen. Ze BLIJVEN staan, want de vergelijking is het
    // punt van de figuur - elke lijn is de maatregel ALLEEN, niet gestapeld.
    t += '<g class="f-deel" data-deel="3">' +
         '<path class="c-lijn accent" d="M96.0 167.7 L159.8 160.0 L244.2 145.4 L308.0 128.8 L371.8 112.2 L392.4 105.9 L456.2 91.4 L520.0 72.5"/>' +
         '<text class="f-tekst sterk accent" x="532" y="75">store</text>' +
         '<text class="f-tekst sterk accent" x="694" y="75" text-anchor="end">T=10</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="4">' +
         '<path class="c-lijn droog" d="M96.0 182.0 L159.8 176.7 L244.2 161.2 L308.0 148.4 L371.8 131.4 L392.4 125.1 L456.2 110.2 L520.0 90.9"/>' +
         '<text class="f-tekst sterk droog" x="532" y="93">retain</text>' +
         '<text class="f-tekst sterk droog" x="694" y="93" text-anchor="end">T=22</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="5">' +
         '<path class="c-lijn derde" d="M96.0 180.0 L159.8 170.8 L244.2 159.3 L308.0 150.1 L371.8 140.8 L392.4 136.0 L456.2 119.3 L520.0 96.6"/>' +
         '<text class="f-tekst sterk derde" x="532" y="113">discharge</text>' +
         '<text class="f-tekst sterk derde" x="694" y="113" text-anchor="end">T=34</text>' +
         '</g>';

    // deel 6-8: dezelfde maatregel op de plaat, MET zijn maat. Precies EEN van
    // deze drie staat aan terwijl de lijnen zich opstapelen: de lijn is het
    // resultaat om te vergelijken, de plaat is de ingreep die erbij hoort.
    var vijver = iso(BERG_X, BERG_Y, MX, MY, S);
    t += '<g class="f-deel" data-deel="6">' +
         isoEllips(BERG_X, BERG_Y, BERG_R, MX, MY, S, "i-vijver") +
         isoEllips(BERG_X, BERG_Y, BERG_R * 0.72, MX, MY, S, "i-vijverwater") +
         '<text class="f-tekst sterk accent" x="' + (vijver[0] + 30).toFixed(0) + '" y="' +
           (vijver[1] - 16).toFixed(0) + '">store</text>' +
         '<text class="f-tekst sterk accent" x="96" y="302">ten hectares more: 5 \u2192 6 % open water</text>' +
         '</g>';

    t += '<g class="f-deel" data-deel="7">' +
         '<path class="i-retentie" d="' + isoVlak(0.06, 0.62, 0.52, 0.95, MX, MY, S) + '"/>' +
         '<text class="f-tekst sterk droog" x="349" y="276" text-anchor="end">retain</text>' +
         '<text class="f-tekst sterk droog" x="96" y="302">708 hectares of land: 74 % retains its water</text>' +
         '</g>';

    var gemaal = iso(1, 0.5, MX, MY, S), uit = iso(1.62, 0.5, MX, MY, S);
    t += '<g class="f-deel" data-deel="8">' +
         isoPijl(gemaal, uit, "i-pijl dik") +
         '<circle class="i-gemaal" cx="' + gemaal[0].toFixed(1) + '" cy="' +
           gemaal[1].toFixed(1) + '" r="9"/>' +
         '<text class="f-tekst sterk derde" x="' + (uit[0] + 10).toFixed(0) + '" y="' +
           (uit[1] - 4).toFixed(0) + '">discharge</text>' +
         '<text class="f-tekst sterk derde" x="96" y="302">half a cubic metre more: pump 1.5 \u2192 2.0 m\u00b3/s</text>' +
         '</g>';

    return t + '</svg>';
  })();


  // ── de twee statistieken, als vorm ───────────────────────────────────────
  //
  // Het verschil tussen de twee IS de stap. De natte statistiek varieert de
  // GEBEURTENIS - dezelfde zomer, drie buiduren. De droge varieert het KLIMAAT
  // - hetzelfde groeiseizoen, zeven toekomsten. Padjes gegenereerd met
  // scripts/gen_statistiek.py.
  // Assen met een instelbaar kader, zodat twee plots in één figuur gestapeld
  // kunnen staan. `onder` is het label onderaan de y-as, want niet elke as
  // begint bij nul.
  function statistiekAssen(kader, labels, eenheid, top, onder) {
    var X0 = 96, X1 = 520;
    var Y0 = kader[0], Y1 = kader[1];
    var t = '<path class="f-lijn" d="M' + X0 + ' ' + Y1 + ' L' + X1 + ' ' + Y1 + '"/>' +
            '<path class="f-lijn" d="M' + X0 + ' ' + Y0 + ' L' + X0 + ' ' + Y1 + '"/>' +
            '<text class="f-tekst klein" x="' + X0 + '" y="' + (Y0 - 10) + '">' + eenheid + '</text>' +
            '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y1 + 4) +
              '" text-anchor="end">' + (onder || "0") + '</text>' +
            '<text class="f-tekst klein" x="' + (X0 - 8) + '" y="' + (Y0 + 6) +
              '" text-anchor="end">' + top + '</text>';
    labels.forEach(function (l) {
      t += '<text class="f-tekst klein" x="' + l[0] + '" y="' + (Y1 + 18) +
           '" text-anchor="middle">' + l[1] + '</text>';
    });
    return t;
  }

  var neerslagstatistiek =
    '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
    statistiekAssen([44, 215], [[96, "\u00bd"], [263, "10"], [520, "1000"]],
                    "rainfall [mm]", "150") +
    '<text class="f-tekst klein" x="308" y="251" text-anchor="middle">return period [years]</text>' +
    '<g class="f-deel aan" data-deel="0">' +
    '  <path class="c-lijn reeks3" d="M96.0 161.4 L134.7 152.3 L173.3 143.2 L224.4 131.8 L263.1 122.7 L301.8 113.5 L314.2 110.1 L352.9 102.1 L391.6 91.8 L430.2 81.4 L442.7 78.0 L481.3 67.6 L520.0 57.2"/>' +
    '  <text class="f-tekst sterk reeks3" x="532" y="60">8 days</text>' +
    '  <path class="c-lijn reeks2" d="M96.0 181.9 L134.7 175.1 L173.3 167.1 L224.4 156.9 L263.1 147.7 L301.8 139.8 L314.2 136.3 L352.9 127.2 L391.6 116.3 L430.2 105.0 L442.7 101.3 L481.3 89.5 L520.0 77.2"/>' +
    '  <text class="f-tekst sterk reeks2" x="532" y="80">4 days</text>' +
    '  <path class="c-lijn reeks1" d="M96.0 196.8 L134.7 189.9 L173.3 183.1 L224.4 174.0 L263.1 166.0 L301.8 158.0 L314.2 154.6 L352.9 145.5 L391.6 134.4 L430.2 122.5 L442.7 118.6 L481.3 105.6 L520.0 91.7"/>' +
    '  <text class="f-tekst sterk reeks1" x="532" y="96">2 days</text>' +
    '</g>' +
    '<g class="f-deel" data-deel="1">' +
    '  <text class="f-tekst klein" x="532" y="126">and per season</text>' +
    '  <text class="f-tekst klein" x="532" y="142">and per regime:</text>' +
    '  <text class="f-tekst sterk droog" x="532" y="164">summer 59 mm</text>' +
    '  <text class="f-tekst sterk droog" x="532" y="182">winter 73 mm</text>' +
    '  <text class="f-tekst klein" x="532" y="200">the same storm,</text>' +
    '  <text class="f-tekst klein" x="532" y="216">once in 10 years</text>' +
    '</g>' +
    // De trekking staat ONDER de grafiek en niet erin: het is een andere
    // grootheid - millimeter per dag - en hij hoort niet in het T-vlak.
    '<g class="f-deel" data-deel="2">' +
    '  <path class="f-lijn" d="M96 322 L200 322"/>' +
    '  <rect class="i-band" x="96" y="316" width="20" height="6"/>' +
    '  <rect class="i-band" x="120" y="289" width="20" height="33"/>' +
    '  <rect class="i-band" x="144" y="261" width="20" height="61"/>' +
    '  <rect class="i-band" x="168" y="312" width="20" height="10"/>' +
    '  <text class="f-tekst klein" x="96" y="336">day 1 to 4</text>' +
    '  <text class="f-tekst sterk" x="216" y="284">one draw</text>' +
    '  <text class="f-tekst klein" x="216" y="302">enters the balance as</text>' +
    '  <text class="f-tekst klein" x="216" y="318">millimetres per day</text>' +
    '</g>' +
    '</svg>';

  // Vraag EN aanbod in één figuur, gestapeld. Twee grootheden met twee
  // eenheden horen niet op één as, maar wel onder elkaar: dezelfde
  // herhaaltijd-as, twee verdiepingen.
  var droogtestatistiek =
    '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet" class="f-hard">' +
    statistiekAssen([40, 158], [], "demand: rainfall deficit [mm]", "600") +
    '<g class="f-deel aan" data-deel="0">' +
    '  <path class="i-band" d="M96.0 129.5 L195.3 118.4 L270.4 111.4 L369.7 103.0 L444.9 97.0 L520.0 91.4 L520.0 79.6 L444.9 85.4 L369.7 91.6 L270.4 100.8 L195.3 108.0 L96.0 120.4 Z"/>' +
    '  <path class="c-lijn" d="M96.0 122.5 L195.3 110.4 L270.4 103.2 L369.7 95.0 L444.9 89.6 L520.0 84.7"/>' +
    '  <text class="f-tekst sterk" x="532" y="112">nu</text>' +
    '  <text class="f-tekst klein" x="532" y="128">21 water boards</text>' +
    '  <path class="c-lijn slecht" d="M96.0 90.5 L195.3 73.1 L270.4 65.0 L369.7 57.5 L444.9 53.2 L520.0 50.0"/>' +
    '  <text class="f-tekst sterk nadruk" x="532" y="58">2100, dry</text>' +
    '  <text class="f-tekst klein nadruk" x="532" y="74">seven futures</text>' +
    '</g>' +
    statistiekAssen([186, 296], [[96, "2"], [270, "10"], [520, "100"]],
                    "supply: river discharge [share of normal]", "1,0", "0,5") +
    '<text class="f-tekst klein" x="308" y="332" text-anchor="middle">return period [years]</text>' +
    '<g class="f-deel" data-deel="1">' +
    '  <path class="c-lijn nat" d="M96.0 186.2 L195.3 198.8 L270.4 208.0 L369.7 219.4 L444.9 227.6 L520.0 235.5"/>' +
    '  <text class="f-tekst sterk nat" x="532" y="216">Rhine</text>' +
    '  <text class="f-tekst klein nat" x="532" y="232">1077 m\u00b3/s normal</text>' +
    '  <path class="c-lijn nat" stroke-dasharray="6 4" d="M96.0 194.6 L195.3 212.2 L270.4 224.5 L369.7 239.5 L444.9 250.0 L520.0 259.9"/>' +
    '  <text class="f-tekst sterk nat" x="532" y="262">Meuse</text>' +
    '  <text class="f-tekst klein nat" x="532" y="278">50 m\u00b3/s normal</text>' +
    '</g>' +
    '</svg>';

  // ── wat dit bestand levert ────────────────────────────────────────────────
  // `statistiekAssen` blijft binnen: het kader is er voor de twee statistieken
  // hierboven en niet voor een plaat die er nog niet is.
  T.kostencurve = kostencurve;
  T.frequentielijn = frequentielijn;
  T.neerslagstatistiek = neerslagstatistiek;
  T.droogtestatistiek = droogtestatistiek;
})(TEKEN);
