// ═══════════════════════════════════════════════════════════════════════════
// De oscilloscoop. Eén signaal, en je hoort het en ziet het tegelijk.
// ═══════════════════════════════════════════════════════════════════════════
//
// Een oscilloscoop in X-Y zet zijn linkerkanaal op de horizontale as en zijn
// rechter op de verticale. Wie dus een stereosignaal maakt waarvan de twee
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
//           hem, en je ziet hem als een uithaal dwars door het beeld.
//
// De opheffing is geen truc met een volumeknop. Beide takken hangen aan
// DEZELFDE bron, dus ze schelen geen sample en de som is exact nul. Zou hier
// het volume dichtgedraaid worden, dan was de plaat een leugen.
//
// Zonder geluid werkt het beeld gewoon door: dan leest dit bestand hetzelfde
// stuk uit het geheugen in plaats van bij de analyser. Op een beamer zonder
// speakers staat er dus nog steeds een oscilloscoop - je hoort er alleen niets
// bij, en de zin "dit is wat u hoort" vervalt.

var OSCILLOSCOOP = (function () {
  "use strict";

  // ═════════════════════════════════════════════════════════════════════════
  // Het stuk
  // ═════════════════════════════════════════════════════════════════════════
  //
  // Eén stem, en dat is geen zuinigheid. Twee stemmen bij elkaar optellen geeft
  // op een scoop hun SOM en niet hun beide figuren, dus wie harmonie wil moet
  // om en om tekenen - en dan flikkert het beeld tussen twee dingen. Eén stem
  // met een vorm die beweegt houdt het beeld heel, en de beweging doet het werk
  // dat een tweede stem anders zou doen.
  //
  // Wat er beweegt is het WATERPEIL, en dat is niet zomaar iets moois: het is
  // waar deze hele talk over gaat. De polderplaat staat stil, en het water erin
  // komt op en zakt weer. Omdat de ruit naar boven toe smaller wordt, wordt de
  // waterlijn korter naarmate hij stijgt - dat klopt meetkundig, en het leest
  // meteen.
  //
  // En het is ook de muziek. De vorm bepaalt de klankkleur, dus een stijgend
  // peil is een verschuivend timbre: je hóórt het water komen. Dat is de reden
  // dat dit stuk niet uit noten bestaat maar uit één lijn die van vorm verandert.

  // De ruit van de polderplaat, in dezelfde 2,5D als de rest van de deck.
  var HALF_B = 0.95;  // halve breedte, bij het peil van de watergang
  var HALF_H = 0.55;  // halve hoogte, van de onderpunt tot de bovenpunt

  // Vier maten van twee seconden. De grondtonen zijn zo bijgesteld dat er per
  // maat een HEEL aantal omlopen in past - anders springt de fase bij de naad
  // van de lus en tikt het stuk elke acht seconden.
  var AKKOORD = [110, 87.5, 131, 98];
  var MAAT = 2.0;
  var DUUR = MAAT * AKKOORD.length;
  var TEL = 0.5;  // honderdtwintig slagen per minuut

  var PEIL_LAAG = 0.03;
  var PEIL_HOOG = 0.44;

  var VORM_STERKTE = 0.42;
  var RUIS_STERKTE = 0.34;

  // De halve breedte van de ruit op hoogte v. Boven is hij nul, en dat is
  // precies waarom de waterlijn korter wordt als het peil stijgt.
  function breedteOp(v) {
    return HALF_B * (1 - Math.abs(v) / HALF_H);
  }

  // Het pad bij één waterstand, als één gesloten lijn - want een scoop tilt zijn
  // pen niet op. Elk stuk ligt op de ruit of op de waterlijn zelf; de stukken
  // die dubbel gelopen worden vallen samen met wat er al staat en zijn dus niet
  // te zien.
  //
  //   links → waterlijn links → waterlijn rechts → en terug → top →
  //   rechts → onder → links
  function padBij(v) {
    var w = breedteOp(v);
    return [
      [-HALF_B, 0], [-w, v], [w, v], [-w, v],
      [0, HALF_H], [w, v], [HALF_B, 0], [0, -HALF_H], [-HALF_B, 0]
    ];
  }

  // Op booglengte lopen en niet op parameter: anders wordt een lang stuk sneller
  // getekend dan een kort, en op een scoop is sneller hetzelfde als flauwer.
  // Geeft x, y en het nummer van het stuk, want de rimpel hoort alleen op het
  // water thuis.
  var _uit = [0, 0, 0];

  function langs(punten, u) {
    var i, totaal = 0, lengte = [];
    for (i = 0; i < punten.length - 1; i++) {
      var dx = punten[i + 1][0] - punten[i][0];
      var dy = punten[i + 1][1] - punten[i][1];
      lengte.push(Math.sqrt(dx * dx + dy * dy));
      totaal += lengte[i];
    }
    var s = u * totaal, gelopen = 0, seg = 0;
    while (seg < lengte.length - 1 && s > gelopen + lengte[seg]) {
      gelopen += lengte[seg];
      seg++;
    }
    var t = lengte[seg] > 1e-9 ? (s - gelopen) / lengte[seg] : 0;
    _uit[0] = punten[seg][0] + t * (punten[seg + 1][0] - punten[seg][0]);
    _uit[1] = punten[seg][1] + t * (punten[seg + 1][1] - punten[seg][1]);
    _uit[2] = seg;
    return _uit;
  }

  // Het hele stuk wordt in één keer uitgerekend en daarna in de rondte gespeeld.
  // Dat is met opzet geen worklet: die moet zijn code ophalen, en dat gaat stuk
  // op file:// - en offline draaien is voor deze deck een eis. Vooraf uitrekenen
  // kan alles wat een worklet kan, hapert nooit, en is na te rekenen.
  var STUK = null;

  function stukVoor(sr) {
    if (STUK && STUK.sr === sr) return STUK;
    var n = Math.round(sr * DUUR);
    var L = new Float32Array(n), R = new Float32Array(n);
    var fase = 0, piek = 0;
    for (var i = 0; i < n; i++) {
      var t = i / sr;
      fase = (fase + AKKOORD[Math.floor(t / MAAT) % AKKOORD.length] / sr) % 1;

      // Eén golf per lus, met een vlakke raaklijn aan beide kanten van de naad:
      // het water komt op en zakt terug zonder dat je hoort waar de lus rond is.
      var v = PEIL_LAAG + (PEIL_HOOG - PEIL_LAAG) *
              (1 - Math.cos(2 * Math.PI * t / DUUR)) / 2;

      var p = langs(padBij(v), fase);
      var x = p[0], y = p[1];

      // De rimpel staat alleen op het WATER - stuk 1 en 2, en geen van de vier
      // ribben - en hij groeit mee met de stand. Voor het oog is het beweging op
      // de lijn; voor het oor een boventoon die met het peil mee opkomt.
      //
      // Dat het water twee keer gelopen wordt, heen en terug, is hier geen
      // verspilling: de rimpel staat op de terugweg een stuk verder in zijn
      // periode, dus de twee passages vallen niet samen. Er staat daardoor geen
      // lijn maar een BAND - water met een oppervlak, in plaats van een streep.
      // Omdat de rimpel een hele boventoon is, is dat patroon elke omloop
      // hetzelfde en staat de band stil in plaats van te flikkeren.
      if (p[2] === 1 || p[2] === 2) {
        y += 0.014 * (v / PEIL_HOOG) * Math.sin(2 * Math.PI * 9 * fase);
      }

      // En de maat: een korte zwelling per tel, zodat de plaat ademt in plaats
      // van stil te staan.
      //
      // De aanslag moet een HELLING zijn en geen sprong. Springt hij, dan staat
      // er twee keer per seconde een knik in de golf - dat tikt hoorbaar, en de
      // plaat verspringt zichtbaar van formaat. Zes milliseconde omhoog is te
      // kort om als aanzet te horen en lang genoeg om de knik weg te halen.
      // Diezelfde helling maakt ook de naad van de lus glad, want daar valt de
      // tel precies op nul.
      var tb = t % TEL;
      var env = 0.86 + 0.14 * Math.min(1, tb / 0.006) * Math.exp(-tb / 0.085);
      L[i] = x * VORM_STERKTE * env;
      R[i] = y * VORM_STERKTE * env;
      piek = Math.max(piek, Math.abs(L[i]), Math.abs(R[i]));
    }
    STUK = { sr: sr, L: L, R: R, n: n, piek: piek };
    return STUK;
  }

  // ═════════════════════════════════════════════════════════════════════════
  // Het geluid
  // ═════════════════════════════════════════════════════════════════════════
  var ctx = null, mix = null, master = null, ruisBron = null;
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

    var s = stukVoor(ctx.sampleRate);
    var sb = ctx.createBuffer(2, s.n, ctx.sampleRate);
    sb.getChannelData(0).set(s.L);
    sb.getChannelData(1).set(s.R);
    var stem = ctx.createBufferSource();
    stem.buffer = sb;
    stem.loop = true;
    stem.connect(mix);

    // Twee seconden ruis, en de twee kanalen los van elkaar: dan spat het beeld
    // in twee richtingen uiteen in plaats van dat het over één lijn trilt.
    var m = Math.floor(ctx.sampleRate * 2);
    var rb = ctx.createBuffer(2, m, ctx.sampleRate);
    for (var k = 0; k < 2; k++) {
      var kanaal = rb.getChannelData(k);
      for (var j = 0; j < m; j++) kanaal[j] = Math.random() * 2 - 1;
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

    stem.start();
    ruisBron.start();
    return true;
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
  var TIK_X = 0.55, TIK_Y = 0.38, TIK_DUUR = 0.008, TIK_ELKE = 1.6;

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

  // ═════════════════════════════════════════════════════════════════════════
  // Het beeld
  // ═════════════════════════════════════════════════════════════════════════
  var doek = null, twee = null, lus = null, hint = null;
  var bufX = new Float32Array(2048), bufY = new Float32Array(2048);
  var grond = "#0b1013", inkt = "#6ecbf5", kop = 0;

  function kleuren() {
    var s = getComputedStyle(document.documentElement);
    grond = (s.getPropertyValue("--scoop-grond") || "#0b1013").trim();
    inkt = (s.getPropertyValue("--scoop-inkt") || "#6ecbf5").trim();
  }

  // Zonder draaiende audio zijn de analysers stil, en dan zou er een streepje
  // staan waar een figuur hoort. Dus leest dit hetzelfde stuk uit het geheugen,
  // met een eigen leeskop: precies hetzelfde beeld, alleen zonder de zin dat je
  // het ook hoort.
  function zelfRekenen() {
    var s = stukVoor(48000);
    var ruis = stand === "ruis" || stand === "achter" ? RUIS_STERKTE : 0;
    // De tik hoort ook hier thuis: zonder geluid zou de beat over de grens van
    // de analogie een leeg scherm zijn, en juist die moet iets laten zien.
    var tikt = stand === "tik" && (kop / s.sr) % TIK_ELKE < 1 / 60;
    for (var i = 0; i < bufX.length; i++) {
      var j = (kop + i) % s.n;
      bufX[i] = s.L[j] + (Math.random() * 2 - 1) * ruis;
      bufY[i] = s.R[j] + (Math.random() * 2 - 1) * ruis;
      if (tikt && i < 380) {
        var v = tikVorm(i / 380);
        bufX[i] += TIK_X * v;
        bufY[i] += TIK_Y * v;
      }
    }
    kop = (kop + Math.round(s.sr / 60)) % s.n;
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

  // ═════════════════════════════════════════════════════════════════════════
  // Wat de presentatie ervan gebruikt
  // ═════════════════════════════════════════════════════════════════════════
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

  return { blok: blok, zet: zet, wek: wek, _stuk: stukVoor };
})();

if (typeof module !== "undefined") module.exports = OSCILLOSCOOP;
