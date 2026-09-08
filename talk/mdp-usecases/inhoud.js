// ═══════════════════════════════════════════════════════════════════════════
// De inhoud. Dit is het enige bestand dat je per repetitie aanraakt.
// ═══════════════════════════════════════════════════════════════════════════
//
// De deck is opgebouwd als een experiment, en het onderzoeksobject is de TOOLSET.
// Niet de polder, en ook niet de vraag of het antwoord goed was:
//
//     onderzoek ⇒ toolbox ⇒ drie situaties ⇒ resultaten
//               ⇒ limitaties ⇒ analyse ⇒ conclusie
//
// De deck eindigt op de aanbevelingen voor de toolset; er staat geen voorbehoudstap meer
// achter. De caveats zitten in de limitaties, met de situatie erbij waar ze opkwamen.
//
// De drie gebieden zijn de experimentele situaties waarin die toolset wordt getest.
// Daarom hebben ze opzettelijk dezelfde drie beats - gebied en vraag, ons antwoord, en
// ernaast de conclusie van het rapport. Als de vorm gelijk is, dan is het verschil tussen
// de casussen het GEBIED en niet de manier van kijken.
//
// De primaire uitkomst is INZICHT in de benadering en het gebruik van de toolset; het
// antwoord op de gebiedsvraag is de secundaire. Die rangorde zit in de volgorde van de
// stappen: eerst hoe het gereedschap is gepakt, en pas daarna wat het opleverde.
//
// Geen enkel getal staat hier met de hand. Alles komt uit `TRANSCRIPT`: de opname van de
// MCP-endpoint en van de sessielog.

var T = TRANSCRIPT;

function n(x, d) {
  return (typeof d === "number" ? x.toFixed(d) : String(x)).replace(".", ",");
}

// Elke casus levert drie beats, en de tekst eromheen verwijst alleen naar velden die alle
// drie de casussen hebben. Zo kan er geen casus zijn die stilletjes een andere vorm krijgt.
var KAARTEN = {
  Gnephoek: "kaart-gnephoek.svg",
  Zuidplaspolder: "kaart-zuidplas.svg",
  Kockengen: "kaart-detol.svg"
};
var ZINNEN = {
  Gnephoek: [
    "Situatie één: polder Gnephoek bij Alphen aan den Rijn. Er ligt een gepubliceerd antwoord op onze vraag.",
    "Het rapport vraagt vijfenveertig hectare open water. Via onze toolset komen er twee bíj."
  ],
  Zuidplaspolder: [
    "Situatie twee: de Zuidplaspolder, met een maalstop — bij deze bui gaan de keringen dicht en mag er niet gemalen worden.",
    "Het rapport komt op vierentachtig centimeter; via onze toolset op honderdtweeënvijftig."
  ],
  Kockengen: [
    "Situatie drie: achtentwintig juli 2014. Dit is de enige casus waar de bui echt gevallen is.",
    "Het gemaal haalt dertien millimeter per dag. Om deze bui op dertig centimeter te houden was negenentwintig nodig."
  ]
};

var CASUSSTAPPEN = T.casussen.map(function (c) {
  return {
    naam: c.naam,
    titel: c.soort,
    bron: c.bron,
    beats: [
      {
        regel: ZINNEN[c.naam][0],
        toon: "casus",
        kaart: KAARTEN[c.naam],
        plaats: c.plaats,
        context: c.context,
        vraag: c.vraag
      },
      {
        regel: ZINNEN[c.naam][1],
        toon: "tegenover",
        grootheid: c.tegenover.grootheid,
        rapport: c.tegenover.rapport,
        kern: c.tegenover.kern,
        duiding: c.tegenover.duiding,
        voet: "de aanroepen staan bij de analyse · opname " + T.opgenomen
      }
    ]
  };
});

