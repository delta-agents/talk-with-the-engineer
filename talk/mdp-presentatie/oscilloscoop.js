// ═══════════════════════════════════════════════════════════════════════════
// De oscilloscoop. Eén signaal, en je hoort het en ziet het tegelijk.
// ═══════════════════════════════════════════════════════════════════════════
//
// Een oscilloscoop in X-Y staat met zijn linkerkanaal op de horizontale as en
// zijn rechter op de verticale. Wie dus een stereosignaal maakt waarvan de twee
// kanalen samen een figuur uittekenen, hoort die figuur ook: de vorm ís de
// golfvorm. Dat is het idee waar Jerobeam Fenderson zijn oscilloscoopmuziek op
// bouwt, en het is precies wat deze stap nodig heeft.
//
// Want de bewering van π is dat het taalmodel niet rekent maar vertaalt, en dat
// er daarom geen gok op het scherm komt. Hier wordt die bewering hoorbaar:
//
//   achter  dezelfde ruis, maar zacht: een bed onder de eerste beats. Je hoort
//           dat er iets niet klopt voordat je ziet wat.
//   ruis    de vorm zit in het signaal, maar er ligt witte ruis overheen. Je
//           hoort gesis en je ziet een kluwen. Er staat iets, en niemand kan
//           zien wat.
//   schoon  de stekker gaat erin: dezelfde ruis komt er in TEGENFASE bij. De
//           som is nul - niet zachter, maar weg - en de polder staat er.
//   tik     en de grens: een tik die NA de opheffing wordt bijgemengd. Hij zit
//           niet in de ruis, dus valt er niets tegen weg te strepen. Je hoort
//           hem, en je ziet hem als een streep dwars door het beeld.
//
// De opheffing is geen truc met een volumeknop. Beide takken hangen aan
// DEZELFDE bron, dus ze schelen geen sample en de som is exact nul. Zou je hier
// het volume dichtdraaien, dan was de plaat een leugen.
//
// Zonder geluid werkt het beeld gewoon door: dan rekent dit bestand dezelfde
// punten uit in plaats van ze bij de analyser op te halen. Op een beamer zonder
// speakers staat er dus nog steeds een oscilloscoop - je hoort er alleen niets
// bij, en de zin "dit is wat u hoort" vervalt.

