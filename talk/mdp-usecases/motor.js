// ═══════════════════════════════════════════════════════════════════════════
// De machinerie. Geen inhoud — die staat in inhoud.js, en de getallen in
// transcript.js.
// ═══════════════════════════════════════════════════════════════════════════
//
// Geen framework, geen import, geen netwerk. Klassieke scripts, dus dit werkt
// ook als je index.html dubbelklikt en ook als de zaal geen wifi heeft.
//
// De hele toestand is één getal: welke beat staat er. Alles op het scherm is
// een functie van dat getal, dus terug kunnen is gratis en er bestaat geen
// stand die je alleen met de muis kunt bereiken.

(function () {
  "use strict";

  // ── de beats uitrollen tot één platte lijst ──────────────────────────────
  var BEATS = [{ stap: null, beat: INHOUD.titel, index: 0, van: 1 }];
  INHOUD.stappen.forEach(function (stap) {
    stap.beats.forEach(function (beat, i) {
      BEATS.push({ stap: stap, beat: beat, index: i, van: stap.beats.length });
    });
  });

  var nu = 0;
  var app = document.getElementById("app");

  function el(tag, klasse, tekst) {
    var e = document.createElement(tag);
    if (klasse) e.className = klasse;
    if (tekst !== undefined && tekst !== null) {
      var s = String(tekst);
      // Een veldnaam staat in de data tussen backticks. Die leestekens horen niet op een
      // scherm en een schreefloze naam is niet als naam te zien, dus krijgt hij kleur en
      // gewicht in plaats van tekens eromheen.
      if (s.indexOf("`") !== -1) {
        s.split("`").forEach(function (deel, i) {
          if (!deel) return;
          if (i % 2) e.appendChild(el("span", "veldnaam", deel));
          else e.appendChild(document.createTextNode(deel));
        });
      } else {
        e.textContent = s;
      }
    }
    return e;
  }

  function komma(x) {
    return String(x).replace(".", ",");
  }

  // ── de kop: de keten, en waar je bent ────────────────────────────────────
  function kop(huidig) {
    var k = el("header", "kop");
    INHOUD.stappen.forEach(function (stap, i) {
      if (i) k.appendChild(el("span", "kop-pijl", "⇒"));
      var s = el("button", "kop-lid" + (stap === huidig ? " hier" : ""), stap.naam);
      s.onclick = function (ev) { ev.stopPropagation(); naarStap(i); };
      k.appendChild(s);
    });
    return k;
  }

  // ── de platen ────────────────────────────────────────────────────────────
  function rijenTabel(rijen, klasse) {
    var t = el("div", "rijen " + (klasse || ""));
    (rijen || []).forEach(function (r) {
      var rij = el("div", "rij" + (r.nadruk ? " nadruk" : "") + (r.breed ? " breed" : ""));
      rij.appendChild(el("span", "rij-l", r.l));
      rij.appendChild(el("span", "rij-r", r.r));
      t.appendChild(rij);
    });
    return t;
  }

  // ── de knopenlijst als tekening ───────────────────────────────────────────
  // Kolom en rij bepalen de plek, `pijlen` volgt de `drains_to`-verwijzingen uit de
  // payload eronder. Handgeschreven SVG en geen bibliotheek: dit is één rechthoek per
  // knoop en één lijn per verwijzing, en dat hoort geen afhankelijkheid te kosten.
  var KOL = 226, RIJ = 62, BREED = 198, HOOG = 40;
  // Compact: alleen het oppervlak en de capaciteit onder de naam. Het vak is breed genoeg
  // voor een naam als "De Tol 2014 plus gebiedsvreemd water", want die naam IS de intentie
  // van de aanroep - hem inkorten haalt het onderwerp uit de tekening.
  var K_KOL = 226, K_BREED = 198, K_MAX_EM = 7.4;
  // Een aanroep met veel losse knopen krijgt smallere vakken: anders moet de hele
  // tekening krimpen om naast de uitkomst te passen, en dan zijn de namen niet meer te
  // lezen. Smal kan daar, want die namen zijn kort.
  var S_KOL = 172, S_BREED = 150;
  // De maatvoering ín een vak: waar de eerste regel staat, hoe hoog een regel is, en wat
  // eronder vrij blijft. De hoogte van het vak volgt uit het aantal regels, dus deze maten
  // en de fontgroottes in `stijl.css` horen bij elkaar.
  var MAAT = {
    compact: { rand: 19, label: 17, tussen: 14, maat: 14, onder: 7, tussenrij: 12 },
    ruim: { rand: 17, label: 15, tussen: 14, maat: 13, onder: 9, tussenrij: 22 }
  };

  function svgEl(naam, kenmerken) {
    var e = document.createElementNS("http://www.w3.org/2000/svg", naam);
    Object.keys(kenmerken || {}).forEach(function (k) { e.setAttribute(k, kenmerken[k]); });
    return e;
  }

  // ── tekst opmeten en afbreken ─────────────────────────────────────────────
  // SVG-tekst breekt niet af en kapt niet af: wat te lang is loopt gewoon over de rand
  // van zijn vak heen. Dus wordt hij hier eerst opgemeten in een verborgen tekening met
  // dezelfde klassen, en daarna over regels verdeeld. Letters tellen is geen alternatief:
  // "1.248,5 ha · 1,879 m³/s" en "De Tol · legger van nu" zijn even lang en meten anders.
  var MEETLAT = {};
  function meetTekst(tekst, klasse, compact) {
    var sleutel = compact ? "compact" : "ruim";
    if (!MEETLAT[sleutel]) {
      var lat = svgEl("svg", { class: "knopendiagram" + (compact ? " compact" : ""), "aria-hidden": "true" });
      lat.style.cssText = "position:absolute;left:-9999px;top:0;width:20px;height:20px;visibility:hidden";
      document.body.appendChild(lat);
      MEETLAT[sleutel] = lat;
    }
    var lat = MEETLAT[sleutel];
    var t = svgEl("text", { class: klasse });
    t.textContent = tekst;
    lat.appendChild(t);
    var breed = t.getComputedTextLength();
    lat.removeChild(t);
    return breed;
  }

  // Woord voor woord, en een woord dat zelf niet past blijft staan - dat wordt bij het
  // tekenen samengeperst in plaats van afgekapt, want een halve eenheid is erger dan
  // een smalle letter.
  function afbreken(tekst, klasse, ruimte, compact) {
    if (!tekst) return [];
    if (meetTekst(tekst, klasse, compact) <= ruimte) return [tekst];
    var regels = [], huidig = "";
    tekst.split(" ").forEach(function (woord) {
      var kandidaat = huidig ? huidig + " " + woord : woord;
      if (huidig && meetTekst(kandidaat, klasse, compact) > ruimte) { regels.push(huidig); huidig = woord; }
      else huidig = kandidaat;
    });
    if (huidig) regels.push(huidig);
    // Twee regels worden in balans gebracht: gulzig afbreken laat "plangebied met 18 mm per"
    // met "dag" eronder achter, en zo'n weduwe leest als een fout in de tekening.
    if (regels.length === 2) {
      var woorden = tekst.split(" "), beste = null;
      for (var i = 1; i < woorden.length; i++) {
        var a = woorden.slice(0, i).join(" "), b = woorden.slice(i).join(" ");
        var wa = meetTekst(a, klasse, compact), wb = meetTekst(b, klasse, compact);
        if (wa > ruimte || wb > ruimte) continue;
        var breedst = Math.max(wa, wb);
        if (!beste || breedst < beste.breedst) beste = { breedst: breedst, regels: [a, b] };
      }
      if (beste) return beste.regels;
    }
    return regels;
  }

  // Eén regel tekst, samengeperst als het één woord is dat niet past.
  function regel(tekst, klasse, x, y, ruimte, compact) {
    var t = svgEl("text", { class: klasse, x: x, y: y });
    t.textContent = tekst;
    if (meetTekst(tekst, klasse, compact) > ruimte) {
      t.setAttribute("textLength", ruimte.toFixed(1));
      t.setAttribute("lengthAdjust", "spacingAndGlyphs");
    }
    return t;
  }

  function diagram(spec, compact) {
    // Een aanroep mag zijn eigen vakmaat vragen: smal als er veel losse knopen naast
    // elkaar staan, ruim als één naam anders over twee regels moet en het vak daardoor
    // tegen het hoogteplafond loopt.
    var breed = compact ? (spec.breed || (spec.smal ? S_BREED : K_BREED)) : BREED;
    var kol = compact ? breed + 28 : KOL;
    var pad = compact ? 9 : 10, ruimte = breed - 2 * pad;
    // Eerst alle tekst afbreken, dan de hoogte: elk vak in één tekening wordt even hoog,
    // ook als maar één naam over twee regels moet. Ongelijke vakken lezen als betekenis.
    var tekst = {};
    var maxLabel = 1, maxMaat = 1;
    spec.knopen.forEach(function (k) {
      var onder = compact ? k.maat : k.ha;
      tekst[k.id] = {
        label: afbreken(k.label, "knoop-label", ruimte, compact),
        maat: afbreken(onder, "knoop-maat", ruimte, compact)
      };
      maxLabel = Math.max(maxLabel, tekst[k.id].label.length);
      maxMaat = Math.max(maxMaat, tekst[k.id].maat.length);
    });
    var mt = compact ? MAAT.compact : MAAT.ruim;
    var hoog = mt.rand + (maxLabel - 1) * mt.label + mt.tussen + (maxMaat - 1) * mt.maat + mt.onder;
    var rij = hoog + mt.tussenrij;
    var kolommen = Math.max.apply(null, spec.knopen.map(function (k) { return k.kol; })) + 1;
    var rijen = Math.max.apply(null, spec.knopen.map(function (k) { return k.rij; })) + 1;
    var extra = spec.uit ? kol : 12;
    var breedte = kolommen * kol + extra;
    var hoogte = rijen * rij + 8;
    // Breedte en hoogte in px erbij, want zonder die twee schaalt de browser elke
    // tekening naar zijn eigen cel: een kolom van zeven krimpt dan tot onleesbaar en
    // een enkele knoop blaast op. Met de eigen maat erin staan ze alle zes op
    // dezelfde schaal, en verschilt alleen de hoogte van de cel.
    var svg = svgEl("svg", {
      class: "knopendiagram" + (compact ? " compact" : ""),
      viewBox: "0 0 " + breedte + " " + hoogte,
      preserveAspectRatio: "xMinYMid meet"
    });
    // De maat in em en niet in px: dan groeien de labels ín de tekening mee met de
    // typemaat van de deck, en blijft een knoop op een beamer leesbaar. Zonder dit
    // staan er 13 px letters op een scherm van vier meter.
    var emBreed = breedte / 15, emHoog = hoogte / 15;
    // En een plafond op de hoogte, want twee tekeningen op één plaat moeten samen met
    // hun koppen tussen de stapkop en de bronregel passen - ook op een 4:3-beamer. De
    // BREEDTE krimpt mee, anders staat de tekening in een leeg vak.
    if (compact && emHoog > K_MAX_EM) emBreed *= K_MAX_EM / emHoog;
    svg.style.width = emBreed.toFixed(2) + "em";

    var punt = {};
    spec.knopen.forEach(function (k) {
      punt[k.id] = { x: k.kol * kol, y: k.rij * rij + 4, k: k };
    });
    function rechts(p) { return { x: p.x + breed, y: p.y + hoog / 2 }; }
    function links(p) { return { x: p.x, y: p.y + hoog / 2 }; }

    // eerst de lijnen, zodat de vakken erover heen liggen
    (spec.pijlen || []).forEach(function (pr) {
      var a = rechts(punt[pr[0]]), b = links(punt[pr[1]]);
      var mid = (a.x + b.x) / 2;
      svg.appendChild(svgEl("path", {
        class: "pijl",
        d: "M" + a.x + " " + a.y + " C" + mid + " " + a.y + " " + mid + " " + b.y + " " + (b.x - 9) + " " + b.y
      }));
      svg.appendChild(svgEl("path", {
        class: "punt",
        d: "M" + (b.x - 9) + " " + (b.y - 4) + " L" + b.x + " " + b.y + " L" + (b.x - 9) + " " + (b.y + 4) + " Z"
      }));
    });
    if (spec.uit) {
      var a = rechts(punt[spec.uit.van]);
      svg.appendChild(svgEl("path", { class: "pijl uit", d: "M" + a.x + " " + a.y + " h" + (kol - 60) }));
      var label = svgEl("text", { class: "uit-label", x: a.x + 12, y: a.y - 8 });
      label.textContent = spec.uit.label;
      svg.appendChild(label);
    }

    spec.knopen.forEach(function (k) {
      var p = punt[k.id];
      var g = svgEl("g", { class: "knoop" + (k.zelfde ? " zelfde" : "") + (k.los ? " los" : "") });
      g.appendChild(svgEl("rect", { x: p.x, y: p.y, width: breed, height: hoog, rx: 2 }));
      var y = p.y + mt.rand;
      tekst[k.id].label.forEach(function (r, i) {
        if (i) y += mt.label;
        g.appendChild(regel(r, "knoop-label", p.x + pad, y, ruimte, compact));
      });
      y += mt.tussen;
      tekst[k.id].maat.forEach(function (r, i) {
        if (i) y += mt.maat;
        g.appendChild(regel(r, "knoop-maat", p.x + pad, y, ruimte, compact));
      });
      svg.appendChild(g);
    });
    return svg;
  }

  // ── de drie schakels van de hypothese ─────────────────────────────────────
  // Eén functie, twee platen: bij de vraag staat hij kaal en bij de conclusie met een
  // oordeel erop. Dat de vorm gelijk is, is het punt - dan is het antwoord zichtbaar
  // dezelfde keten als de belofte.
  function schakelketen(schakels) {
    var keten = el("div", "hypo-keten");
    schakels.forEach(function (s, i) {
      if (i) keten.appendChild(el("span", "keten-pijl", "→"));
      var k = el("div", "hypo-schakel" + (s.splits ? " gesplitst" : "") +
                       (s.teken ? " oordeel " + s.teken : ""));
      if (s.teken) {
        k.appendChild(el("span", "hypo-teken", s.teken === "ja" ? "✓" : "~"));
      }
      k.appendChild(el("span", "hypo-schakel-l", s.l));
      if (s.maat) k.appendChild(el("span", "hypo-maat", s.maat));
      if (s.regel) k.appendChild(el("span", "hypo-regel", s.regel));
      if (s.splits) {
        var vork = el("div", "hypo-vork");
        s.splits.forEach(function (tak, j) {
          if (j) vork.appendChild(el("span", "hypo-of", "of"));
          vork.appendChild(el("span", "hypo-tak", tak));
        });
        k.appendChild(vork);
      }
      keten.appendChild(k);
    });
    return keten;
  }

  var PLAAT = {
    // ── de eerste beat van elke casus: gebied links, vraag rechts ─────────
    // Alle drie de casussen krijgen deze plaat, met hun eigen kaart. Dezelfde vorm
    // maakt van het verschil tussen de gebieden een inhoudelijk verschil.
    casus: function (beat) {
      var w = el("div", "casus");
      var links = el("div", "casus-kaart");
      var img = el("img");
      img.src = beat.kaart;
      img.alt = "de peilvakken van dit gebied uit de legger van het waterschap";
      links.appendChild(img);
      w.appendChild(links);
      var rechts = el("div", "casus-tekst");
      rechts.appendChild(el("div", "casus-plaats", beat.plaats));
      rechts.appendChild(rijenTabel(beat.context));
      var v = el("div", "casus-vraag");
      v.appendChild(el("span", "casus-vraag-kop", "de vraag"));
      v.appendChild(el("p", null, beat.vraag));
      rechts.appendChild(v);
      w.appendChild(rechts);
      return w;
    },

    // ── de tweede beat: ons antwoord, en waar het uit kwam ────────────────
    antwoord: function (beat) {
      var w = el("div", "antwoord");
      w.appendChild(rijenTabel(beat.rijen, "groot"));
      return w;
    },

    lijst: function (beat) {
      return rijenTabel(beat.rijen, "lijst");
    },

    // ── de derde beat: ons antwoord tegenover het rapport ─────────────────
    vergelijk: function (beat) {
      var w = el("div", "vergelijk");
      [beat.links, beat.rechts].forEach(function (kolom, i) {
        var k = el("div", "kolom" + (i ? " tweede" : ""));
        k.appendChild(el("div", "kolom-kop", kolom.kop));
        k.appendChild(rijenTabel(kolom.rijen));
        w.appendChild(k);
      });
      return w;
    },

    // ── de limitaties, gegroepeerd, met de casus erachter ─────────────────
    limitaties: function (beat) {
      var w = el("div", "limitaties");
      var vorige = null;
      beat.rijen.forEach(function (r) {
        if (r.groep !== vorige) {
          w.appendChild(el("div", "limitatie-groep", r.groep));
          vorige = r.groep;
        }
        var rij = el("div", "limitatie-rij" + (r.hard ? " hard" : ""));
        rij.appendChild(el("span", "limitatie-wat", r.wat));
        rij.appendChild(el("span", "limitatie-waar", r.waar));
        w.appendChild(rij);
      });
      return w;
    },

    // ── de tabel uit STOWA 2018-68, met onze eigen stand ernaast ──────────
    licentie: function (beat) {
      var w = el("div", "licentie");
      beat.rijen.forEach(function (r) {
        var rij = el("div", "licentie-rij " + (r.goed ? "goed" : "gat"));
        rij.appendChild(el("span", "licentie-functie", r.functie));
        rij.appendChild(el("span", "licentie-oordeel", r.oordeel));
        rij.appendChild(el("span", "licentie-wij", r.wij));
        w.appendChild(rij);
      });
      w.appendChild(el("div", "licentie-bovenal", beat.bovenal));
      return w;
    },

    // ── de volgorde van de aanroepen, per casus ───────────────────────────
    volgorde: function (beat) {
      var w = el("div", "volgorde");
      beat.per_casus.forEach(function (c) {
        var groep = el("div", "volgorde-groep");
        var kop = el("div", "volgorde-kop");
        kop.appendChild(el("span", "volgorde-casus", c.casus));
        kop.appendChild(el("span", "volgorde-n", c.mcp + " calls · " + c.mcp_blok_s + " s"));
        groep.appendChild(kop);
        var keten = el("div", "keten");
        c.volgorde.forEach(function (tool, i) {
          if (i) keten.appendChild(el("span", "keten-pijl", "→"));
          var soort = tool === "read_me" ? "handleiding"
            : tool.indexOf("cascade") === 0 ? "netwerk"
            : tool.indexOf("find_package") === 0 ? "pakket" : "maatregel";
          keten.appendChild(el("span", "keten-lid " + soort, tool));
        });
        groep.appendChild(keten);
        groep.appendChild(el("div", "volgorde-lezing", c.lezing));
        w.appendChild(groep);
      });
      var legenda = el("div", "legenda");
      ["handleiding", "maatregel", "pakket", "netwerk"].forEach(function (s) {
        legenda.appendChild(el("span", "sleutel k-" + s, s));
      });
      w.appendChild(legenda);
      return w;
    },

    // ── gebruikt tegenover ongebruikt ─────────────────────────────────────
    tools: function (beat) {
      var w = el("div", "tools");
      var links = el("div", "tools-kolom");
      links.appendChild(el("div", "kolom-kop", "aangeroepen"));
      // De meest aangeroepen tool is het NETWERK, en dat is de verrassing: de vraag
      // was drie keer een enkel gebied. Die regel krijgt daarom nadruk.
      beat.gebruikt.forEach(function (g, i) {
        var r = el("div", "tool-rij" + (i === 0 ? " top" : ""));
        r.appendChild(el("span", "tool-n", g.n + "×"));
        r.appendChild(el("span", "tool-naam", g.tool));
        links.appendChild(r);
      });
      w.appendChild(links);
      var rechts = el("div", "tools-kolom weg");
      rechts.appendChild(el("div", "kolom-kop", "nooit aangeroepen"));
      beat.ongebruikt.forEach(function (g) {
        var r = el("div", "tool-rij");
        r.appendChild(el("span", "tool-n", g.groep));
        r.appendChild(el("span", "tool-naam", g.tool));
        rechts.appendChild(r);
      });
      w.appendChild(rechts);
      return w;
    },

    // ── drie gebieden naast elkaar; de rij die kantelt krijgt nadruk ──────
    matrix: function (beat) {
      var w = el("div", "matrix");
      var kop = el("div", "matrix-rij kop");
      kop.appendChild(el("span", "matrix-l", ""));
      beat.kolommen.forEach(function (k) { kop.appendChild(el("span", "matrix-c", k)); });
      w.appendChild(kop);
      beat.rijen.forEach(function (r) {
        var rij = el("div", "matrix-rij" + (r.nadruk ? " nadruk" : ""));
        rij.appendChild(el("span", "matrix-l", r.l));
        r.waarden.forEach(function (v) { rij.appendChild(el("span", "matrix-c", v)); });
        w.appendChild(rij);
      });
      return w;
    },

    // ── de bevindingen over het aanroepen ─────────────────────────────────
    bevindingen: function (beat) {
      var w = el("div", "bevindingen");
      beat.rijen.forEach(function (b, i) {
        var k = el("div", "bevinding");
        k.appendChild(el("span", "bevinding-n", String(i + 1)));
        var t = el("div", "bevinding-tekst");
        t.appendChild(el("div", "bevinding-kop", b.kop));
        t.appendChild(el("p", null, b.tekst));
        k.appendChild(t);
        w.appendChild(k);
      });
      return w;
    },

    // ── de onderzoeksvraag, met de rangorde van de uitkomsten ─────────────
    // De vraag groot, en eronder wat primair is en wat secundair. Die twee regels zijn
    // de hele opzet: een geslaagd antwoord kan een slecht ontworpen tool verbergen.
    onderzoeksvraag: function (beat) {
      var w = el("div", "ovraag");
      w.appendChild(el("div", "ovraag-label", "onderzoeksvraag"));
      w.appendChild(el("p", "ovraag-tekst", beat.vraag));
      var paar = el("div", "ovraag-paar");
      [["primair", beat.primair, "primair"],
       ["secundair", beat.secundair, "secundair"]].forEach(function (p) {
        var c = el("div", "ovraag-cel " + p[2]);
        c.appendChild(el("span", "ovraag-cel-l", p[0]));
        c.appendChild(el("span", "ovraag-cel-r", p[1]));
        paar.appendChild(c);
      });
      w.appendChild(paar);

      // De hypothese is de keten en niet de zin eromheen: drie schakels, en de derde
      // splitst. Geen ondertitels eronder - dat was de kleine tekst die de plaat vulde.
      var hyp = el("div", "ovraag-hypo");
      hyp.appendChild(el("span", "ovraag-label", "hypothese"));
      hyp.appendChild(schakelketen(beat.schakels));
      w.appendChild(hyp);
      return w;
    },

    // ── de werkwijze als keten ────────────────────────────────────────────
    // Dezelfde vorm als de agentplaat in de talk: de vraag wordt een doel, de agent
    // kiest en vult in, en het antwoord komt terug met zijn aannames. Hier is het de
    // procedure die drie keer is uitgevoerd.
    methode: function (beat) {
      var w = el("div", "methode");
      var rij = el("div", "methode-keten");

      function chip(stap, soort) {
        return el("span", "methode-stap " + soort, stap);
      }
      beat.keten.eenmaal.forEach(function (stap, i) {
        if (i) rij.appendChild(el("span", "methode-pijl", "→"));
        rij.appendChild(chip(stap, i === 0 ? "vraag" : "stap"));
      });
      rij.appendChild(el("span", "methode-pijl", "→"));

      // Het middenstuk staat in een haak met een label: dit is het deel dat per vraag
      // meerdere keren is doorlopen. Zonder die haak leest de keten als één aanroep.
      var lus = el("div", "methode-lus");
      var binnen = el("div", "methode-lus-keten");
      beat.keten.herhaald.forEach(function (stap, i) {
        if (i) binnen.appendChild(el("span", "methode-pijl", "→"));
        binnen.appendChild(chip(stap, stap.indexOf("tool call") === 0 ? "call" : "stap"));
      });
      lus.appendChild(binnen);
      lus.appendChild(el("div", "methode-lus-label", beat.keten.lus));
      rij.appendChild(lus);

      rij.appendChild(el("span", "methode-pijl", "→"));
      beat.keten.slot.forEach(function (stap) { rij.appendChild(chip(stap, "evaluatie")); });
      w.appendChild(rij);

      var driemaal = el("div", "methode-driemaal");
      ["Gnephoek", "Zuidplaspolder", "Kockengen"].forEach(function (c) {
        driemaal.appendChild(el("span", "methode-casus", c));
      });
      w.appendChild(el("div", "methode-label", "drie keer dezelfde procedure, met alleen de gebruikersvraag anders"));
      w.appendChild(driemaal);
      w.appendChild(el("div", "methode-eerlijk", beat.eerlijk));
      return w;
    },

    // ── de opzet: een agent, gekoppeld aan de toolbox ─────────────────────
    // Links wie de vraag krijgt, rechts wat er openstaat. De koppeling ertussen is het
    // MCP-protocol, en dat is precies wat er onderzocht wordt.
    opzet: function (beat) {
      var w = el("div", "opzet");
      var links = el("div", "opzet-agent");
      links.appendChild(el("div", "opzet-doos-kop", "de agent"));
      links.appendChild(el("div", "opzet-doos-naam", beat.agent));
      links.appendChild(el("div", "opzet-doos-sub", beat.agentsub));
      w.appendChild(links);
      var brug = el("div", "opzet-brug");
      brug.appendChild(el("span", "opzet-brug-l", "MCP"));
      brug.appendChild(el("span", "opzet-brug-pijl", "⇄"));
      w.appendChild(brug);
      var rechts = el("div", "opzet-tools");
      rechts.appendChild(el("div", "opzet-doos-kop", beat.totaal));
      var gr = el("div", "opzet-groepen");
      beat.groepen.forEach(function (g) {
        var k = el("div", "opzet-groep " + g.soort);
        k.appendChild(el("div", "opzet-groep-kop", g.kop));
        var namen = el("div", "opzet-namen");
        g.tools.forEach(function (tool) {
          namen.appendChild(el("span", "opzet-naam", tool.naam.replace("calculate_", "")));
        });
        k.appendChild(namen);
        gr.appendChild(k);
      });
      rechts.appendChild(gr);
      w.appendChild(rechts);
      return w;
    },

    // ── de toolbox: wat er openstond ──────────────────────────────────────
    // Vier groepen met de kleur die ze in de analyse ook hebben. Dat is de aansluiting:
    // wat hier openstaat is straks wat er wel en niet is aangeraakt.
    toolbox: function (beat) {
      var w = el("div", "toolbox");
      beat.groepen.forEach(function (g) {
        var k = el("div", "tb-groep " + g.soort);
        var kop = el("div", "tb-kop");
        kop.appendChild(el("span", "tb-kop-naam", g.kop));
        kop.appendChild(el("span", "tb-kop-n", g.tools.length + (g.tools.length === 1 ? " tool" : " tools")));
        k.appendChild(kop);
        k.appendChild(el("div", "tb-vraag", g.vraag));
        var lijst = el("div", "tb-tools");
        g.tools.forEach(function (tool) {
          var rij = el("div", "tb-tool");
          rij.appendChild(el("span", "tb-naam", tool.naam));
          if (tool.wat) rij.appendChild(el("span", "tb-wat", tool.wat));
          lijst.appendChild(rij);
        });
        k.appendChild(lijst);
        w.appendChild(k);
      });
      return w;
    },

    // ── het rapport tegenover de kern, op één grootheid ───────────────────
    // Twee getallen naast elkaar en niets erbij. Dat is de enige vorm waarin de zaal een
    // vergelijking kan maken; twee lijstjes met verschillende grootheden kan niemand naast
    // elkaar leggen, en dat was het probleem met de vorige opzet.
    tegenover: function (beat) {
      var w = el("div", "tegen");
      w.appendChild(el("div", "tegen-grootheid", beat.grootheid));
      var paar = el("div", "tegen-paar");
      [["de conclusie in het rapport", beat.rapport, "rapport"], ["het antwoord via onze toolset", beat.kern, "kern"]].forEach(function (z) {
        var k = el("div", "tegen-cel " + z[2]);
        k.appendChild(el("div", "tegen-kop", z[0]));
        var getal = el("div", "tegen-getal");
        getal.appendChild(el("span", "tegen-cijfer", z[1].getal));
        getal.appendChild(el("span", "tegen-eenheid", z[1].eenheid));
        k.appendChild(getal);
        k.appendChild(el("div", "tegen-bij", z[1].bij));
        paar.appendChild(k);
      });
      w.appendChild(paar);
      w.appendChild(el("div", "tegen-duiding", beat.duiding));
      return w;
    },

    // ── de onderzoeksvraag beantwoord ─────────────────────────────────────
    // Zelfde opbouw als de vraagplaat in stap 1: de vraag klein bovenaan, het antwoord
    // groot, en eronder wat hield tegenover wat kraakte. De bonus staat apart en onderaan,
    // want dat is de secundaire uitkomst en die hoort niet in het midden.
    beantwoord: function (beat) {
      var w = el("div", "beantw");
      w.appendChild(el("div", "beantw-vraag", beat.vraag));
      w.appendChild(schakelketen(beat.schakels));
      w.appendChild(el("p", "beantw-slot", beat.slot));
      var sec = el("div", "beantw-sec");
      sec.appendChild(el("span", "beantw-sec-kop", beat.secundair.kop));
      sec.appendChild(el("span", "beantw-sec-tekst", beat.secundair.tekst));
      w.appendChild(sec);
      return w;
    },

    // ── de resultaten per criterium ───────────────────────────────────────
    // De primaire uitkomst krijgt een dikke streep en de secundaire een stippellijn;
    // `deels` is een eigen teken en geen halve ja.
    resultaten: function (beat) {
      var w = el("div", "res");
      var kop = el("div", "res-rij kop");
      kop.appendChild(el("span", null, ""));
      beat.casussen.forEach(function (c) { kop.appendChild(el("span", "res-c", c)); });
      kop.appendChild(el("span", null, ""));
      w.appendChild(kop);
      beat.rijen.forEach(function (r) {
        var rij = el("div", "res-rij" + (r.primair ? " primair" : "") + (r.secundair ? " secundair" : ""));
        rij.appendChild(el("span", "res-crit", r.criterium));
        r.waarden.forEach(function (v) {
          var cel = el("span", "res-c res-" + v);
          cel.appendChild(el("span", "res-teken", v === "ja" ? "✓" : "~"));
          rij.appendChild(cel);
        });
        // De noot is een steekwoord en geen zin: wie leest, luistert niet.
        rij.appendChild(el("span", "res-noot", r.noot));
        w.appendChild(rij);
      });
      w.appendChild(el("div", "res-slot", beat.slot));
      return w;
    },

    // ── de cascade-aanroepen van één casus ────────────────────────────────
    // Drie beats gebruiken deze plaat, één per gebied, met dezelfde opbouw: per aanroep
    // een nummer, de bui, de intentie in één regel, en daaronder de knopenlijst als
    // tekening. Dat de opbouw identiek is, maakt het verschil tussen de gebieden zichtbaar.
    casusaanroepen: function (beat) {
      var w = el("div", "cas-aanroepen");
      // De toolnaam en het aantal boven de plaat: zonder die regel is niet te zien dat dit
      // tool calls zijn, en dat is precies wat deze drie platen laten zien.
      var telwoord = ["geen", "één", "twee", "drie", "vier", "vijf", "zes", "zeven"];
      var n = beat.aanroepen.length;
      var kop = el("div", "cas-tool");
      kop.appendChild(el("span", "cas-tool-naam", beat.tool));
      kop.appendChild(el("span", "cas-tool-bij",
        (telwoord[n] || n) + (n === 1 ? " tool call" : " tool calls") + " bij " + beat.casus));
      w.appendChild(kop);
      beat.aanroepen.forEach(function (a) {
        var cel = el("div", "cas-cel " + a.vorm);
        var kop = el("div", "cas-kop");
        kop.appendChild(el("span", "cas-nr", "aanroep " + a.nr + " van " + beat.aanroepen.length));
        kop.appendChild(el("span", "cas-bui", "bui van " + a.bui));
        kop.appendChild(el("span", "cas-tel", a.tel));
        cel.appendChild(kop);
        cel.appendChild(el("div", "cas-intentie", a.intentie));
        // De tekening links, en rechts wat eruit kwam met de reden dat er een volgende
        // aanroep kwam. Dat tweede is het verhaal van deze drie platen: de tool schuift van
        // netwerk naar variant, en elke stap heeft een aanleiding in het antwoord ervoor.
        var lijf = el("div", "cas-lijf");
        lijf.appendChild(diagram(a, true));
        if (a.uitkomst) {
          // Eén veld, één uitkomst, één gevolg - en niet meer. De pijl wijst naar beneden
          // als er een volgende aanroep uit voortkwam, en wordt een vinkje bij de laatste.
          // De onderbouwing hoort in de mond van de presentator en niet op de plaat.
          var u = el("div", "cas-uit" + (a.uitkomst.slot ? " slot" : ""));
          u.appendChild(el("div", "cas-veld", a.uitkomst.veld));
          u.appendChild(el("div", "cas-waarde", a.uitkomst.waarde));
          var dus = el("div", "cas-dus");
          dus.appendChild(el("span", "cas-dus-teken", a.uitkomst.slot ? "\u2713" : "\u2193"));
          dus.appendChild(el("span", "cas-dus-tekst", a.uitkomst.dus));
          u.appendChild(dus);
          lijf.appendChild(u);
        }
        cel.appendChild(lijf);
        w.appendChild(cel);
      });
      return w;
    },


    // ── de aanbevelingen, met de casus die ze opriep ──────────────────────
    // ── eerst wat blijft, dan wat verandert ──────────────────────────────
    // De volgorde is een uitspraak: begin met wat werkt, want een aanbevelingenlijst
    // zonder dat leest als een lijst gebreken. Daarna de drie die er echt zijn - groot,
    // onder elkaar, met hun reden - en dan een streep en drie die kleiner mogen omdat
    // het een schakelaar, een toegestane waarde en een terugmelding zijn.
    aanbevelingen: function (beat) {
      var w = el("div", "aanbev");

      beat.rijen.filter(function (a) { return a.houden; }).forEach(function (a) {
        var k = el("div", "aanbev-houden");
        k.appendChild(el("span", "aanbev-n", "✓"));
        var tekst = el("div", "aanbev-tekst");
        tekst.appendChild(el("div", "aanbev-wat", a.wat));
        tekst.appendChild(el("div", "aanbev-waarom", a.waarom));
        k.appendChild(tekst);
        w.appendChild(k);
      });

      w.appendChild(el("div", "aanbev-label", "en dit zou het beter maken"));

      var voor = el("div", "aanbev-voor");
      beat.rijen.filter(function (a) { return a.voor; }).forEach(function (a, i) {
        var k = el("div", "aanbev-groot");
        k.appendChild(el("span", "aanbev-n", String(i + 1)));
        var tekst = el("div", "aanbev-tekst");
        tekst.appendChild(el("div", "aanbev-wat", a.wat));
        tekst.appendChild(el("div", "aanbev-waarom", a.waarom));
        k.appendChild(tekst);
        voor.appendChild(k);
      });
      w.appendChild(voor);

      var achter = el("div", "aanbev-achter");
      beat.rijen.filter(function (a) { return !a.voor && !a.houden; }).forEach(function (a, i) {
        var r = el("div", "aanbev-klein");
        r.appendChild(el("span", "aanbev-n-klein", String(i + 4)));
        r.appendChild(el("span", "aanbev-wat-klein", a.wat));
        r.appendChild(el("span", "aanbev-waarom-klein", a.waarom));
        achter.appendChild(r);
      });
      w.appendChild(achter);
      return w;
    },

    slot: function () {
      var w = el("div", "slot");
      w.appendChild(el("div", "slot-groot", "de rangorde houdt, de maatvoering beweegt"));
      w.appendChild(el("p", "slot-klein",
        "Drie polders met een gepubliceerd rapport, vijftien aanroepen, één sessie. Het model " +
        "is sterk over haalbaarheid en rangorde en zwak over maatvoering — genoeg om een " +
        "ontwerpkeuze te bevragen, en niet genoeg om er een te nemen."));
      return w;
    }
  };

  // ── het toneel ───────────────────────────────────────────────────────────
  function toneel(item) {
    var t = el("section", "toneel");
    if (!item.stap) {
      var v = el("div", "titelblad");
      v.appendChild(el("h1", null, INHOUD.titel.kop));
      t.appendChild(v);
      return t;
    }
    // Alleen de naam van de stap, geen ondertitel erbij: die stond er als toelichting
    // en werd op een beamer een tweede regel die niemand leest.
    var hoofd = el("div", "toneel-kop");
    hoofd.appendChild(el("span", "toneel-naam", item.stap.naam));
    t.appendChild(hoofd);

    // Een plaat die omvalt mag nooit een wit scherm geven: het toneel is op dat moment
    // al leeggemaakt, en dan staat er niets meer. Liever een zichtbare melding op de
    // plek van de plaat, zodat je in een repetitie ziet WAT er mist.
    var maak = PLAAT[item.beat.toon];
    if (!maak) {
      t.appendChild(el("div", "kapot", "onbekende plaat: " + item.beat.toon));
    } else {
      try {
        t.appendChild(maak(item.beat));
      } catch (fout) {
        t.appendChild(el("div", "kapot", "plaat “" + item.beat.toon + "” valt om: " + fout.message));
      }
    }

    var voet = item.beat.voet || item.stap.bron;
    if (voet) t.appendChild(el("div", "toneel-bron", voet));
    return t;
  }

  // ── de voet: de zin, en waar je in de stap bent ──────────────────────────
  function voet(item) {
    var f = el("footer", "voet");
    var punten = el("div", "punten");
    for (var i = 0; i < item.van; i++) {
      punten.appendChild(el("span", "punt" + (i === item.index ? " aan" : (i < item.index ? " gehad" : ""))));
    }
    f.appendChild(punten);
    f.appendChild(el("p", "regel", item.beat.regel));
    return f;
  }

  function teken() {
    var item = BEATS[nu];
    app.innerHTML = "";
    app.appendChild(kop(item.stap));
    app.appendChild(toneel(item));
    app.appendChild(voet(item));
    var s = INHOUD.stappen.indexOf(item.stap);
    location.hash = item.stap ? (s + 1) + "." + (item.index + 1) : "";
  }

  // ── bewegen ──────────────────────────────────────────────────────────────
  function naar(i) {
    nu = Math.max(0, Math.min(BEATS.length - 1, i));
    teken();
  }
  function naarStap(i) {
    var stap = INHOUD.stappen[i];
    for (var b = 0; b < BEATS.length; b++) {
      if (BEATS[b].stap === stap) { naar(b); return; }
    }
  }
  function stapOp(richting) {
    var i = INHOUD.stappen.indexOf(BEATS[nu].stap);
    if (richting > 0 && i + 1 < INHOUD.stappen.length) naarStap(i + 1);
    else if (richting < 0 && i > 0) naarStap(i - 1);
    else if (richting < 0) naar(0);
  }

  document.addEventListener("keydown", function (e) {
    var hulp = document.getElementById("hulp");
    if (e.key === "ArrowRight" || e.key === " " || e.key === "Enter") { naar(nu + 1); e.preventDefault(); }
    else if (e.key === "ArrowLeft" || e.key === "Backspace") { naar(nu - 1); e.preventDefault(); }
    else if (e.key === "ArrowDown") { stapOp(1); e.preventDefault(); }
    else if (e.key === "ArrowUp") { stapOp(-1); e.preventDefault(); }
    else if (e.key >= "1" && e.key <= "9") { naarStap(Number(e.key) - 1); }
    else if (e.key === "Escape") { naar(0); }
    else if (e.key === "f") { if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen(); }
    else if (e.key === "?") { hulp.hidden = !hulp.hidden; }
  });

  // Klikken alleen op het toneel en de voet: een klik om het venster naar
  // voren te halen mag geen beat opschuiven.
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".toneel, .voet")) return;
    naar(e.clientX < window.innerWidth * 0.15 ? nu - 1 : nu + 1);
  });

  // `#4.2` opent stap 4 op beat 2, ook als de pagina al open staat.
  function uitHash() {
    var m = /^#(\d+)(?:\.(\d+))?$/.exec(location.hash);
    if (!m) return false;
    var stap = INHOUD.stappen[Number(m[1]) - 1];
    if (!stap) return false;
    var beat = Math.max(1, Number(m[2] || 1)) - 1;
    for (var b = 0; b < BEATS.length; b++) {
      if (BEATS[b].stap === stap && BEATS[b].index === beat) { nu = b; return true; }
    }
    return false;
  }
  window.addEventListener("hashchange", function () { if (uitHash()) teken(); });

  uitHash();
  teken();
})();