var VOOR = [
  // ─────────────────────────────────────────────────────────────────────────
  {
    naam: "onderzoek",
    bron: "één sessie · drie situaties · dezelfde toolset",
    beats: [
      {
        regel:
          "De vraag gaat niet over water. Hij gaat over de toolset: hoe benadert en " +
          "gebruikt een agent hem bij het beantwoorden van een gebruikersvraag?",
        toon: "onderzoeksvraag",
        vraag: T.onderzoek.vraag,
        primair: T.onderzoek.primair,
        secundair: T.onderzoek.secundair,
        hypothese: T.onderzoek.hypothese,
        schakels: T.onderzoek.schakels,
        voet:
          "Die derde schakel is de hele hypothese: een tool gebruiken zoals hij is ontworpen en " +
          "hem gebruiken zoals de vraag het vraagt, zijn twee dingen — en ze vielen niet altijd samen."
      },
    ]
  },

  // ─────────────────────────────────────────────────────────────────────────
  {
    naam: "opzet",
    bron: "een Claude-agent, met de MCP-toolset van de rekenkern eraan",
    beats: [
      {
        regel:
          "De opzet is één agent met één toolbox eraan. Twaalf tools in vier groepen: " +
          "een handleiding, vier maatregelen in twee richtingen, twee systeemvragen en een " +
          "pakketzoeker.",
        toon: "opzet",
        agent: "Claude",
        agentsub: "krijgt de gebruikersvraag, kiest en vult in",
        totaal: T.toolbox.totaal,
        groepen: T.toolbox.groepen,
        voet: T.toolbox.meebrengt
      },
      {
        regel:
          "En dit is de procedure, drie keer identiek doorlopen. Let op het gestippelde " +
          "deel: dat doorloopt de agent cyclisch, tot hij genoeg heeft om te antwoorden.",
        toon: "methode",
        keten: T.onderzoek.keten,
        eerlijk: T.onderzoek.eerlijk,
        voet:
          "In de talk staat deze keten bij de policy, als belofte. Hier is het de procedure die " +
          "drie keer is uitgevoerd, met de sessielog ernaast."
      }
    ]
  }
];

