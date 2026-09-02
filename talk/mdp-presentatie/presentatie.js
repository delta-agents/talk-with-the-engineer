// ═══════════════════════════════════════════════════════════════════════════
// De machinerie. Hier zit geen inhoud in — die staat in inhoud.js.
// ═══════════════════════════════════════════════════════════════════════════
//
// Geen framework, geen import, geen netwerk. Een klassiek script, dus dit werkt
// ook als je het bestand dubbelklikt en ook als de zaal geen wifi heeft. Dat is
// geen zuinigheid maar de eis: een presentatie die op een netwerkfout kan
// stukvallen, is geen presentatie.
//
// De hele toestand is één getal: welke beat staat er. Alles op het scherm is
// een functie van dat getal, dus terug kunnen is gratis en er bestaat geen
// stand die je alleen met de muis kunt bereiken.

(function () {
  "use strict";

  // ─────────────────────────────────────────────────────────────────────────
  // De beats uitrollen: één platte lijst, zodat vooruit en achteruit hetzelfde
  // zijn en de voortgang een deling is.
  // ─────────────────────────────────────────────────────────────────────────
  var BEATS = [{ stap: null, beat: INHOUD.titel, index: 0, van: 1 }];

  INHOUD.stappen.forEach(function (stap) {
    stap.beats.forEach(function (beat, i) {
      BEATS.push({ stap: stap, beat: beat, index: i, van: stap.beats.length });
    });
  });

  var nu = 0;

  // ─────────────────────────────────────────────────────────────────────────
  // Figuren. Een figuur krijgt de beat-nadruk als lijst van deelnummers; welk
  // deel bij welk nummer hoort staat in de `data-deel` van de tekening.
  // ─────────────────────────────────────────────────────────────────────────

  // Het schema van een world model: ÉÉN tekening, twee vullingen.
  //
  // Dat is geen zuinigheid maar de claim van de talk. Het schema blijft staan
  // en alleen wat erin staat wisselt van de microduck naar de polder; twee
  // losse SVG's zouden uit elkaar kunnen lopen en dan is die claim niet meer
  // waar te maken op het scherm.
  //
  // De symbolen op de pijlen zijn dezelfde als de leden van de tuple erna:
  // wie dit schema begrijpt, kent `a`, `e` en `s′` al voordat ze een eigen stap
  // krijgen.
  //
  // Delen: 0 = de transitie, 1 = de policy die de actie kiest, 2 = het exogene,
  // 3 = de beloning en de lus die de policy bijwerkt.
  function wereldmodel(v) {
    return '<svg viewBox="0 0 660 340" preserveAspectRatio="xMidYMid meet">' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <text class="f-tekst klein" x="210" y="88">de transitie van ' + v.wie + '</text>' +
      '    <rect class="f-vlak" x="210" y="96" width="250" height="78" rx="7"/>' +
      '    <text class="f-tekst sterk" x="335" y="122" text-anchor="middle">' + v.transitie + '</text>' +
      '    <text class="f-tekst klein" x="335" y="142" text-anchor="middle">opgeschreven, niet geleerd</text>' +
      '    <text class="f-tekst klein" x="335" y="160" text-anchor="middle">' + v.hoe + '</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-accent" d="M460 135 L516 135 L516 266 L470 266"/>' +
      '    <path class="f-accent" d="M478 260 L468 266 L478 272"/>' +
      '    <rect class="f-vlak" x="210" y="240" width="250" height="52" rx="7"/>' +
      '    <text class="f-tekst sterk" x="335" y="262" text-anchor="middle">de policy</text>' +
      '    <text class="f-tekst klein" x="335" y="280" text-anchor="middle">' + v.policy + '</text>' +
      '    <path class="f-accent" d="M210 266 L160 266 L160 135 L204 135"/>' +
      '    <path class="f-accent" d="M196 129 L206 135 L196 141"/>' +
      '    <text class="f-tekst wis" x="150" y="192" text-anchor="end">a</text>' +
      '    <text class="f-tekst klein" x="150" y="212" text-anchor="end">' + v.actie1 + '</text>' +
      '    <text class="f-tekst klein" x="150" y="228" text-anchor="end">' + v.actie2 + '</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-lijn" stroke-dasharray="5 5" d="M420 44 L420 88"/>' +
      '    <path class="f-lijn" d="M414 80 L420 90 L426 80"/>' +
      '    <text class="f-tekst wis" x="405" y="58" text-anchor="end">e</text>' +
      '    <text class="f-tekst klein" x="436" y="52">' + v.exogeen1 + '</text>' +
      '    <text class="f-tekst klein" x="436" y="68">' + v.exogeen2 + '</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="3">' +
      '    <text class="f-tekst wis" x="526" y="141">s\u2032</text>' +
      '    <text class="f-tekst klein" x="526" y="163">en de beloning:</text>' +
      '    <text class="f-tekst klein" x="526" y="179">' + v.beloning1 + '</text>' +
      '    <text class="f-tekst klein" x="526" y="195">' + v.beloning2 + '</text>' +
      '    <path class="f-droog" stroke-dasharray="4 4" d="M335 292 L335 308"/>' +
      '    <path class="f-droog" d="M329 300 L335 310 L341 300"/>' +
      '    <text class="f-tekst sterk" x="335" y="328" text-anchor="middle">' + v.ppo + '</text>' +
      '  </g>' +
      '</svg>';
  }

  var FIGUREN = {

    wereldmodel_robot: wereldmodel({
      wie: "de microduck",
      transitie: "starre lichamen en contact",
      hoe: "MuJoCo, 4096 werelden parallel",
      policy: "61 getallen in, 14 uit",
      actie1: "14 gewrichtsdoelen,",
      actie2: "50\u00d7 per seconde",
      exogeen1: "de vloer, de wrijving,",
      exogeen2: "de batterijspanning",
      beloning1: "vooruit,",
      beloning2: "en niet vallen",
      ppo: "PPO: twee uur op \u00e9\u00e9n GPU, en hij loopt",
    }),

    wereldmodel_polder: wereldmodel({
      wie: "de polder",
      transitie: "een massabalans",
      hoe: "uurstappen, 0,06 ms per keer",
      policy: "bestaat nog niet",
      actie1: "welke maatregel,",
      actie2: "en in welk jaar",
      exogeen1: "de bui, de droogte,",
      exogeen2: "het klimaatscenario",
      beloning1: "kosten tegen",
      beloning2: "vermeden schade",
      ppo: "PPO: dezelfde stap, nog niet gezet",
    }),

    // deel 0 = de gesloten lus, 1 = de doorrekening, 2 = wat exogeen is.
    // De s-doos staat BUITEN elk deel: hij is het onderwerp van alle drie de
    // beats, dus hij mag nooit wegvallen.
    transitie:
      '<svg viewBox="0 0 620 290" preserveAspectRatio="xMidYMid meet">' +
      '  <rect class="f-vlak" x="150" y="96" width="136" height="58" rx="7"/>' +
      '  <text class="f-tekst wis" x="218" y="122" text-anchor="middle">s</text>' +
      '  <text class="f-tekst klein" x="218" y="141" text-anchor="middle">de polder</text>' +
      /* Omlaag is apply, naar rechts is simulate, en de lus komt links als een
         boog terug. Eerder liep de retourpijl langs de vier randen van het vlak
         en las hij als een kader om de hele tekening in plaats van als een pijl. */
      '  <g class="f-deel aan" data-deel="0">' +
      '    <path class="f-accent" d="M218 154 L218 202"/>' +
      '    <path class="f-accent" d="M212 194 L218 204 L224 194"/>' +
      '    <text class="f-tekst klein" x="232" y="184">een maatregel</text>' +
      '    <rect class="f-vlak" x="150" y="204" width="136" height="58" rx="7"/>' +
      '    <text class="f-tekst wis" x="218" y="230" text-anchor="middle">s′</text>' +
      '    <text class="f-tekst klein" x="218" y="249" text-anchor="middle">zelfde type</text>' +
      '    <path class="f-accent" stroke-dasharray="6 5"' +
      '          d="M150 233 C 92 233, 92 125, 144 125"/>' +
      '    <path class="f-accent" d="M136 119 L146 125 L136 131"/>' +
      '    <text class="f-tekst sterk" x="80" y="174" text-anchor="end">terug te</text>' +
      '    <text class="f-tekst sterk" x="80" y="192" text-anchor="end">voeren</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-nat" d="M286 125 L352 125"/>' +
      '    <path class="f-nat" d="M344 119 L354 125 L344 131"/>' +
      '    <rect class="f-vlak" x="354" y="96" width="140" height="58" rx="7"/>' +
      '    <text class="f-tekst sterk" x="424" y="122" text-anchor="middle">de waterbalans</text>' +
      '    <text class="f-tekst klein" x="424" y="141" text-anchor="middle">0,06 ms</text>' +
      '    <path class="f-nat" d="M424 154 L424 176"/>' +
      '    <path class="f-nat" d="M418 168 L424 178 L430 168"/>' +
      '    <text class="f-tekst wis" x="424" y="200" text-anchor="middle">Δh</text>' +
      '    <text class="f-tekst klein" x="424" y="220" text-anchor="middle">een piekstand,</text>' +
      '    <text class="f-tekst klein" x="424" y="236" text-anchor="middle">geen toestand</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-lijn" stroke-dasharray="5 5" d="M218 42 L218 90"/>' +
      '    <path class="f-lijn" d="M212 82 L218 92 L224 82"/>' +
      '    <text class="f-tekst sterk" x="238" y="52">het weer — getrokken, niet gekozen</text>' +
      '    <text class="f-tekst klein" x="238" y="70">bui: uren · droogte: een groeiseizoen</text>' +
      '  </g>' +
      '</svg>',

    // deel 0 = het risico zonder maatregelen, 1 = de zaagtand, 2 = de korting.
    // De as en de norm staan buiten de delen: de norm is de eis waar het hele
    // plaatje over gaat, en die hoort er vanaf de eerste beat te staan.
    zaagtand:
      '<svg viewBox="0 0 620 320" preserveAspectRatio="xMidYMid meet">' +
      '  <path class="f-lijn" d="M62 250 L596 250"/>' +
      '  <path class="f-lijn" d="M62 28 L62 250"/>' +
      '  <text class="f-tekst klein" x="62" y="266">2026</text>' +
      '  <text class="f-tekst klein" x="596" y="266" text-anchor="end">2100</text>' +
      '  <text class="f-tekst klein" x="62" y="20">risico</text>' +
      '  <path class="f-lijn" stroke-dasharray="7 5" d="M62 152 L596 152"/>' +
      '  <text class="f-tekst sterk" x="596" y="145" text-anchor="end">de norm</text>' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <path class="f-lijn" stroke-dasharray="4 4" d="M62 206 L596 62"/>' +
      '    <text class="f-tekst klein" x="470" y="86">zonder maatregelen:</text>' +
      '    <text class="f-tekst klein" x="470" y="102">klimaat en bodemdaling</text>' +
      '  </g>' +
      /* De maatregelnamen staan BOVEN hun sprong. Onder de sprong liepen ze door
         de discontokromme heen, en dan las "peilopzet" als een label bij γ. */
      '  <g class="f-deel" data-deel="1">' +
      '    <path class="f-accent" d="M62 206 L188 168 L188 212 L316 174 L316 220' +
      '      L444 178 L444 224 L572 182 L596 174"/>' +
      '    <g class="f-tekst klein">' +
      '      <text x="188" y="160" text-anchor="middle">bergen</text>' +
      '      <text x="316" y="166" text-anchor="middle">afvoeren</text>' +
      '      <text x="444" y="170" text-anchor="middle">peilopzet</text>' +
      '    </g>' +
      '  </g>' +
      /* De korting krijgt zijn eigen band ONDER de tijdas. In het vlak zelf
         kruiste hij de zaagtand en suggereerde hij hetzelfde soort grootheid. */
      '  <g class="f-deel" data-deel="2">' +
      '    <text class="f-tekst klein" x="62" y="288">wat een euro in dat jaar nog weegt</text>' +
      '    <path class="f-droog" stroke-dasharray="3 4" d="M62 300 C 230 306, 400 312, 596 314"/>' +
      '  </g>' +
      '</svg>',

    // deel 0 = optimize, 1 = de policy, 2 = de toets tussen die twee
    keuze:
      '<svg viewBox="0 0 620 290" preserveAspectRatio="xMidYMid meet">' +
      '  <g class="f-deel aan" data-deel="0">' +
      '    <text class="f-tekst sterk" x="22" y="34">de zoeker</text>' +
      '    <rect class="f-vlak" x="22" y="46" width="82" height="48" rx="7"/>' +
      '    <text class="f-tekst klein" x="63" y="70" text-anchor="middle">één polder,</text><text class="f-tekst klein" x="63" y="84" text-anchor="middle">één bui</text>' +
      '    <path class="f-ink" d="M104 70 L146 70"/>' +
      '    <path class="f-ink" d="M138 64 L148 70 L138 76"/>' +
      '    <rect class="f-vlak" x="148" y="42" width="124" height="56" rx="7"/>' +
      '    <text class="f-tekst sterk" x="210" y="66" text-anchor="middle">31 combinaties</text>' +
      '    <text class="f-tekst klein" x="210" y="84" text-anchor="middle">elk exact opgelost</text>' +
      '    <path class="f-ink" d="M272 70 L314 70"/>' +
      '    <path class="f-ink" d="M306 64 L316 70 L306 76"/>' +
      '    <circle cx="334" cy="70" r="7" fill="var(--accent)"/>' +
      '    <text class="f-tekst sterk" x="356" y="66">één punt</text>' +
      '    <text class="f-tekst klein" x="356" y="84">overal hetzelfde getal</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="1">' +
      '    <text class="f-tekst sterk" x="22" y="196">een policy</text>' +
      '    <rect class="f-vlak" x="22" y="208" width="82" height="48" rx="7"/>' +
      '    <text class="f-tekst klein" x="63" y="232" text-anchor="middle">alle</text><text class="f-tekst klein" x="63" y="246" text-anchor="middle">polders</text>' +
      '    <path class="f-ink" d="M104 232 L146 232"/>' +
      '    <path class="f-ink" d="M138 226 L148 232 L138 238"/>' +
      '    <rect class="f-vlak" x="148" y="204" width="124" height="56" rx="7"/>' +
      '    <text class="f-tekst sterk" x="210" y="228" text-anchor="middle">training</text>' +
      '    <text class="f-tekst klein" x="210" y="246" text-anchor="middle">in het model</text>' +
      '    <path class="f-ink" d="M272 232 L314 232"/>' +
      '    <path class="f-ink" d="M306 226 L316 232 L306 238"/>' +
      '    <path class="f-droog" d="M326 250 C 344 250, 348 214, 370 214 C 392 214, 396 230, 414 230"/>' +
      '    <text class="f-tekst sterk" x="356" y="200">een functie</text>' +
      '    <text class="f-tekst klein" x="440" y="240">ook voor een ongeziene polder</text>' +
      '  </g>' +
      '  <g class="f-deel" data-deel="2">' +
      '    <path class="f-lijn" stroke-dasharray="4 4" d="M334 98 L334 200"/>' +
      '    <text class="f-tekst sterk" x="348" y="144">op één jaar horizon</text>' +
      '    <text class="f-tekst klein" x="348" y="162">moeten ze hetzelfde zeggen</text>' +
      '  </g>' +
      '</svg>',
  };

  // ─────────────────────────────────────────────────────────────────────────
  // Tekenen
  // ─────────────────────────────────────────────────────────────────────────
  var app = document.getElementById("app");

  function el(tag, klasse, tekst) {
    var n = document.createElement(tag);
    if (klasse) n.className = klasse;
    if (tekst != null) n.textContent = tekst;
    return n;
  }

  function kop(actief) {
    var n = el("div", "kop");

    var inZone = function (naam) {
      return INHOUD.stappen.filter(function (s) { return s.zone === naam; });
    };
    var voor = inZone("voor");
    var tuple = inZone("tuple");
    var buiten = inZone("buiten");
    var gezien = true;

    function chip(stap) {
      var b = el("button", "lid");
      b.appendChild(el("span", "sym", stap.sym));
      b.title = stap.titel;
      if (stap === actief) { b.classList.add("actief"); gezien = false; }
      else if (gezien) b.classList.add("gedaan");
      b.addEventListener("click", function () { naarStap(stap); });
      return b;
    }

    // Een stap in zone "voor" staat links van `M =`: hij gaat over het schema
    // zelf en niet over een lid ervan.
    voor.forEach(function (stap) {
      n.appendChild(chip(stap));
      n.appendChild(el("span", "scheiding", "⇒"));
    });

    n.appendChild(el("span", "mlabel", INHOUD.label));
    n.appendChild(el("span", "haak", INHOUD.open));

    tuple.forEach(function (stap, i) {
      if (i > 0) n.appendChild(el("span", "komma", ","));
      n.appendChild(chip(stap));
    });
    n.appendChild(el("span", "haak", INHOUD.sluit));

    buiten.forEach(function (stap, i) {
      n.appendChild(el("span", "scheiding", i === 0 ? "+" : "⇒"));
      n.appendChild(chip(stap));
    });
    return n;
  }

  function rijenTabel(stap, beat) {
    var toon = beat.toon == null ? stap.rijen.length : beat.toon;
    var nadruk = beat.nadruk || [];
    var tabel = el("table", "rijen");
    var body = el("tbody");
    stap.rijen.forEach(function (rij, i) {
      var tr = el("tr", i >= toon ? "uit" : nadruk.indexOf(i) >= 0 ? "aan nadruk" : "aan");
      tr.appendChild(el("td", "veld", rij[0]));
      tr.appendChild(el("td", "waarde", rij[1]));
      tr.appendChild(el("td", "uitleg", rij[2]));
      body.appendChild(tr);
    });
    tabel.appendChild(body);
    return tabel;
  }

  function figuurBlok(stap, beat) {
    var n = el("div", "figuur");
    // `beat.figuur` wint van `stap.figuur`. Zo kan één stap halverwege van
    // vulling wisselen zonder dat het een tweede stap wordt - de robot die een
    // polder wordt is precies dat.
    n.innerHTML = FIGUREN[beat.figuur || stap.figuur] || "";
    // Geen `nadruk` betekent "het eerste deel", een LEGE `nadruk` betekent
    // "nog niets" — dat is het verschil tussen een figuur die vanzelf begint
    // en een beat die de kale assen laat staan.
    var nadruk = beat.nadruk == null ? [0] : beat.nadruk;
    Array.prototype.forEach.call(n.querySelectorAll("[data-deel]"), function (g) {
      g.classList.toggle("aan", nadruk.indexOf(Number(g.getAttribute("data-deel"))) >= 0);
    });
    return n;
  }

  // Een video die per beat opnieuw in de DOM wordt gezet, springt terug naar
  // frame nul. Daarom houden we het ELEMENT vast zolang de bron dezelfde blijft:
  // twee beats over hetzelfde fragment lopen dan door in plaats van te herstarten.
  var lopendeVideo = null;

  function videoBlok(bron) {
    if (lopendeVideo && lopendeVideo.dataset.bron === bron) return lopendeVideo;
    var v = document.createElement("video");
    v.className = "video";
    v.dataset.bron = bron;
    v.src = bron;
    v.autoplay = true;
    v.loop = true;
    v.muted = true;          // anders weigert de browser autoplay
    v.playsInline = true;
    lopendeVideo = v;
    return v;
  }

  function toneel(stap, beat) {
    if (!stap) {
      var leeg = el("div", "toneel leeg");
      var blok = el("div");
      blok.appendChild(el("div", "titelkop", beat.kop));
      blok.appendChild(el("div", "titelonder", beat.onder));
      leeg.appendChild(blok);
      return leeg;
    }

    var n = el("div", "toneel");

    var zijde = el("div", "zijde");
    zijde.appendChild(el("div", "glyph", stap.sym));
    zijde.appendChild(el("div", "stap-titel", stap.titel));
    zijde.appendChild(el("div", "stap-formule", beat.formule || stap.formule));
    n.appendChild(zijde);

    var romp = el("div", "romp");
    if (beat.video) romp.appendChild(videoBlok(beat.video));
    else if (stap.figuur || beat.figuur) romp.appendChild(figuurBlok(stap, beat));
    else if (stap.rijen) romp.appendChild(rijenTabel(stap, beat));
    // Expliciet op undefined en niet op falsy: `bron: ""` op een beat betekent
    // "laat hem weg", en met `||` viel dat terug op de bron van de stap.
    var bron = beat.bron === undefined ? stap.bron : beat.bron;
    if (bron) romp.appendChild(el("div", "bron", bron));
    n.appendChild(romp);

    return n;
  }

  function voet(post) {
    var n = el("div", "voet");
    n.appendChild(el("div", "regel", post.beat.regel));

    var tellers = el("div", "tellers");
    for (var i = 0; i < post.van; i++) {
      var p = el("span", "punt" + (i <= post.index ? " aan" : ""));
      tellers.appendChild(p);
    }
    tellers.appendChild(el("span", "teller", nu + " / " + (BEATS.length - 1)));
    n.appendChild(tellers);
    return n;
  }

  function teken() {
    var post = BEATS[nu];
    app.replaceChildren(kop(post.stap), toneel(post.stap, post.beat), voet(post));
    var hash = post.stap ? post.stap.sleutel + "." + (post.index + 1) : "start";
    if (location.hash.slice(1) !== hash) history.replaceState(null, "", "#" + hash);
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Bediening. Elke stand is met het toetsenbord te bereiken, want op een
  // beamer staan de handen niet op de muis.
  // ─────────────────────────────────────────────────────────────────────────
  function ga(d) { nu = Math.min(BEATS.length - 1, Math.max(0, nu + d)); teken(); }

  function naarStap(stap) {
    for (var i = 0; i < BEATS.length; i++) {
      if (BEATS[i].stap === stap && BEATS[i].index === 0) { nu = i; teken(); return; }
    }
  }

  function naarSprong(d) {
    var hier = BEATS[nu].stap;
    var stappen = INHOUD.stappen;
    var i = stappen.indexOf(hier);
    if (d > 0) naarStap(stappen[Math.min(stappen.length - 1, i + 1)]);
    else if (i <= 0) { nu = 0; teken(); }
    else naarStap(stappen[i - 1]);
  }

  var hulp = document.getElementById("hulp");

  addEventListener("keydown", function (e) {
    var k = e.key;
    if (k === "ArrowRight" || k === " " || k === "PageDown" || k === "Enter") { ga(1); e.preventDefault(); }
    else if (k === "ArrowLeft" || k === "PageUp" || k === "Backspace") { ga(-1); e.preventDefault(); }
    else if (k === "ArrowDown") { naarSprong(1); e.preventDefault(); }
    else if (k === "ArrowUp") { naarSprong(-1); e.preventDefault(); }
    else if (k === "Home") { nu = 0; teken(); }
    else if (k === "End") { nu = BEATS.length - 1; teken(); }
    else if (k === "Escape") { if (!hulp.hidden) hulp.hidden = true; else { nu = 0; teken(); } }
    else if (k === "?" || k === "/") { hulp.hidden = !hulp.hidden; e.preventDefault(); }
    else if (k === "f") { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen(); }
    else if (k >= "1" && k <= "9") {
      var stap = INHOUD.stappen[Number(k) - 1];
      if (stap) naarStap(stap);
    }
  });

  // Klikken en tikken: rechterkant vooruit, linkerstrook terug. Alleen op het
  // TONEEL en de VOET, en niet op het hele document: een klik om het venster
  // naar voren te halen kwam anders binnen als "volgende beat", en die schoof
  // dan ongevraagd door terwijl de presentator nog niets gezegd had.
  addEventListener("click", function (e) {
    var binnen = e.target.closest(".toneel") || e.target.closest(".voet");
    if (!binnen) return;
    ga(e.clientX < innerWidth * 0.28 ? -1 : 1);
  });

  // Diep linken: #E.3 opent stap E op beat 3.
  function uitHash() {
    var h = decodeURIComponent(location.hash.slice(1));
    if (!h || h === "start") return;
    var deel = h.split(".");
    for (var i = 0; i < BEATS.length; i++) {
      var b = BEATS[i];
      if (b.stap && b.stap.sleutel === deel[0] && b.index === (Number(deel[1]) || 1) - 1) { nu = i; return; }
    }
  }

  // Een hash die verandert terwijl de pagina al open staat, laadt niets opnieuw.
  // Zonder deze regel doet een gedeelde link `#E.4` alleen iets bij een verse
  // load, en dat is precies wanneer je hem niet gebruikt.
  addEventListener("hashchange", function () { uitHash(); teken(); });

  uitHash();
  teken();
})();
