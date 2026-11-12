// ═══════════════════════════════════════════════════════════════════════════
// De machinerie. Hier zit geen inhoud in — die staat in inhoud.js — en geen
// tekening: die staan in teken/ en worden geregistreerd in figuren.js.
// ═══════════════════════════════════════════════════════════════════════════
//
// Geen framework, geen import, geen netwerk. Klassieke scripts, dus dit werkt
// ook als je het bestand dubbelklikt en ook als de zaal geen wifi heeft. Dat is
// geen zuinigheid maar de eis: een presentatie die op een netwerkfout kan
// stukvallen, is geen presentatie. Daarom ook geen ES-modules: `import` valt op
// `file://` om op CORS, en een reeks script-tags in de goede volgorde niet.
//
// De hele toestand is één getal: welke beat staat er. Alles op het scherm is
// een functie van dat getal, dus terug kunnen is gratis en er bestaat geen
// stand die je alleen met de muis kunt bereiken.
//
// Dit is het enige bestand met een eigen binnenkant: alles hieronder blijft
// binnen de IIFE, want niets ervan is voor een figuur bedoeld.

(function () {
  "use strict";

  var FIGUREN = TEKEN.FIGUREN;

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

  var ROUTE = INHOUD.stappen.filter(function (s) { return s.zone === "route"; });
  var ROUTE_BEATS = BEATS.filter(function (b) { return ROUTE.indexOf(b.stap) >= 0; }).length;

  var nu = 0;

  // Boven dit aantal beats gaan de puntjes op twee rijen.
  var PUNTEN_PER_RIJ = 14;


  // ──────────────────────────────────────────────────────────────────────────
  // Tekenen
  // ──────────────────────────────────────────────────────────────────────────
  var app = document.getElementById("app");

  function el(tag, klasse, tekst) {
    var n = document.createElement(tag);
    if (klasse) n.className = klasse;
    if (tekst != null) n.textContent = tekst;
    return n;
  }

  // De kop is de route: de stappen in zone "route", als woorden met een pijl
  // ertussen. Een reservestap staat er niet in, en dan is geen enkel woord actief.
  function kop(actief) {
    var n = el("div", "kop");
    var gezien = ROUTE.indexOf(actief) >= 0;
    ROUTE.forEach(function (stap, i) {
      if (i > 0) n.appendChild(el("span", "scheiding", "⇒"));
      var b = el("button", "lid", stap.kop);
      b.title = stap.titel;
      if (stap === actief) { b.classList.add("actief"); gezien = false; }
      else if (gezien) b.classList.add("gedaan");
      b.addEventListener("click", function () { naarStap(stap); });
      n.appendChild(b);
    });
    return n;
  }

  // ── Media die blijft staan ────────────────────────────────────────────────
  //
  // Een element dat uit het document wordt gehaald en er weer in gezet, begint
  // zijn CSS-animatie opnieuw en een video springt terug naar frame nul. Twee
  // beats over dezelfde bui lieten de bui dus twee keer bij dag 1 beginnen -
  // gemeten 1487 ms terug naar 184 ms - en dan hoort de zaal "en dan loopt het
  // land onder" terwijl er nog niets gebeurd is.
  //
  // Daarom draagt elk stuk media een SLEUTEL. Verandert de sleutel niet, dan
  // blijft het element staan en werken we alleen bij wat er wél verschilt: welke
  // delen oplichten, en welke rijen zichtbaar zijn.
  var media = { sleutel: null, el: null };

  function mediaSleutel(stap, beat) {
    if (beat.video) return "video:" + beat.video;
    var f = beat.figuur || stap.figuur;
    if (f) return "figuur:" + f;
    if (stap.rijen) return "rijen:" + stap.sleutel;
    return null;
  }

  function figuurBlok(naam) {
    var n = el("div", "figuur");
    n.innerHTML = FIGUREN[naam] || "";
    return n;
  }

  // Video's die zichzelf willen starten MET geluid worden door elke browser
  // geweigerd zolang er nog geen gebruikersactie op de pagina is geweest. In een
  // presentatie is die actie er meestal wel - je drukt op een pijltje om hier te
  // komen - maar niet als iemand rechtstreeks op `#W.1` binnenkomt.
  //
  // Daarom: probeer met geluid, en val bij een weigering terug op stil in plaats
  // van op stilstand. Het blokje eromheen zegt dan dat je erop kunt klikken, en
  // elke volgende toets of klik zet het geluid alsnog aan.
  var stilGevallen = [];

  function stilMarkeren(v) {
    var wrap = v.parentNode;
    if (wrap && wrap.classList.contains("videoblok")) {
      if (v.muted) wrap.setAttribute("data-stil", "");
      else wrap.removeAttribute("data-stil");
    }
  }

  function videoBlok(bron) {
    var wrap = el("div", "videoblok");
    var v = document.createElement("video");
    v.className = "video";
    v.src = bron;
    v.loop = true;
    v.playsInline = true;
    v.autoplay = true;
    v.muted = false;
    wrap.appendChild(v);
    wrap.appendChild(el("span", "geluidhint", "click for sound"));
    alleVideos.push(v);

    // Pas ná het volgende frame, want dan staat het element in het document;
    // `play()` op een losse knoop is onnodig wankel.
    requestAnimationFrame(function () {
      var poging = v.play();
      if (poging && poging.catch) {
        poging.catch(function () {
          v.muted = true;
          stilMarkeren(v);
          if (stilGevallen.indexOf(v) < 0) stilGevallen.push(v);
          v.play();
        });
      }
    });
    return wrap;
  }

  // GEEN `once`: de eerste toetsaanslag kan al voorbij zijn voordat de video
  // bestaat, en dan zou het geluid nooit meer terugkomen.
  function geluidAan() {
    if (!stilGevallen.length) return;
    stilGevallen.forEach(function (v) { v.muted = false; stilMarkeren(v); });
    stilGevallen = [];
  }
  addEventListener("keydown", geluidAan);

  // Drie of VIER kolommen. De vierde bestaat voor de maatregelen, waar heen en
  // terug naast elkaar horen te staan in plaats van in aparte beats.
  function rijenTabel(stap) {
    var breed = stap.rijen.some(function (r) { return r.length > 3; });
    var tabel = el("table", "rijen" + (breed ? " vier" : ""));
    var body = el("tbody");
    stap.rijen.forEach(function (rij) {
      var tr = el("tr");
      tr.appendChild(el("td", "veld", rij[0]));
      tr.appendChild(el("td", "waarde", rij[1]));
      tr.appendChild(el("td", "uitleg", rij[2]));
      if (breed) tr.appendChild(el("td", "uitleg terug", rij[3] || ""));
      body.appendChild(tr);
    });
    tabel.appendChild(body);
    return tabel;
  }

  // Alles wat per beat verschilt maar het element niet vervangt.
  function stemAf(node, stap, beat) {
    // Geen `nadruk` betekent "het eerste deel", een LEGE `nadruk` betekent
    // "nog niets" - dat is het verschil tussen een figuur die vanzelf begint
    // en een beat die de kale assen laat staan.
    var nadruk = beat.nadruk == null ? [0] : beat.nadruk;
    Array.prototype.forEach.call(node.querySelectorAll("[data-deel]"), function (g) {
      g.classList.toggle("aan", nadruk.indexOf(Number(g.getAttribute("data-deel"))) >= 0);
    });
    var rijen = node.querySelectorAll("tr");
    if (rijen.length && stap.rijen) {
      var toon = beat.toon == null ? stap.rijen.length : beat.toon;
      Array.prototype.forEach.call(rijen, function (tr, i) {
        tr.className = i >= toon ? "uit"
          : nadruk.indexOf(i) >= 0 ? "aan nadruk" : "aan";
      });
    }
  }

  // Een `<video>` die uit de DOM wordt gehaald STOPT NIET: hij speelt
  // gedetacheerd door, en dan hoor je de clip nog terwijl er al een andere slide
  // staat. Alleen de knoop weggooien is dus niet genoeg.
  //
  // Dit stond eerst als opruimpad op de twee plekken waar media wordt
  // weggegooid, en dat bleef fout gaan: er is altijd nog een route waarlangs een
  // element blijft hangen. Nu is het een INVARIANT die `teken()` bij ELKE beat
  // afdwingt - hoogstens een video mag spelen, en alleen die op het toneel staat.
  var alleVideos = [];

  function videosOpHetToneel() {
    if (!media.el) return [];
    return media.el.tagName === "VIDEO"
      ? [media.el]
      : Array.prototype.slice.call(media.el.querySelectorAll("video"));
  }

  function alleenDezeMagSpelen() {
    var op = videosOpHetToneel();
    alleVideos.forEach(function (v) {
      if (op.indexOf(v) >= 0) return;
      v.pause();
      var i = stilGevallen.indexOf(v);
      if (i >= 0) stilGevallen.splice(i, 1);
    });
    // Wat nergens meer aan hangt hoeft ook niet meer bewaakt te worden.
    alleVideos = alleVideos.filter(function (v) {
      return op.indexOf(v) >= 0 || document.contains(v);
    });
  }

  function mediaVoor(stap, beat) {
    var sleutel = mediaSleutel(stap, beat);
    if (sleutel === null) {
      media.sleutel = null;
      media.el = null;
      return null;
    }
    if (media.sleutel !== sleutel) {
      media.sleutel = sleutel;
      media.el = beat.video ? videoBlok(beat.video)
        : (beat.figuur || stap.figuur) ? figuurBlok(beat.figuur || stap.figuur)
        : rijenTabel(stap);
    }
    stemAf(media.el, stap, beat);
    return media.el;
  }

  // Het toneel, de zijde en de romp BLIJVEN staan; alleen hun inhoud wisselt.
  // Zodra je een van die drie per beat opnieuw opbouwt, raakt de media even los
  // van het document, en dat alleen al herstart elke animatie erin.
  var zijdeEl = el("div", "zijde");
  var rompEl = el("div", "romp");
  var titelEl = el("div");
  var bronEl = el("div", "bron");

  function vulToneel(n, stap, beat) {
    n.className = "toneel" + (stap ? "" : " leeg");

    if (!stap) {
      // De titelbeat heeft geen media om te sparen, dus hier mag het simpel.
      media.sleutel = null;
      media.el = null;
      // Alleen de kop. Een ondertitel is een tweede bewering op een scherm dat
      // er nog maar één nodig heeft, en de voet zegt al waar we beginnen.
      titelEl.replaceChildren(el("div", "titelkop", beat.kop));
      var wie = el("div", "wie"), afzender = el("div", "afzender");
      wie.replaceChildren.apply(wie, beat.afzender.map(function (r) { return el("div", "", r); }));
      afzender.replaceChildren(wie, Object.assign(el("img"), { src: "hkv-logo.png", alt: "HKV" }));
      n.replaceChildren(titelEl, afzender);
      return;
    }

    var glyph = el("div", "glyph", stap.sym);
    zijdeEl.replaceChildren(
      glyph,
      el("div", "stap-titel", beat.titel || stap.titel),
      el("div", "stap-formule", beat.formule || stap.formule));

    var m = mediaVoor(stap, beat);
    if (m && m.parentNode !== rompEl) rompEl.replaceChildren(m);
    else if (!m) rompEl.replaceChildren();

    var bron = beat.bron === undefined ? stap.bron : beat.bron;
    bronEl.textContent = bron || "";
    bronEl.hidden = !bron;
    if (bronEl.parentNode !== rompEl) rompEl.appendChild(bronEl);

    if (zijdeEl.parentNode !== n) n.replaceChildren(zijdeEl, rompEl);
  }

  function voet(post) {
    var n = el("div", "voet");

    // De zin die de presentator zegt staat niet op het scherm: hij zit achter
    // een knopje en verschijnt bij hover, of blijft staan na een klik of `n`.
    var notitie = el("div", "notitie");
    notitie.appendChild(el("button", "knop", "notes"));
    notitie.appendChild(el("div", "regel", post.beat.regel));
    n.appendChild(notitie);

    var tellers = el("div", "tellers");

    // Voorbij PUNTEN_PER_RIJ wordt een enkele rij een streepjescode. Twee rijen
    // met evenveel kolommen leest wel: een raster vult rij voor rij, dus de
    // volgorde blijft van links naar rechts en dan naar beneden.
    var kolommen = post.van > PUNTEN_PER_RIJ ? Math.ceil(post.van / 2) : post.van;
    var punten = el("div", "punten");
    punten.style.gridTemplateColumns = "repeat(" + kolommen + ", auto)";
    for (var i = 0; i < post.van; i++) {
      punten.appendChild(el("span", "punt" + (i <= post.index ? " aan" : "")));
    }
    tellers.appendChild(punten);
    tellers.appendChild(el("span", "teller",
      nu > ROUTE_BEATS ? "reserve" : nu + " / " + ROUTE_BEATS));
    n.appendChild(tellers);
    return n;
  }

  var kopEl = el("div", "kop");
  var toneelEl = el("div", "toneel");
  var voetEl = el("div", "voet");
  app.replaceChildren(kopEl, toneelEl, voetEl);

  // Tekst in een figuur telt in eenheden van de viewBox, dus hoe groter de
  // figuur wordt uitgetekend, hoe kleiner diezelfde tekst op het scherm staat.
  // Dit zet de omgekeerde schaal als `--px`, en `style.css` rekent daarmee terug
  // naar een vast aantal pixels. Zo leest een plaat van 880 bij 520 net zo goed
  // als een van 660 bij 340.
  function schaalFiguur() {
    var n = toneelEl.querySelector(".figuur");
    var svg = n && n.querySelector("svg");
    if (!svg || !svg.viewBox.baseVal.width) return;
    var vb = svg.viewBox.baseVal;
    var r = svg.getBoundingClientRect();
    if (!r.width || !r.height) return;
    var s = Math.min(r.width / vb.width, r.height / vb.height);
    if (s > 0) n.style.setProperty("--px", (1 / s).toFixed(4));
  }

  addEventListener("resize", schaalFiguur);

  function teken() {
    var post = BEATS[nu];
    kopEl.replaceChildren.apply(kopEl, Array.prototype.slice.call(kop(post.stap).childNodes));
    vulToneel(toneelEl, post.stap, post.beat);
    alleenDezeMagSpelen();
    voetEl.replaceChildren.apply(voetEl, Array.prototype.slice.call(voet(post).childNodes));
    schaalFiguur();
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
    else if (k === "n") voetEl.classList.toggle("vast");
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
  //
  // Op de VIDEO is een klik het geluid en niet de volgende beat. Anders kun je
  // het geluid niet aanzetten zonder de slide kwijt te raken.
  addEventListener("click", function (e) {
    var blok = e.target.closest(".videoblok");
    if (blok) {
      var v = blok.querySelector("video");
      v.muted = !v.muted;
      if (!v.muted) {
        var i = stilGevallen.indexOf(v);
        if (i >= 0) stilGevallen.splice(i, 1);
      }
      stilMarkeren(v);
      v.play();
      return;
    }
    geluidAan();
    var knop = e.target.closest(".notitie .knop");
    if (knop) { voetEl.classList.toggle("vast"); knop.blur(); return; }
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