var NA = [
  // ─────────────────────────────────────────────────────────────────────────
  {
    naam: "resultaten",
    titel: "wat het gebruik laat zien",
    bron: "zes criteria · drie situaties · vijftien aanroepen",
    beats: [
      {
        regel:
          "Zes criteria, drie situaties. Vijftien aanroepen, vijftien geldige antwoorden — " +
          "en toch staat er in de helft van de vakjes geen volmondige ja.",
        toon: "resultaten",
        casussen: T.resultaten.casussen,
        rijen: T.resultaten.rijen,
        slot: T.resultaten.slot,
        voet:
          "Waar `deels` staat was de aanroep geldig maar betekende hij niet wat de tool bedoelt. " +
          "Dat is geen zachte ja maar de vindplaats: elk van die vakjes is een moment waarop het " +
          "gebruik van het ontwerp afweek."
      },
    ]
  },

  // ─────────────────────────────────────────────────────────────────────────
  {
    naam: "limitaties",
    titel: "wat de rekenkern niet kan, opgelopen in deze drie situaties",
    bron: "de `caveats` uit de tooluitvoer, plus wat er in de invoer niet te zeggen was",
    beats: [
      {
        regel:
          "Tien limitaties, en dit is geen lijst op voorraad: achter elke regel staat de " +
          "situatie waar hij zich liet zien.",
        toon: "limitaties",
        rijen: T.limitaties,
        voet:
          "De vier met een dikke streep zijn hard: die veranderen het antwoord. De andere zes " +
          "verschuiven het, en staan in de tooluitvoer als `caveat` gemeld."
      },
    ]
  },

  // ─────────────────────────────────────────────────────────────────────────
  {
    naam: "analyse",
    bron: "uit de sessielog van " + T.experiment.sessie.datum + " · " +
          T.experiment.sessie.calls + " tool calls, " + T.experiment.sessie.mcp +
          " op de rekenkern, één sessie van " + n(T.experiment.sessie.uren) + " uur",
    beats: [
      {
        regel:
          "Een geldige aanroep zegt nog niet waarom hij werkte. Dus eerst de volgorde: " +
          "bij de eerste situatie wordt de toolbox in de breedte afgelopen, daarna gaat het " +
          "meteen naar netwerk en pakket.",
        toon: "volgorde",
        per_casus: T.experiment.per_casus,
        voet:
          "Dezelfde agent, dezelfde toolset, oplopende gerichtheid. De kleuren zijn die van de " +
          "toolbox in stap twee."
      },
      {
        regel:
          "En kijk welke tool het meest is aangeroepen: het netwerk, zes keer. Dat is " +
          "de verrassing, want de vraag ging drie keer over één gebied.",
        toon: "tools",
        gebruikt: T.experiment.gebruikt,
        ongebruikt: T.experiment.ongebruikt,
        voet:
          "En zes van de twaalf zijn nooit aangeroepen: alle voorwaartse varianten en de hele " +
          "droge kant. Voorwaarts rekenen ging via het netwerk, want dat neemt meerdere gebieden " +
          "in één call en vraagt geen doelwaarde."
      },
      {
        regel:
          "Dus: waarom die zes? Kijk niet naar de getallen maar naar de beweging. Bij " +
          "Gnephoek is de aanroep een echt netwerk — en de eerste poging meet nul " +
          "doorwerking. Dát is de reden dat er een tweede kwam.",
        toon: "casusaanroepen",
        tool: "calculate_cascade_given_excess",
        casus: "Gnephoek",
        aanroepen: T.experiment.zes[0].aanroepen,
        voet:
          "Dit is de enige situatie waarin de tool als netwerk is gebruikt, en er waren twee " +
          "aanroepen nodig om er te komen: de knopen anders verbinden was een schemakeuze."
      },
      {
        regel:
          "Bij de Zuidplaspolder valt de doorwerking helemaal weg — en op zeven gebieden " +
          "komen twee getallen terug. Dan kunnen er ook twee knopen in, en die zijn geen " +
          "gebied meer maar een variant.",
        toon: "casusaanroepen",
        tool: "calculate_cascade_given_excess",
        casus: "de Zuidplaspolder",
        aanroepen: T.experiment.zes[1].aanroepen,
        voet:
          "Hier kantelt het gebruik: van zeven gebieden zonder verbinding naar één gebied twee " +
          "keer. Dezelfde tool, dezelfde velden, en een andere vraag eronder."
      },
      {
        regel:
          "En bij Kockengen gaat de tool alleen nog in variantvorm de deur uit — twee keer, " +
          "want de bui staat één keer per aanroep en een variant óp de bui past er niet naast.",
        toon: "casusaanroepen",
        tool: "calculate_cascade_given_excess",
        casus: "Kockengen",
        aanroepen: T.experiment.zes[2].aanroepen,
        voet:
          "En let op wat er met het gebiedsvreemde water is gebeurd: er is geen veld voor een " +
          "inlaat, dus is het omgerekend naar 6,4 mm neerslag. De tool ziet geen tweede bron maar " +
          "een grotere bui — en die conversie staat in geen enkel `assumptions`."
      },
    ]
  },

  // ─────────────────────────────────────────────────────────────────────────
  {
    naam: "conclusie",
    titel: "wat het experiment over de toolset zegt",
    bron: "drie situaties · vijftien aanroepen · één sessie",
    beats: [
      {
        regel:
          "De onderzoeksvraag, beantwoord — met dezelfde drie schakels als de hypothese, " +
          "nu met wat er van elk terechtkwam.",
        toon: "beantwoord",
        vraag: T.beantwoord.vraag,
        schakels: T.beantwoord.schakels,
        slot: T.beantwoord.slot,
        secundair: T.beantwoord.secundair,
        voet:
          "Een geslaagd antwoord kan een slecht ontworpen tool verbergen, en een gekraakt " +
          "gebruik kan een goed antwoord opleveren. Daarom staat de derde schakel apart."
      },
      {
        regel:
          "Begin met wat moet blijven — daar zit de reden dat dit werkte. En dan zes " +
          "aanbevelingen: drie die er echt zijn, en drie kleinere.",
        toon: "aanbevelingen",
        rijen: T.experiment.aanbevelingen,
        voet:
          "De zes komen elk uit een moment in deze sessie waarop de invoer niet kon zeggen wat het " +
          "gebied wél zei. Dat is de opbrengst van een experiment dat over het gereedschap gaat en " +
          "niet alleen over het water."
      }
    ]
  },

];

var INHOUD = {
  titel: {
    kop: "Een experiment op onze MCP-toolset, in drie polders",
    regel:
      "Het onderzoeksobject is de toolset en niet het water. Drie gebieden met een " +
      "gepubliceerd rapport zijn de situaties waarin we hem testen — en alles in één sessie."
  },
  stappen: VOOR.concat(CASUSSTAPPEN).concat(NA)
};
