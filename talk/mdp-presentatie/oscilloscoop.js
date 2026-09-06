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

  // De polderplaat, in exact dezelfde 2,5D als de plaat bij ⟳. De meetkunde is
  // niet nagemaakt maar overgenomen: dezelfde isometrie, dezelfde verhouding van
  // dikte tot halve diagonaal (22 op 168), dezelfde watergang op vijf procent.
  //
  //     schermx = (x - y) · cos30        schermy = (x + y) · sin30
  //
  // `x` en `y` lopen van 0 tot 1 over de plaat. Hier staat de y-as omhoog, want
  // een scoop rekent zo, en `MIDDEN` schuift de figuur om zijn eigen midden.
  var COS30 = 0.8660254, SIN30 = 0.5;
  var DIK = 22 / 168;
  var SCHAAL = 1.05;
  var MIDDEN = (1 + DIK) / 2;

  function plek(x, y, zak) {
    return [
      (x - y) * COS30 * SCHAAL,
      (MIDDEN - (x + y) * SIN30 - (zak ? DIK : 0)) * SCHAAL
    ];
  }

  // Waar de figuur eindigt, en dat komt uit de meetkunde hierboven en niet uit
  // een schatting: de hoekpunten links en rechts, en de bovenpunt tegen de
  // onderrand van de wand.
  var HALF_B = COS30 * SCHAAL;
  var HALF_H = MIDDEN * SCHAAL;

  // Twee dingen bewegen, en ze bewegen in verschillend tempo.
  //
  // De WATERGANG zwelt en krimpt over de hele lus - het water dat opkomt en weer
  // zakt. Dat is de trage beweging, en omdat de vorm de klankkleur bepaalt, is
  // het ook de muziek: je hoort het water komen.
  //
  // Het GEMAAL klopt op de tel. Dat is de maat, en die zit nu in het gemaal in
  // plaats van in de hele plaat - een plaat die twee keer per seconde van
  // formaat verspringt leest als een fout, een gemaal dat pompt niet.
  // Vier maten van VIER seconden. De grondtonen zijn zo bijgesteld dat er per
  // maat een HEEL aantal omlopen in past - anders springt de fase bij de naad
  // van de lus en tikt het stuk elke ronde.
  //
  // Trager dan het eerst was, en dat is de helft van waarom dit geen brom meer
  // is: een akkoordwissel elke twee seconden vraagt aandacht, elke vier seconden
  // ligt hij eronder.
  var AKKOORD = [110, 87.5, 131, 98];
  var MAAT = 4.0;
  var DUUR = MAAT * AKKOORD.length;
  var TEL = 0.5;  // honderdtwintig slagen per minuut

  // Een trage triller, zes hele perioden per lus.
  //
  // Hij verschuift de FASE en niet de frequentie, en dat is geen detail. Als
  // factor op de frequentie loopt hij weg: de akkoorden duren even lang maar
  // zijn niet even hoog, dus weegt elke maat de sinus anders en telt hij niet
  // meer op tot nul. Gemeten was de lus daardoor 1705,89 omlopen in plaats van
  // 1706 - en dat is een sprong van een kwart bij de naad, elke ronde hoorbaar.
  // Als faseverschuiving kán hij niet weglopen: hij komt terug waar hij begon.
  var TRILLER_PER_LUS = 6;
  var TRILLER_DIEPTE = 0.6;

  var GEUL_LAAG = 0.05;   // vijf procent open water, net als bij S
  var GEUL_HOOG = 0.115;
  var POMP_KLEIN = 0.055;
  var POMP_GROOT = 0.095;
  var RONDJE = 18;

  var VORM_STERKTE = 0.42;

  // De ruis is een DERDE van de vorm en niet er even hard bovenop. Harder ziet
  // er indrukwekkender uit, maar dan is de figuur er niet meer, en dan leest de
  // stekker als een omschakeling naar iets anders in plaats van als schoonmaken.
  // De zaal moet het beeld door de ruis heen zien staan - net zoals je de muziek
  // door het gebrom van een vliegtuig heen hoort.
  var RUIS_STERKTE = 0.14;

  // En hij is LAAGDOORLATEND, en dat is de eigenlijke oorzaak van het probleem
  // hierboven. Witte ruis springt elke sample naar een nieuwe plek, dus de pen
  // teleporteert en de lijnen ertussen kruisen het hele vlak - dat is waarom het
  // een dichte wolk werd in plaats van een vuile lijn. Gefilterde ruis verandert
  // langzaam, dus de pen dwaalt om het echte spoor heen en de figuur blijft
  // staan, alleen rafelig.
  //
  // Het klopt bovendien beter. Een koptelefoon haalt juist het lage gebrom weg
  // en niet de tik ernaast, en zo is het hier nu ook: de ruis zit onder de
  // tweeënhalve kilohertz en de tik erboven.
  var RUIS_KANTEL = 2500;

  // En de DRIFT, die eronder ligt: een paar trillingen ver beneden het gehoor,
  // zodat de hele figuur langzaam over het scherm zwerft. Zo staat een scoop die
  // niet op zijn signaal aangehaakt is, en dat is precies het gevoel dat deze
  // beat nodig heeft - er staat iets, het is niet scherp, én het blijft niet
  // liggen. Hij zit IN de ruis, dus met de stekker erin valt hij mee weg en komt
  // de plaat stil te liggen.
  var DRIFT_TOV_RUIS = 1.1;
  var DRIFT_TONEN = [0.125, 0.25, 0.375];  // hele delers van de ruislus
  var RUIS_LUS = 8;

  // Het pad bij één stand van de watergang en één stand van het gemaal, als één
  // gesloten lijn - want een scoop tilt zijn pen niet op. De route loopt de
  // silhouetten en de ribben van de plaat af, doet onderweg het gemaal aan, en
  // sluit af met de watergang. Wat dubbel gelopen wordt valt samen met wat er al
  // staat, op de radiale streepje naar het gemaal na - en dat leest als de stip
  // die het gemaal bij ⟳ ook is.
  function padNu(geul, pomp) {
    var i;
    var A = plek(0, 0), B = plek(1, 0), C = plek(1, 1), D = plek(0, 1);
    var Bz = plek(1, 0, 1), Cz = plek(1, 1, 1), Dz = plek(0, 1, 1);
    var g = plek(1, 0.5);
    var w1 = plek(0, 0.5 - geul), w2 = plek(1, 0.5 - geul);
    var w3 = plek(1, 0.5 + geul), w4 = plek(0, 0.5 + geul);

    var p = [A, B, Bz, Cz, C, g];
    for (var k = 1; k <= RONDJE; k++) {
      var h = 2 * Math.PI * k / RONDJE;
      p.push(plek(1 + pomp * Math.cos(h), 0.5 + pomp * Math.sin(h)));
    }
    p.push(g, B, C, D, Dz, Cz, Dz, D, w4, w1, w2, w3, w4, w1, A);

    // De booglengtes horen bij het pad en niet bij de sample: ze één keer per
    // herbouw uitrekenen scheelt dertig miljoen worteltrekkingen bij het laden.
    var lengte = [], totaal = 0;
    for (i = 0; i < p.length - 1; i++) {
      var dx = p[i + 1][0] - p[i][0], dy = p[i + 1][1] - p[i][1];
      lengte.push(Math.sqrt(dx * dx + dy * dy));
      totaal += lengte[i];
    }
    return { punt: p, lengte: lengte, totaal: totaal };
  }

  // Welke stukken de watergang zijn - daar en nergens anders hoort de rimpel.
  var GEUL_HEEN = 15 + RONDJE, GEUL_TERUG = 17 + RONDJE;

  // Op booglengte lopen en niet op parameter: anders wordt een lang stuk sneller
  // getekend dan een kort, en op een scoop is sneller hetzelfde als flauwer.
  // Geeft x, y en het nummer van het stuk.
  var _uit = [0, 0, 0];

  function langs(pad, u) {
    var lengte = pad.lengte, punten = pad.punt;
    var s = u * pad.totaal, gelopen = 0, seg = 0;
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
    var grond = 0, piek = 0, punten = padNu(GEUL_LAAG, POMP_KLEIN);
    for (var i = 0; i < n; i++) {
      var t = i / sr;
      grond = (grond + AKKOORD[Math.floor(t / MAAT) % AKKOORD.length] / sr) % 1;
      var fase = (grond + TRILLER_DIEPTE *
                  Math.sin(2 * Math.PI * TRILLER_PER_LUS * t / DUUR) + 4) % 1;

      var tb = t % TEL;
      // De aanslag moet een HELLING zijn en geen sprong. Springt hij, dan staat
      // er twee keer per seconde een knik in de golf - dat tikt hoorbaar, en het
      // beeld verspringt zichtbaar. Zes milliseconde omhoog is te kort om als
      // aanzet te horen en lang genoeg om de knik weg te halen. Diezelfde
      // helling maakt ook de naad van de lus glad, want daar valt de tel
      // precies op nul.
      var slag = Math.min(1, tb / 0.006) * Math.exp(-tb / 0.085);

      // Eén golf per lus, met een vlakke raaklijn aan beide kanten van de naad:
      // het water komt op en zakt terug zonder dat je hoort waar de lus rond is.
      var op = (1 - Math.cos(2 * Math.PI * 2 * t / DUUR)) / 2;

      // De vorm hoeft niet elke sample opnieuw uitgemeten te worden - geul en
      // pomp veranderen traag, en om de tweeëndertig samples is ruim binnen wat
      // te zien is.
      if (i % 32 === 0) {
        punten = padNu(GEUL_LAAG + (GEUL_HOOG - GEUL_LAAG) * op,
                       POMP_KLEIN + (POMP_GROOT - POMP_KLEIN) * slag);
      }

      var p = langs(punten, fase);
      var x = p[0], y = p[1];

      // De rimpel staat alleen op de WATERGANG, en hij groeit mee met de stand.
      // Voor het oog is het beweging op het water; voor het oor een boventoon die
      // met het peil mee opkomt.
      //
      // Dat de geul heen én terug gelopen wordt is hier geen verspilling: de
      // rimpel staat op de terugweg een stuk verder in zijn periode, dus de twee
      // passages vallen niet samen. Er staat daardoor geen lijn maar een BAND -
      // water met een oppervlak. Omdat de rimpel een hele boventoon is, is dat
      // patroon elke omloop hetzelfde en staat de band stil.
      if (p[2] === GEUL_HEEN || p[2] === GEUL_TERUG) {
        y += 0.012 * op * Math.sin(2 * Math.PI * 9 * fase);
      }

      // De plaat zelf ademt nog een klein beetje mee, maar het meeste van de maat
      // zit nu in het gemaal hierboven.
      var env = 0.96 + 0.04 * slag;
      L[i] = x * VORM_STERKTE * env;
      R[i] = y * VORM_STERKTE * env;
      piek = Math.max(piek, Math.abs(L[i]), Math.abs(R[i]));
    }
    STUK = { sr: sr, L: L, R: R, n: n, piek: piek };
    return STUK;
  }

  // Een paar trillingen ver onder het gehoor, opgeteld en teruggeschaald op de
  // theoretische piek. Ze zijn hele delers van de ruislus, dus ze lopen precies
  // rond en er komt geen tik bij de naad.
  function drift(t, fasen) {
    var som = 0;
    for (var i = 0; i < DRIFT_TONEN.length; i++) {
      som += Math.sin(2 * Math.PI * DRIFT_TONEN[i] * t + fasen[i]);
    }
    return som / DRIFT_TONEN.length;
  }

  // ═════════════════════════════════════════════════════════════════════════
  // De omgeving
  // ═════════════════════════════════════════════════════════════════════════
  //
  // Onder de eerste drie beats staat een beek met vogels. Die is NIET in beeld,
  // en dat kan ook niet: een scoop tekent wat hij hoort, en stromend water is
  // breedbandige ruis - als je dat laat meetekenen krijg je precies de kluwen
  // waar deze beat vanaf moest. Een staand beeld is een periodieke golf, en een
  // periodieke golf is een toon. Dat is geen keuze maar meetkunde.
  //
  // Daarom hangt deze laag rechtstreeks aan het volume en niet aan de mengknoop
  // waar de scoop naar kijkt. Hij staat alleen aan bij `achter`, en daar staat
  // er geen oscilloscoop op het scherm - er valt dus niets te beweren wat niet
  // klopt. Zodra de scoop verschijnt, is hij weg.
  var BEEK_LAAG = 380, BEEK_HOOG = 4200;
  var VOGELS = [
    // start, duur, grondtoon, uitslag, triller, links/rechts
    [1.9, 0.20, 2700, 1500, 26, 0.7], [2.35, 0.14, 2900, 1100, 30, 0.8],
    [5.1, 0.26, 2300, 1900, 18, 0.3], [7.4, 0.16, 3300, 900, 34, 0.9],
    [7.7, 0.16, 3350, 950, 34, 0.85], [8.0, 0.22, 3200, 1200, 30, 0.8],
    [11.2, 0.30, 2100, 2100, 15, 0.4], [12.6, 0.13, 3600, 800, 38, 0.6],
    [14.1, 0.19, 2600, 1400, 24, 0.5]
  ];

  // Een roep: de toonhoogte gaat omhoog en weer omlaag met een snelle triller
  // erop, en de omhullende is een halve sinus in het kwadraat - zacht in, zacht
  // uit, want een harde aanzet klinkt als een piep en niet als een vogel.
  function roep(links, rechts, sr, start, duur, f0, uitslag, triller, balans) {
    var n = Math.floor(sr * duur), begin = Math.floor(sr * start), fase = 0;
    for (var i = 0; i < n; i++) {
      var u = i / n;
      var omh = Math.sin(Math.PI * u);
      omh *= omh;
      var f = f0 + uitslag * Math.sin(Math.PI * u) +
              120 * Math.sin(2 * Math.PI * triller * u * duur);
      fase += f / sr;
      var w = 0.16 * omh * Math.sin(2 * Math.PI * fase);
      links[(begin + i) % links.length] += w * balans;
      rechts[(begin + i) % rechts.length] += w * (1.3 - balans);
    }
  }

  function omgevingBuffer(ctx) {
    var sr = ctx.sampleRate, n = Math.round(sr * DUUR);
    // Er wordt LANGER gerekend dan de buffer lang is, en die staart gaat in de
    // kop. Alleen overvloeien zonder afknippen helpt niet: dan speelt de staart
    // nog steeds af en springt hij daarna naar een kop die ergens anders begint.
    // Gemeten was dat een sprong van 1,74 - elke ronde een klap.
    var over = Math.floor(sr * 0.4), n2 = n + over;
    var ruw = [new Float32Array(n2), new Float32Array(n2)];
    var aH = 1 - Math.exp(-2 * Math.PI * BEEK_HOOG / sr);
    var aL = 1 - Math.exp(-2 * Math.PI * BEEK_LAAG / sr);
    for (var k = 0; k < 2; k++) {
      var kan = ruw[k], hoog = 0, laag = 0;
      var fase1 = Math.random() * 6.283, fase2 = Math.random() * 6.283;
      for (var i = 0; i < n2; i++) {
        var wit = Math.random() * 2 - 1;
        hoog += aH * (wit - hoog);
        laag += aL * (wit - laag);
        // Het verschil van twee laagdoorlaters is een band, en die band is wat
        // stromend water is. De trage golving eroverheen maakt het klateren:
        // zonder die beweging is het gewoon gesis.
        var golving = 0.62 + 0.38 * Math.sin(2 * Math.PI * 0.23 * i / sr + fase1)
                                * Math.sin(2 * Math.PI * 0.41 * i / sr + fase2);
        kan[i] = (hoog - laag) * 2.6 * golving;
      }
    }
    VOGELS.forEach(function (v) {
      roep(ruw[0], ruw[1], sr, v[0], v[1], v[2], v[3], v[4], v[5]);
    });

    var b = ctx.createBuffer(2, n, sr);
    for (k = 0; k < 2; k++) {
      var uit = b.getChannelData(k), in_ = ruw[k];
      for (i = 0; i < n; i++) uit[i] = in_[i];
      for (var j = 0; j < over; j++) {
        var m = j / over;
        uit[j] = in_[j] * m + in_[n + j] * (1 - m);
      }
    }
    return b;
  }

  // Eenpolig laagdoorlatend filter: y += a * (x - y). Bij deze kantelfrequentie
  // verandert de ruis ongeveer elke twintig samples, en dat is ruim binnen één
  // omloop van de vorm - dus wordt het spoor rafelig in plaats van uitgewist.
  function kantelFactor(sr) {
    return 1 - Math.exp(-2 * Math.PI * RUIS_KANTEL / sr);
  }

  var ctx = null, mix = null, master = null, ruisBron = null, zacht = null;
  var ruisTak = null, tegenTak = null, links = null, rechts = null;
  var beekTak = null, stemTak = null;
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

    // En hiertussen staat een zachte laagdoorlater. Een gesloten figuur van
    // rechte stukken met scherpe hoeken is een golf met veel boventonen, en dat
    // klinkt als een zaag - dat was de brom. De hoeken eraf halen zou de plaat
    // afronden, dus gebeurt het NA de mengknoop: de scoop ziet het scherpe
    // signaal, de speaker krijgt de zachte versie. Dat is precies wat de
    // verticale versterker van een scoop en een luidspreker sowieso al met
    // elkaar verschillen.
    zacht = ctx.createBiquadFilter();
    zacht.type = "lowpass";
    zacht.frequency.value = 1400;
    zacht.Q.value = 0.6;
    mix.connect(zacht).connect(master);

    var s = stukVoor(ctx.sampleRate);
    var sb = ctx.createBuffer(2, s.n, ctx.sampleRate);
    sb.getChannelData(0).set(s.L);
    sb.getChannelData(1).set(s.R);
    // De getekende stem heeft zijn eigen kraan, en die staat dicht zolang er geen
    // scoop op het scherm staat. Deze toon is namelijk niet zomaar muziek: hij
    // ís de figuur. Hem laten klinken terwijl er niets te zien is, belooft iets
    // wat er nog niet is - en dat is precies de brom die je dan hoort.
    var stem = ctx.createBufferSource();
    stem.buffer = sb;
    stem.loop = true;
    stemTak = ctx.createGain();
    stemTak.gain.value = 0;
    stem.connect(stemTak).connect(mix);

    // Twee seconden ruis, en de twee kanalen los van elkaar: dan spat het beeld
    // in twee richtingen uiteen in plaats van dat het over één lijn trilt.
    // Acht seconden lang, en niet twee: de drift eronder telt in tienden van een
    // trilling per seconde, en die moeten heel in de lus passen of hij tikt.
    var m = Math.floor(ctx.sampleRate * RUIS_LUS);
    var rb = ctx.createBuffer(2, m, ctx.sampleRate);
    var a = kantelFactor(ctx.sampleRate);
    for (var k = 0; k < 2; k++) {
      var kanaal = rb.getChannelData(k);
      var vorig = 0, kwad = 0;
      for (var j = 0; j < m; j++) {
        vorig += a * (Math.random() * 2 - 1 - vorig);
        kanaal[j] = vorig;
        kwad += vorig * vorig;
      }
      // Filteren haalt energie weg, dus terugschalen - op drie keer de effectieve
      // waarde, want normaliseren op de piek zou de hele ruis laten meebewegen
      // met één uitschieter.
      var schaal = 1 / (3 * Math.sqrt(kwad / m));
      // Elk kanaal krijgt zijn eigen faseverdraaiing, anders zwerft de figuur
      // over één schuine lijn heen en weer in plaats van over het vlak.
      var fasen = DRIFT_TONEN.map(function () { return Math.random() * 2 * Math.PI; });
      for (j = 0; j < m; j++) {
        kanaal[j] = kanaal[j] * schaal + DRIFT_TOV_RUIS * drift(j / ctx.sampleRate, fasen);
      }
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

    // De beek hangt aan het volume en niet aan de mengknoop: hij mag klinken,
    // hij mag niet meetekenen.
    var beek = ctx.createBufferSource();
    beek.buffer = omgevingBuffer(ctx);
    beek.loop = true;
    beekTak = ctx.createGain();
    beekTak.gain.value = 0;
    beek.connect(beekTak).connect(master);
    beek.start();

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
  var TIK_X = 0.28, TIK_Y = 0.24, TIK_DUUR = 0.008, TIK_ELKE = 1.6;

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
  var ruisX = 0, ruisY = 0;
  var driftFasen = [
    DRIFT_TONEN.map(function () { return Math.random() * 2 * Math.PI; }),
    DRIFT_TONEN.map(function () { return Math.random() * 2 * Math.PI; })
  ];

  function zelfRekenen() {
    var s = stukVoor(48000);
    var ruis = stand === "ruis" || stand === "achter" ? RUIS_STERKTE : 0;
    // Hetzelfde filter als in de buffer hierboven, anders ziet het rekenpad er
    // anders uit dan het geluidspad klinkt.
    var a = kantelFactor(s.sr);
    // De tik hoort ook hier thuis: zonder geluid zou de beat over de grens van
    // de analogie een leeg scherm zijn, en juist die moet iets laten zien.
    var tikt = stand === "tik" && (kop / s.sr) % TIK_ELKE < 1 / 60;
    for (var i = 0; i < bufX.length; i++) {
      var j = (kop + i) % s.n;
      ruisX += a * (Math.random() * 2 - 1 - ruisX);
      ruisY += a * (Math.random() * 2 - 1 - ruisY);
      var kt = (kop + i) / s.sr;
      bufX[i] = s.L[j] + (ruisX * 3.2 + DRIFT_TOV_RUIS * drift(kt, driftFasen[0])) * ruis;
      bufY[i] = s.R[j] + (ruisY * 3.2 + DRIFT_TOV_RUIS * drift(kt, driftFasen[1])) * ruis;
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

    // De straal is zo gekozen dat alles NET binnen het scherm blijft: de figuur
    // (0,91 bij 0,59), de ruis eromheen (0,33) en de drift eronder (0,37). Wat
    // eraf loopt zou als een rechte rand lezen die er niet is.
    var mx = b / 2, my = h / 2, r = Math.min(b * 0.30, h * 0.38);
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
    master.gain.setTargetAtTime(stand === "achter" ? 0.30 : 0.5, ctx.currentTime, 0.08);
    // De beek staat alleen onder de beats waar geen scoop op het scherm staat.
    // Zodra hij verschijnt, moet alles wat je hoort er ook op staan - en dan
    // wisselen ze: de beek gaat weg en de stem komt op, samen met het beeld.
    beekTak.gain.setTargetAtTime(stand === "achter" ? 0.85 : 0, ctx.currentTime, 0.35);
    // De stem komt SNELLER op dan de beek weggaat. Met dezelfde tijdconstante
    // groeit de figuur een seconde lang op uit het niets, en dat leest als een
    // haperende plaat in plaats van als een instrument dat aangaat.
    stemTak.gain.setTargetAtTime(stand === "achter" ? 0 : 1, ctx.currentTime, 0.10);
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

  // De twee bouwers staan hier zodat ze buiten een browser na te rekenen zijn -
  // de naad van de lus, de piek en de grootste stap tussen twee samples.
  return { blok: blok, zet: zet, wek: wek, _stuk: stukVoor, _omgeving: omgevingBuffer };
})();

if (typeof module !== "undefined") module.exports = OSCILLOSCOOP;