var OSCILLOSCOOP = (function () {
  "use strict";

  // ── de vorm die je hoort ────────────────────────────────────────────────
  //
  // De polderplaat van boven, in dezelfde 2,5D als de rest van de deck: een
  // ruit met de watergang er dwars doorheen. Hij is met opzet iets wat de zaal
  // al veertig beats gezien heeft, want het moment moet een herkenning zijn en
  // geen raadsel.
  //
  // Het is één gesloten lijn, want de scoop tilt zijn pen niet op. De ruit
  // wordt daarom deels dubbel gelopen; die stukken vallen samen met wat er al
  // staat en zijn dus onzichtbaar.
  var TOP = [0, 0.55], RECHTS = [0.95, 0], ONDER = [0, -0.55], LINKS = [-0.95, 0];
  var VORM = [TOP, RECHTS, ONDER, LINKS, TOP, RECHTS, LINKS, TOP];

  // Eén omloop in de buffer. Bij 48 kHz duurt die 2048/48000 s, en de toonhoogte
  // komt uit de afspeelsnelheid - zo hoort dezelfde vorm bij elke noot.
  var OMLOOP = 2048;

  // Een trage baslijn onder de sectie: A, C, E, D. Laag genoeg om onder een stem
  // door te lopen, en traag genoeg om niet om aandacht te vragen.
  var NOTEN = [110.0, 130.81, 164.81, 146.83];
  var NOOT_DUUR = 1.6;

  var RUIS_STERKTE = 0.34;
  var VORM_STERKTE = 0.42;
  var TIK_ELKE = 1.6;

  // ── de vorm bemonsteren op booglengte ───────────────────────────────────
  //
  // Op parameter bemonsteren zou de lange stukken sneller laten tekenen dan de
  // korte, en op een scoop is sneller hetzelfde als flauwer. Op booglengte
  // bemonsteren geeft een lijn die overal even fel staat.
  function bemonster(n) {
    var lengtes = [], totaal = 0, i;
    for (i = 0; i < VORM.length - 1; i++) {
      var dx = VORM[i + 1][0] - VORM[i][0], dy = VORM[i + 1][1] - VORM[i][1];
      lengtes.push(Math.sqrt(dx * dx + dy * dy));
      totaal += lengtes[i];
    }
    var punten = new Float32Array(n * 2), seg = 0, gelopen = 0;
    for (i = 0; i < n; i++) {
      var s = (i / n) * totaal;
      while (seg < lengtes.length - 1 && s > gelopen + lengtes[seg]) {
        gelopen += lengtes[seg];
        seg++;
      }
      var t = lengtes[seg] ? (s - gelopen) / lengtes[seg] : 0;
      punten[i * 2] = VORM[seg][0] + t * (VORM[seg + 1][0] - VORM[seg][0]);
      punten[i * 2 + 1] = VORM[seg][1] + t * (VORM[seg + 1][1] - VORM[seg][1]);
    }
    return punten;
  }

  var PUNTEN = bemonster(OMLOOP);

  // ── het geluid ──────────────────────────────────────────────────────────
  var ctx = null, mix = null, master = null, vormBron = null, ruisBron = null;
  var ruisTak = null, tegenTak = null, links = null, rechts = null;
  var tikKlok = null, stand = null;

  function bouw() {
    if (ctx) return true;
    var Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) return false;
    ctx = new Audio();

    // Twee knopen en niet één, en het verschil doet ertoe. Alles komt samen op
    // `mix`, en dáár kijkt de scoop naar; `master` is alleen het volume. Hing de
    // scoop erachter, dan zou de figuur krimpen als je zachter zet - en dan zegt
    // het beeld iets over de knop in plaats van over het signaal.
    mix = ctx.createGain();
    mix.gain.value = 1.0;
    master = ctx.createGain();
    master.gain.value = 0.0;
    mix.connect(master);

    // De vorm als één omloop in een stereobuffer, en de toonhoogte als
    // afspeelsnelheid erbovenop.
    var vb = ctx.createBuffer(2, OMLOOP, ctx.sampleRate);
    var vx = vb.getChannelData(0), vy = vb.getChannelData(1);
    for (var i = 0; i < OMLOOP; i++) {
      vx[i] = PUNTEN[i * 2] * VORM_STERKTE;
      vy[i] = PUNTEN[i * 2 + 1] * VORM_STERKTE;
    }
    vormBron = ctx.createBufferSource();
    vormBron.buffer = vb;
    vormBron.loop = true;
    vormBron.connect(mix);

    // Twee seconden ruis, en de twee kanalen los van elkaar: dan spat het beeld
    // in twee richtingen uiteen in plaats van dat het over één lijn trilt.
    var n = Math.floor(ctx.sampleRate * 2);
    var rb = ctx.createBuffer(2, n, ctx.sampleRate);
    for (var k = 0; k < 2; k++) {
      var kanaal = rb.getChannelData(k);
      for (var j = 0; j < n; j++) kanaal[j] = Math.random() * 2 - 1;
    }
    ruisBron = ctx.createBufferSource();
    ruisBron.buffer = rb;
    ruisBron.loop = true;

    // Hier zit de hele bewering. Twee takken aan DEZELFDE bron: de ene staat
    // altijd aan, de andere gaat op min één zodra de stekker erin gaat. Samen
    // exact nul - geen demping, maar opheffing.
    ruisTak = ctx.createGain();
    ruisTak.gain.value = RUIS_STERKTE;
    tegenTak = ctx.createGain();
    tegenTak.gain.value = 0;
    ruisBron.connect(ruisTak).connect(mix);
    ruisBron.connect(tegenTak).connect(mix);

    // De scoop kijkt naar de som van alles wat er klinkt - dezelfde golfvorm die
    // naar de speaker gaat, alleen zonder het volume erin verrekend.
    var splits = ctx.createChannelSplitter(2);
    links = ctx.createAnalyser();
    rechts = ctx.createAnalyser();
    links.fftSize = 2048;
    rechts.fftSize = 2048;
    mix.connect(splits);
    splits.connect(links, 0);
    splits.connect(rechts, 1);
    master.connect(ctx.destination);

    vormBron.start();
    ruisBron.start();
    noten();
    return true;
  }

  // De baslijn loopt door zolang de context leeft; hij hangt aan de klok van de
  // audiocontext en niet aan die van de pagina, dus hij blijft strak.
  function noten() {
    // Ruim twintig minuten vooruit ingepland: de baslijn hangt aan de klok van
    // de audiocontext en niet aan die van de pagina, en hij mag niet halverwege
    // een talk op zijn laatste noot blijven staan.
    var t = ctx.currentTime, ronden = 200;
    vormBron.playbackRate.cancelScheduledValues(t);
    for (var i = 0; i < ronden * NOTEN.length; i++) {
      var f = NOTEN[i % NOTEN.length];
      vormBron.playbackRate.setValueAtTime(f * OMLOOP / ctx.sampleRate, t + i * NOOT_DUUR);
    }
  }

  // De vorm van de tik, en die is met zorg gekozen. Een korte hoge toon zou
  // hoorbaar zijn maar het beeld alleen doen trillen: de figuur schuift dan heen
  // en weer en wordt wazig. Een BULT trekt hem één keer naar buiten en laat hem
  // terugkomen, en dat is wat je op een scoop als uithaal ziet. De rimpel
  // erbovenop doet niets voor het beeld en alles voor het oor.
  //
  // En hij moet KORT zijn, korter dan het venster van de analyser. Duurt de tik
  // langer dan die tweeduizend samples, dan staat het hele spoor even ergens
  // anders en wordt de figuur wazig in plaats van dat er iets uit schiet. Acht
  // milliseconde is ruim een vijfde van het venster: genoeg voor een uithaal die
  // je ziet, kort genoeg om de rest van de figuur te laten staan.
  var TIK_X = 0.55, TIK_Y = 0.38, TIK_DUUR = 0.008;

  function tikVorm(t) {
    var bult = Math.sin(Math.PI * t);
    return bult * bult * (0.78 + 0.22 * Math.sin(2 * Math.PI * 1600 * t * TIK_DUUR));
  }

  function tik() {
    if (!ctx) return;
    // NA de opheffing bijgemengd, en dus niet weg te strepen: deze tik zit niet
    // in de ruis waar de tegenfase van gemaakt is.
    var lengte = Math.floor(ctx.sampleRate * TIK_DUUR);
    var b = ctx.createBuffer(2, lengte, ctx.sampleRate);
    var a = b.getChannelData(0), c = b.getChannelData(1);
    for (var i = 0; i < lengte; i++) {
      var v = tikVorm(i / lengte);
      a[i] = TIK_X * v;
      c[i] = TIK_Y * v;
    }
    var bron = ctx.createBufferSource();
    bron.buffer = b;
    bron.connect(mix);
    bron.start();
  }

  // ── het beeld ───────────────────────────────────────────────────────────
  var doek = null, twee = null, lus = null, hint = null;
  var bufX = new Float32Array(2048), bufY = new Float32Array(2048);
  var grond = "#14181c", inkt = "#5cb3de", fase = 0;

  function kleuren() {
    var s = getComputedStyle(document.documentElement);
    grond = (s.getPropertyValue("--scoop-grond") || "#14181c").trim();
    inkt = (s.getPropertyValue("--scoop-inkt") || "#5cb3de").trim();
  }

  // Zonder draaiende audio zijn de analysers stil, en dan zou er een streepje
  // staan waar een figuur hoort. Dus rekent dit dezelfde punten uit: hetzelfde
  // beeld, alleen zonder de zin dat je het ook hoort.
  function zelfRekenen() {
    var f = NOTEN[Math.floor(fase / (NOOT_DUUR * 60)) % NOTEN.length];
    var perSample = f * OMLOOP / 48000;
    var ruis = stand === "ruis" || stand === "achter" ? RUIS_STERKTE : 0;
    // De tik hoort ook hier thuis: zonder geluid zou de beat over de grens van
    // de analogie een leeg scherm zijn, en juist die moet iets laten zien.
    var tikt = stand === "tik" && fase % Math.round(TIK_ELKE * 60) < 6;
    for (var i = 0; i < bufX.length; i++) {
      var p = Math.floor((fase * 900 + i * perSample) % OMLOOP);
      bufX[i] = PUNTEN[p * 2] * VORM_STERKTE + (Math.random() * 2 - 1) * ruis;
      bufY[i] = PUNTEN[p * 2 + 1] * VORM_STERKTE + (Math.random() * 2 - 1) * ruis;
      if (tikt && i < 380) {
        var v = tikVorm(i / 380);
        bufX[i] += TIK_X * v;
        bufY[i] += TIK_Y * v;
      }
    }
    fase++;
  }

  function teken() {
    lus = requestAnimationFrame(teken);
    if (!doek || !doek.clientWidth) return;

    var dpr = Math.min(2, window.devicePixelRatio || 1);
    var b = Math.round(doek.clientWidth * dpr), h = Math.round(doek.clientHeight * dpr);
    if (doek.width !== b || doek.height !== h) { doek.width = b; doek.height = h; }

    // Fosfor: het vorige beeld wordt niet gewist maar weggetrokken, en dat is
    // wat een spoor geeft in plaats van een flikkerende lijn.
    twee.globalCompositeOperation = "source-over";
    twee.fillStyle = grond;
    twee.globalAlpha = 0.30;
    twee.fillRect(0, 0, b, h);
    twee.globalAlpha = 1;

    if (ctx && ctx.state === "running") {
      links.getFloatTimeDomainData(bufX);
      rechts.getFloatTimeDomainData(bufY);
    } else {
      zelfRekenen();
    }

    // De straal is zo gekozen dat de wolk NET binnen het scherm blijft: de ruis
    // reikt tot ruim anderhalf keer de vorm, en wat eraf loopt zou als een
    // rechte rand lezen die er niet is.
    var mx = b / 2, my = h / 2, r = Math.min(b * 0.28, h * 0.36);
    twee.globalCompositeOperation = "lighter";
    twee.strokeStyle = inkt;
    twee.lineWidth = Math.max(1, 1.6 * dpr);
    twee.lineJoin = "round";
    twee.lineCap = "round";
    // Additief mengen loopt bij duizenden lijnstukken vol tot wit. Laag genoeg
    // gezet wordt de ruis een krabbel, terwijl de vorm - die elke omloop
    // dezelfde pixels aandoet - er nog steeds doorheen brandt.
    twee.globalAlpha = 0.15;
    twee.beginPath();
    for (var i = 0; i < bufX.length; i++) {
      var x = mx + bufX[i] / VORM_STERKTE * r;
      var y = my - bufY[i] / VORM_STERKTE * r;
      if (i === 0) twee.moveTo(x, y); else twee.lineTo(x, y);
    }
    twee.stroke();
    twee.globalAlpha = 1;
    twee.globalCompositeOperation = "source-over";
  }

  // ── wat de presentatie ervan gebruikt ───────────────────────────────────
  function blok() {
    var wrap = document.createElement("div");
    wrap.className = "scoopblok";
    doek = document.createElement("canvas");
    doek.className = "scoop";
    wrap.appendChild(doek);
    hint = document.createElement("span");
    hint.className = "geluidhint";
    hint.textContent = "klik voor geluid";
    wrap.appendChild(hint);
    twee = doek.getContext("2d");
    kleuren();
    if (!lus) teken();
    return wrap;
  }

  // Elke beat dwingt de stand af, net als de regel dat hoogstens één video mag
  // spelen. Geen opruimpad dat je ergens kunt missen: wie geen stand vraagt,
  // krijgt stilte.
  function zet(nieuw) {
    if (nieuw && !bouw()) nieuw = null;
    stand = nieuw || null;

    if (tikKlok) { clearInterval(tikKlok); tikKlok = null; }
    if (!ctx) return;

    if (!stand) {
      master.gain.setTargetAtTime(0, ctx.currentTime, 0.05);
      if (lus) { cancelAnimationFrame(lus); lus = null; }
      return;
    }
    if (!lus && doek) teken();
    kleuren();

    // Onder de eerste beats staat hij zacht: daar praat er iemand overheen, en
    // het gesis hoeft daar alleen op te vallen en niet te storen.
    master.gain.setTargetAtTime(stand === "achter" ? 0.22 : 0.5, ctx.currentTime, 0.08);
    // De stekker: van nul naar min één in een kwart seconde. Kort genoeg om als
    // schakelen te lezen, lang genoeg om niet te ploffen.
    var opgeheven = stand === "schoon" || stand === "tik";
    tegenTak.gain.setTargetAtTime(opgeheven ? -RUIS_STERKTE : 0, ctx.currentTime, 0.07);
    if (stand === "tik") tikKlok = setInterval(tik, TIK_ELKE * 1000);
    wek();
  }

  // Een browser start geen geluid zonder dat er iets aangeraakt is. In een zaal
  // is dat pijltje al ingedrukt voordat je hier bent, maar niet als iemand
  // rechtstreeks op de hash binnenkomt - dus blijft dit bij elke toets proberen.
  function wek() {
    if (!ctx) return;
    if (ctx.state === "suspended") ctx.resume();
    if (hint) hint.hidden = ctx.state === "running";
  }

  addEventListener("resize", kleuren);

  return { blok: blok, zet: zet, wek: wek };
})();
