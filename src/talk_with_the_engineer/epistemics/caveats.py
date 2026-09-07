"""Structurele onzekerheid: wat dit model niet weet, met naam en toedracht.

Twee soorten onzekerheid, twee mechanismen, en ze worden bewust niet samengevoegd:

    parametrisch  -> BEREKENBAAR. Meld hem als een berekend bereik; zie `uncertainty.py`.
    structureel   -> NIET berekenbaar. Meld hem als een benoemde lijst: `ModelCaveat`.

Nooit als een gefuseerd getal. Een gefabriceerd "+/- 15 %" is erger dan een gefabriceerd
puntgetal, want het ziet uit als kennis.
"""

from pydantic import BaseModel, ConfigDict, Field

from talk_with_the_engineer.epistemics.assumptions import in_language, language_of


class ModelCaveat(BaseModel):
    """Een structurele beperking die op dít antwoord van toepassing is.

    Geen algemene disclaimer en geen percentage: een benoemde term met de richting waarin
    hij schuift. Conditioneel, zodat een lezer alleen ziet wat hier geldt - dezelfde vorm
    als `assumptions`, die al bewijst dat een agent dat oppikt.
    """

    model_config = ConfigDict(frozen=True)

    topic: str = Field(..., description="Waar de beperking over gaat")
    what: str = Field(..., description="Wat er niet in het model zit, of open staat")
    consequence: str = Field(
        ..., description="In welke richting en hoeveel het antwoord kan schuiven"
    )


def _caveat(language: str, topic: dict, what: dict, consequence: dict) -> "ModelCaveat":
    """Bouw de caveat in de taal van de aanroep.

    Drie tweetalige woordenboeken en geen if/else per regel: zo staat de Nederlandse en de
    Engelse formulering van dezelfde beperking naast elkaar, en is te zien wanneer er een
    uit de pas loopt.
    """
    return ModelCaveat(
        topic=in_language(topic, language),
        what=in_language(what, language),
        consequence=in_language(consequence, language),
    )


def _summer_loss_caveat(input, extra) -> "ModelCaveat | None":
    if getattr(input, "time_of_year", None) != "summer":
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "neerslagverlies van dit gebied",
            "en": "rainfall loss of this area",
        },
        {
            "nl": (
                "Er gaat 20 mm neerslagverlies van de eerste twee dagen af: wat dit "
                "oppervlak vasthoudt voordat er iets tot afvoer komt. Dat is een "
                "eigenschap van het GEBIED en niet van de bui, en het staat hier op een "
                "landelijke vuistregel en niet op een waarde voor dit gebied. Of het "
                "verlies bovendien al in de gebruikte neerslagstatistiek zit is een open "
                "vraag"
            ),
            "en": (
                "20 mm of rainfall loss is subtracted from the first two days. That is a "
                "property of the AREA and not of the event - what this surface holds back "
                "before anything reaches the water system - but it rests on a national "
                "rule of thumb here and not on a value for this area. Whether the loss is "
                "also already contained in the rainfall statistic used is an open question"
            ),
        },
        {
            "nl": (
                "Een gebied dat meer vasthoudt dan 20 mm krijgt hier dus een te zware "
                "maatregel en een gebied dat minder vasthoudt een te lichte; het verlies "
                "schaalt niet mee met de terugkeertijd. Zit het verlies al in de "
                "statistiek, dan wordt het bovendien dubbel geteld en valt de benodigde "
                "maatregel tot een derde lager uit - alle zomeruitkomsten zijn dan "
                "systematisch aan de veilige kant"
            ),
            "en": (
                "An area that holds back more than 20 mm therefore gets too heavy a "
                "measure here and one that holds back less too light a measure; the loss "
                "does not scale with the return period. If the loss is already in the "
                "statistic it is counted twice on top of that, and the measure needed "
                "comes out up to a third smaller - every summer answer is then "
                "systematically on the safe side"
            ),
        },
    )


def _event_length_caveat(input, extra) -> "ModelCaveat | None":
    length = getattr(input, "length_event_hrs", None)
    if length not in (48.0, 192.0):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "verdeling van het neerslagverlies",
            "en": "how the rainfall loss is spread",
        },
        {
            "nl": (
                "De regel die het verlies over de eerste twee dagen verdeelt is ontworpen "
                "voor een vierdaagse bui; bij 48 en 192 uur valt de piek elders"
            ),
            "en": (
                "The rule that spreads the loss over the first two days was designed for a "
                "four-day event; at 48 and 192 hours the peak falls elsewhere"
            ),
        },
        {
            "nl": (
                "Bij 192 uur dragen de eerste twee dagen samen 12 % van de bui, dus is de "
                "verdeling van het verlies daar het minst zeker"
            ),
            "en": (
                "At 192 hours the first two days together carry 12 % of the event, so the "
                "spread of the loss is least certain there"
            ),
        },
    )


def _return_period_caveat(input, extra) -> "ModelCaveat | None":
    period = getattr(input, "return_period", None)
    if period is None or period < 200:
        return None
    return _caveat(
        language_of(input),
        {"nl": "extrapolatie van de statistiek", "en": "extrapolating the statistic"},
        {
            "nl": (
                f"Een terugkeertijd van {period:g} jaar komt uit een reeks die veel korter "
                "is dan die terugkeertijd"
            ),
            "en": (
                f"A return period of {period:g} years comes from a record that is much "
                "shorter than that return period"
            ),
        },
        {
            "nl": (
                "De neerslagsom zelf heeft daar een onzekerheid die groter is dan het "
                "verschil tussen twee naburige terugkeertijden. Gebruik zo'n bui als "
                "testas en niet als voorspelling"
            ),
            "en": (
                "The rainfall total itself carries an uncertainty there that is larger "
                "than the difference between two neighbouring return periods. Use such an "
                "event as a test axis and not as a prediction"
            ),
        },
    )


def _cost_caveat(input, extra) -> "ModelCaveat | None":
    if not extra.get("has_cost"):
        return None
    return _caveat(
        language_of(input),
        {"nl": "kostenvorm", "en": "shape of the cost"},
        {
            "nl": (
                "De kosten zijn lineair in de toename gerekend, terwijl een gemaal in "
                "werkelijkheid een trapkost is: je koopt een gemaal en niet een m3/min"
            ),
            "en": (
                "Costs are computed as linear in the increase, while a pumping station is "
                "really a step cost: you buy a station and not a m3/min"
            ),
        },
        {
            "nl": (
                "Lineair onderschat een kleine uitbreiding sterk, en het verandert de "
                "rangorde: in de vervangingslezing is er een omslagnorm waarBOVEN bergen "
                "goedkoper is dan afvoeren, en waaronder afvoeren wint. Waar die norm "
                "ligt verschilt per gebied, gemaal en bui - gemeten tussen ongeveer 40 en "
                "150 cm op uiteenlopende polders - dus lees de rangorde van dit antwoord "
                "af in plaats van er een vaste grens voor te nemen. De eenheidsprijzen "
                "hebben zelf een bandbreedte van ongeveer een factor twee bij bergen"
            ),
            "en": (
                "Linear badly understates a small extension, and it changes the ranking: "
                "under the replacement reading there is a crossover norm ABOVE which "
                "storage is cheaper than discharge, and below which discharge wins. Where "
                "that norm lies differs per area, pumping station and event - measured "
                "between roughly 40 and 150 cm across diverse polders - so read the "
                "ranking off this answer instead of assuming a fixed threshold. The unit "
                "prices themselves have a spread of roughly a factor two for storage"
            ),
        },
    )


def _supply_availability_caveat(input, extra) -> "ModelCaveat | None":
    """De dragende aanname onder een aanvoerantwoord - tenzij hij is opgegeven.

    Zolang de beller geen bronvolume meegeeft, rekent de tool met een onbeperkte bron en is
    dit de belangrijkste caveat van het hele model: op de natte kant is "de rand neemt je
    water aan" onschuldig, op de droge kant is hij dragend.

    Geef je het volume wél mee, dan zit de beschikbaarheid IN het model en is deze tekst
    onwaar. Dan blijft er een andere beperking over - waar dat volume vandaan komt - en die
    staat in `_supply_source_origin_caveat`. Dat onderscheid is de reden dat deze regel
    conditioneel is en niet altijd afgaat.
    """
    volume = extra.get("required_supply_volume_m3")
    if not volume or extra.get("source_volume_is_modelled"):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "beschikbaarheid van aanvoerwater",
            "en": "availability of water to draw in",
        },
        {
            "nl": (
                "Dit antwoord gaat over de capaciteit van de inlaat en veronderstelt dat "
                "het water bij die inlaat beschikbaar is. Dat is een eigenschap van het "
                "regionale watersysteem en niet van dit gebied, en het zit niet in dit model"
            ),
            "en": (
                "This answer is about the capacity of the intake and assumes the water is "
                "available at that intake. That is a property of the regional water system "
                "and not of this area, and it is not in this model"
            ),
        },
        {
            "nl": (
                f"Er is {volume / 1e6:.2f} miljoen m3 nodig over de opgegeven periode. In "
                "hoog Nederland - de zandgronden, boven het landelijke verdeelnetwerk - is "
                "aanvoer doorgaans niet beschikbaar en is beschikbaarheid en niet "
                "capaciteit de bindende beperking. Bij tekort rantsoeneert de "
                "verdringingsreeks landelijk"
            ),
            "en": (
                f"{volume / 1e6:.2f} million m3 is needed over the period given. In the "
                "elevated parts of the Netherlands - the sandy soils, above the national "
                "distribution network - supply is usually not available, and availability "
                "rather than capacity is the binding constraint. Under shortage the legal "
                "priority order rations nationally"
            ),
        },
    )


def _supply_source_origin_caveat(input, extra) -> "ModelCaveat | None":
    """Wat er overblijft zodra de bron wel is gemodelleerd.

    Dit is de opvolger van `_supply_availability_caveat`: de beschikbaarheid zit nu in het
    model, maar het volume is een INVOER. Hoe het tot stand komt - de landelijke
    waterverdeling, het Distributiemodel, de afvoer van de Rijn - zit er niet in.

    Tenzij het volume uit de droogtestatistiek komt. Dan is een deel van die herkomst er wel
    in gekomen - hoeveel minder de rivier levert bij een droogte van deze zeldzaamheid - en
    is deze tekst in die vorm onwaar. `_supply_source_statistic_caveat` neemt het dan over,
    met wat er dan nog openstaat en wat de statistiek zelf niet hard maakt.
    """
    if not extra.get("source_volume_is_modelled") or extra.get(
        "source_volume_from_statistic"
    ):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "herkomst van het bronvolume",
            "en": "where the source volume comes from",
        },
        {
            "nl": (
                "De beschikbaarheid van aanvoerwater zit nu IN dit antwoord, want er is een "
                "bronvolume opgegeven. Wat er niet in zit is hoe dat volume tot stand komt: "
                "de landelijke waterverdeling, het Distributiemodel, de afvoer van de rivier"
            ),
            "en": (
                "The availability of water is now IN this answer, because a source volume "
                "was given. What is not in it is how that volume comes about: the national "
                "water distribution, the Distribution Model, the discharge of the river"
            ),
        },
        {
            "nl": (
                "Dit antwoord is dus voorwaardelijk - 'als er zoveel is, dan gebeurt dit' - "
                "en geen voorspelling van hoeveel er zal zijn. Bij schaarste rantsoeneert de "
                "verdringingsreeks landelijk, en wat deze polder dan toekomt is een "
                "verdeling over meer afnemers; daarvoor is er een aparte vraag"
            ),
            "en": (
                "This answer is therefore conditional - 'if there is this much, then this "
                "happens' - and not a prediction of how much there will be. Under scarcity "
                "the legal priority order rations nationally, and what this area is then "
                "entitled to is an allocation across more consumers; there is a separate "
                "question for that"
            ),
        },
    )


def _supply_source_statistic_caveat(input, extra) -> "ModelCaveat | None":
    """Wat de afgeleide bron wel en niet hard maakt.

    Het bronvolume komt nu uit dezelfde statistiek als de droogte, en dat is winst: vraag en
    aanbod bewegen niet meer los van elkaar. Maar het verband waarop dat rust is zwak, en dat
    hoort een lezer te weten voordat hij op de derde decimaal gaat sturen.
    """
    if not extra.get("source_volume_from_statistic"):
        return None
    fraction = extra.get("source_availability_fraction")
    low, high = extra.get("source_spread_factor", (None, None))
    correlation = extra.get("source_fit_r")
    river = extra.get("source_river")
    # De aanvoertools zetten die band ook in `sensitivity`; de allocatietool heeft dat veld
    # niet. Het veld noemen waar het niet staat is erger dan het niet noemen.
    listed = extra.get("source_spread_in_sensitivity")
    where_nl = " Hij staat ook in `sensitivity`." if listed else ""
    where_en = " It is also in `sensitivity`." if listed else ""
    return _caveat(
        language_of(input),
        {
            "nl": "het bronvolume komt uit een zwak verband",
            "en": "the source volume rests on a weak relation",
        },
        {
            "nl": (
                f"Het aanbod is afgeleid uit de minimale 7-daagse {river}afvoer bij deze "
                f"droogte: {fraction * 100:.0f} % van een normaal jaar. Dat is een verband "
                f"met een correlatie van {correlation:+.2f} - een droogte in de polder en "
                "een lage rivierafvoer vallen maar deels samen"
            ),
            "en": (
                f"The supply is derived from the minimum 7-day discharge of the {river} "
                f"under this drought: {fraction * 100:.0f} % of a normal year. That relation "
                f"has a correlation of {correlation:+.2f} - a drought in the polder and a low "
                "river flow only partly coincide"
            ),
        },
        {
            "nl": (
                f"Reken daarom met een band van {low:.2f} tot {high:.2f} maal dit volume in "
                f"plaats van met het getal.{where_nl} Twee dingen schuiven "
                "hem verder: de indicator is de DIEPSTE week, dus als index op een heel "
                "groeiseizoen valt hij aan de lage kant uit, en wat van de rivier bij jouw "
                "inlaat aankomt bepaalt de landelijke verdeling en niet dit model"
            ),
            "en": (
                f"So work with a band of {low:.2f} to {high:.2f} times this volume rather "
                f"than with the number.{where_en} Two things shift it further: "
                "the indicator is the DEEPEST week, so as an index over a whole growing "
                "season it comes out on the low side, and what of the river arrives at your "
                "intake is set by the national distribution and not by this model"
            ),
        },
    )


def _demand_posts_caveat(input, extra) -> "ModelCaveat | None":
    """De vraagkant van dit model is een van vier posten, en de kleinste.

    Gaat op elke droogtevraag af, want de smalte is een eigenschap van het model en niet van
    de aanroep. Staat er een regio uit de werkopgave bij, dan wordt hij concreet: dan noemt
    hij het aandeel dat deze doorrekening beslaat.

    Dragen de afnemers zelf een post, dan zitten de vier posten IN het antwoord en is deze
    tekst onwaar; dan blijft alleen de vraag staan waar hun categorie op rust, en die staat in
    `_demand_post_category_caveat`.
    """
    if not extra.get("is_drought") or extra.get("demand_posts_used"):
        return None
    shares = extra.get("demand_share")
    if shares:
        irrigation = (shares.get("beregening") or 0.0) * 100
        management = (shares.get("peilbeheer") or 0.0) * 100
        flushing = (
            (shares.get("doorspoeling_boezem") or 0.0)
            + (shares.get("doorspoeling_polders") or 0.0)
        ) * 100
        region = extra.get("demand_post_choice", {}).get("demand_region", "deze regio")
        what_nl = (
            f"In {region} is beregening {irrigation:.0f} % van de zomerse watervraag, "
            f"peilbeheer {management:.0f} % en doorspoeling {flushing:.0f} %. Dit antwoord "
            "gaat over de beregeningsvraag plus het deel van peilbeheer dat op het open "
            "water verdampt; doorspoeling zit er niet in"
        )
        what_en = (
            f"In {region} irrigation is {irrigation:.0f} % of the summer water demand, "
            f"level management {management:.0f} % and flushing {flushing:.0f} %. This answer "
            "covers the irrigation demand plus the part of level management that evaporates "
            "from the open water; flushing is not in it"
        )
    else:
        what_nl = (
            "De vraag in dit model is een verdampingstekort dat uit het oppervlaktewater "
            "wordt gedekt, en dat is de post beregening. Landelijk is dat 9 tot 19 % van de "
            "zomerse watervraag en in West 5 tot 9 %; peilbeheer en doorspoeling zijn samen "
            "de rest en zitten hier niet in"
        )
        what_en = (
            "The demand in this model is an evaporation deficit met from the surface water, "
            "and that is the irrigation post. Nationally that is 9 to 19 % of the summer "
            "water demand and in the west 5 to 9 %; level management and flushing together "
            "are the rest and are not in this model"
        )
    return _caveat(
        language_of(input),
        {"nl": "een van vier watervraagposten", "en": "one of four water demand posts"},
        {"nl": what_nl, "en": what_en},
        {
            "nl": (
                "Een maatregel die hier helpt, helpt dus aan de kleinste post. En een getal "
                "uit dit antwoord naast een getal uit de werkopgave leggen is geen "
                "vergelijking van twee metingen van hetzelfde: die rust op de "
                "Basisprognoses 2018 en daarmee op KNMI'14, waar dit model op KNMI'23 rust. "
                "Het tekort onder KNMI'23 is tot een factor 1,42 groter"
            ),
            "en": (
                "A measure that helps here therefore helps the smallest post. And a number "
                "from this answer next to a number from the national assessment is not two "
                "measurements of the same thing: that rests on the 2018 base projections and "
                "thus on KNMI'14, where this model rests on KNMI'23. The deficit under "
                "KNMI'23 is up to a factor 1.42 larger"
            ),
        },
    )


def _demand_share_resolution_caveat(input, extra) -> "ModelCaveat | None":
    """De aandelen van een kleine regio zijn grof, en dan zegt het tweede cijfer niets."""
    if not extra.get("demand_share_is_coarse"):
        return None
    step = (extra.get("demand_share_resolution") or 0.0) * 100
    return _caveat(
        language_of(input),
        {
            "nl": "de vraagverdeling van deze regio is grof",
            "en": "the demand split of this region is coarse",
        },
        {
            "nl": (
                f"De werkopgave is op hele miljoenen m3 afgerond, en deze regio is zo klein "
                f"dat elk aandeel daardoor in stappen van {step:.0f} procentpunt ligt"
            ),
            "en": (
                f"The national assessment is rounded to whole millions of m3, and this "
                f"region is small enough that each share therefore comes in steps of "
                f"{step:.0f} percentage points"
            ),
        },
        {
            "nl": (
                "Lees de verdeling hier als een orde van grootte en niet als een "
                "verhouding. Wil je er een vraag over verdelen, neem dan de bovenliggende "
                "regio"
            ),
            "en": (
                "Read the split here as an order of magnitude and not as a ratio. To "
                "distribute a demand over it, take the parent region"
            ),
        },
    )


def _demand_post_category_caveat(input, extra) -> "ModelCaveat | None":
    """De categorie per post is een verdedigbare toewijzing en geen wettelijke tabel."""
    used = extra.get("demand_posts_used")
    if not used:
        return None
    listed = ", ".join(used)
    return _caveat(
        language_of(input),
        {
            "nl": "de categorie per vraagpost is toegewezen",
            "en": "the category per demand post is an assignment",
        },
        {
            "nl": (
                f"Deze posten dragen een categorie uit de verdringingsreeks: {listed}. De "
                "wet noemt criteria en geen posten: categorie 1 is veiligheid en "
                "onomkeerbare schade, en peilhandhaving tegen uitdrogende keringen, "
                "veenoxidatie en verzilting van veen valt daaronder"
            ),
            "en": (
                f"These posts carry a category from the legal priority order: {listed}. The "
                "law names criteria and not posts: category 1 is safety and irreversible "
                "damage, and maintaining levels against drying dikes, peat oxidation and "
                "salinisation of peat falls under it"
            ),
        },
        {
            "nl": (
                "Waar de post een gebruiker dient in plaats van onomkeerbare schade tegen "
                "te houden, ligt de categorie anders: doorspoelen voor de waterkwaliteit van "
                "glastuinbouw is 3 of 4, en beregening van kapitaalintensieve gewassen is 3. "
                "Geef dan `category` op in plaats van `demand_post`"
            ),
            "en": (
                "Where the post serves a user instead of preventing irreversible damage, the "
                "category differs: flushing for the water quality of greenhouse horticulture "
                "is 3 or 4, and irrigation of capital-intensive crops is 3. Then give "
                "`category` instead of `demand_post`"
            ),
        },
    )


def _salinisation_caveat(input, extra) -> "ModelCaveat | None":
    """Bij schaarste is de volgende stap zouter inlaten, en dat kent dit model niet."""
    if not extra.get("salinisation_is_the_next_step"):
        return None
    return _caveat(
        language_of(input),
        {"nl": "verzilting zit er niet in", "en": "salinisation is not in the model"},
        {
            "nl": (
                "Dit model rekent in hoeveelheden water en kent geen chloride. Bij schaarste "
                "is de volgende stap in de praktijk niet minder inlaten maar ZOUTER inlaten, "
                "en dat is een andere beslissing met een andere schade"
            ),
            "en": (
                "This model works in quantities of water and knows no chloride. Under "
                "scarcity the next step in practice is not to draw in less but to draw in "
                "SALTIER water, and that is a different decision with different damage"
            ),
        },
        {
            "nl": (
                "Twee dingen volgen eruit. De inlaatcapaciteit van een verziltende polder is "
                "gedimensioneerd op doorspoeling en dus op waterkwaliteit - landelijk 32 tot "
                "46 % van de zomerse watervraag - dus een capaciteit die hier volstaat kan "
                "voor de kwaliteitsopgave te klein zijn. En verzilting van een veenpakket is "
                "onomkeerbaar, dus doorspoelen ertegen staat in categorie 1 van de "
                "verdringingsreeks en niet bij de landbouw"
            ),
            "en": (
                "Two things follow. The intake capacity of a salinising polder is sized on "
                "flushing and therefore on water quality - nationally 32 to 46 % of the "
                "summer water demand - so a capacity that suffices here may be too small for "
                "the quality task. And salinisation of a peat layer is irreversible, so "
                "flushing against it sits in category 1 of the legal priority order and not "
                "with agriculture"
            ),
        },
    )


def _storage_is_full_at_the_start_caveat(input, extra) -> "ModelCaveat | None":
    """De voorraad staat vol bij het begin, en hem vullen kost bronwater.

    Dit is de kanttekening die in de plaats komt van een tijd-as. Vullen tijdens de droogte
    haalt water uit dezelfde bron die de rest van de selectie ook aanspreekt, en of dat water
    er op dat moment nog is, is een vraag die dit model niet stelt.
    """
    if not extra.get("storage_m3"):
        return None
    days = extra.get("days_of_shortfall_covered")
    bought = (
        f" Deze voorraad dekt het tekort van {days:.1f} dagen."
        if days is not None
        else ""
    )
    bought_en = (
        f" This store covers {days:.1f} days of the shortfall."
        if days is not None
        else ""
    )
    return _caveat(
        language_of(input),
        {
            "nl": "de voorraad staat vol bij het begin",
            "en": "the store is full at the start",
        },
        {
            "nl": (
                f"De {extra['storage_m3'] / 1e6:.2f} miljoen m3 voorraad in deze selectie is "
                "vol veronderstéld op de eerste dag van de periode, alsof hij in een nattere "
                f"tijd is gevuld.{bought}"
            ),
            "en": (
                f"The {extra['storage_m3'] / 1e6:.2f} million m3 of storage in this selection "
                "is assumed FULL on the first day of the period, as if it had been filled in "
                f"a wetter time.{bought_en}"
            ),
        },
        {
            "nl": (
                "Hem tijdens de droogte vullen kost water uit dezelfde bron die de rest van "
                "de selectie aanspreekt, en dat is hier niet meegerekend - dit antwoord is "
                "daarmee te gunstig. Wanneer je moet vullen en of het water er dan nog is, "
                "zegt dit model niet: daarvoor is een verloop binnen het seizoen nodig en de "
                "statistiek geeft één getal per seizoen"
            ),
            "en": (
                "Filling it during the drought costs water from the same source the rest of "
                "the selection draws on, and that is not counted here - so this answer is too "
                "favourable. When to fill, and whether the water is still there by then, this "
                "model does not say: that needs a profile within the season and the statistic "
                "gives one number per season"
            ),
        },
    )


def _storage_place_caveat(input, extra) -> "ModelCaveat | None":
    """Waar het gedeelde water in het model terechtkomt, en waar het exact is.

    Alleen wanneer er voorraad wordt GEDEELD - een gebied dat zijn eigen voorraad opmaakt,
    deelt niets en heeft deze kanttekening niet nodig.
    """
    if not extra.get("storage_shared_m3"):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "de plaats van het gedeelde water",
            "en": "where the shared water sits",
        },
        {
            "nl": (
                f"De {extra['storage_shared_m3'] / 1e6:.2f} miljoen m3 die gebieden zonder "
                "eigen vraag inbrengen, komt bij het bronvolume van de hele selectie. Dit "
                "model weet niet welke afnemer er fysiek achter ligt"
            ),
            "en": (
                f"The {extra['storage_shared_m3'] / 1e6:.2f} million m3 contributed by areas "
                "without demand of their own is added to the source volume of the whole "
                "selection. This model does not know which consumer physically sits behind it"
            ),
        },
        {
            "nl": (
                "Dat is EXACT zolang er één boezem is waar iedereen achter hangt, en TE "
                "GUNSTIG bij parallelle takken: een berging in de ene tak helpt in het model "
                "dan ook de andere. Deel de selectie in dat geval per tak op"
            ),
            "en": (
                "That is EXACT as long as there is one main channel everyone sits behind, and "
                "TOO FAVOURABLE with parallel branches: storage in one branch then also helps "
                "the other in this model. In that case split the selection per branch"
            ),
        },
    )


def _no_groundwater_caveat(input, extra) -> "ModelCaveat | None":
    """De voorraad is het open water - zolang de bodem er niet bij is gezet.

    Zodra de beller een bodemvoorraad opgeeft is deze tekst onwaar, en neemt
    `_soil_store_caveat` het over met wat er dan nog niet in zit.
    """
    if not extra.get("is_drought") or extra.get("soil_store_is_modelled"):
        return None
    return _caveat(
        language_of(input),
        {"nl": "alleen oppervlaktewater", "en": "surface water only"},
        {
            "nl": (
                "De voorraad in dit model is de berging onder het streefpeil in het open "
                "water. Bodemvocht, grondwater en overdracht van winter naar zomer zitten "
                "er niet in"
            ),
            "en": (
                "The store in this model is the storage below the target level in the open "
                "water. Soil moisture, groundwater and carry-over from winter to summer are "
                "not in it"
            ),
        },
        {
            "nl": (
                "Water vasthouden in de bodem - sponswerking - is daarmee niet te "
                "waarderen, terwijl dat voor gebieden met weinig open water juist de "
                "belangrijkste maatregel is. Voor die gebieden is dit antwoord een "
                "ondergrens op wat er mogelijk is"
            ),
            "en": (
                "Retaining water in the soil - the sponge effect - therefore cannot be "
                "valued, while for areas with little open water that is precisely the most "
                "important measure. For those areas this answer is a lower bound on what is "
                "possible"
            ),
        },
    )


def _soil_store_caveat(input, extra) -> "ModelCaveat | None":
    """Wat de bodemvoorraad wel en niet hard maakt.

    Neemt het over van `_no_groundwater_caveat`: de bodem zit nu IN het antwoord, en wat er
    overblijft is dat de getallen indicatief zijn en dat het plafond niet meebeweegt met de
    droogte.
    """
    if not extra.get("soil_store_is_modelled"):
        return None
    from_table = extra.get("soil_type")
    origin_nl = (
        f"De voorraad en het plafond komen uit het gebiedstype {from_table!r} en zijn "
        "afgeleid uit een bergingscoefficient, een toegestane zakking, een "
        "infiltratieweerstand en de kritieke opstijghoogte"
        if from_table
        else (
            "De voorraad en het plafond zijn opgegeven in deze aanroep en komen niet uit een "
            "gebiedstype"
        )
    )
    origin_en = (
        f"The store and the ceiling come from area type {from_table!r} and are derived from a "
        "storage coefficient, an allowed drawdown, an infiltration resistance and the "
        "critical capillary rise height"
        if from_table
        else (
            "The store and the ceiling were supplied in this call and do not come from an "
            "area type"
        )
    )
    return _caveat(
        language_of(input),
        {
            "nl": "de bodemvoorraad is indicatief en zijn plafond staat stil",
            "en": "the soil store is indicative and its ceiling is constant",
        },
        {
            "nl": (
                f"{origin_nl}. Die afleiding is niet aan veldmetingen getoetst, en hoe "
                "zelfvoorzienend gebieden werkelijk zijn wordt niet gemonitord - elk getal "
                "hierover is dus een modeluitspraak zonder veldreferentie"
            ),
            "en": (
                f"{origin_en}. That derivation has not been tested against field "
                "measurements, and how self-sufficient areas really are is not monitored - "
                "so any number about this is a model statement without a field reference"
            ),
        },
        {
            "nl": (
                "Twee dingen om mee te wegen. Het plafond geldt voor de route DOOR de bodem, "
                "dus voor infiltratie uit de sloot en capillaire opstijging; beregening die "
                "water rechtstreeks uit de watergang op het gewas brengt loopt daar niet "
                "door, en voor die vraag is dit antwoord te streng. En het plafond loopt in "
                "werkelijkheid terug naarmate het grondwater zakt - hoe dieper de stand, hoe "
                "minder er capillair naar boven komt - terwijl het hier een constante is, dus "
                "aan het eind van een lange droogte is het antwoord te gunstig. De maatregel "
                "die het plafond verhoogt, onderwaterdrainage of subirrigatie, kost zelf "
                "water; die post staat in `priceless`"
            ),
            "en": (
                "Two things to weigh. The ceiling applies to the route THROUGH the soil, so "
                "to infiltration from the ditch and capillary rise; sprinkler irrigation that "
                "takes water straight from the watercourse onto the crop does not pass "
                "through it, and for that demand this answer is too strict. And in reality "
                "the ceiling falls as the groundwater drops - the deeper the level, the less "
                "rises capillary - while here it is a constant, so at the tail of a long "
                "drought the answer is too favourable. The measure that raises the ceiling, "
                "submerged drainage or subirrigation, costs water itself; that post is in "
                "`priceless`"
            ),
        },
    )


def _coupling_law_caveat(input, extra) -> "ModelCaveat | None":
    """De koppelingswet is een open vraag en het cascade-effect hangt eraan.

    Staat apart van de andere caveats omdat hij alleen op systeemschaal bestaat: bij een
    losse polder is er geen benedenstroomse stand die iets blokkeert.
    """
    if not extra.get("coupling_law"):
        return None
    return _caveat(
        language_of(input),
        {"nl": "koppelingswet tussen gebieden", "en": "coupling law between areas"},
        {
            "nl": (
                "De capaciteit neemt lineair af met de benedenstroomse stand. Of "
                "waterschappen een poldergemaal zo modelleren of met een uitschakelpeil, en "
                "met welke waarden, is een open vraag"
            ),
            "en": (
                "Capacity falls off linearly with the downstream level. Whether water "
                "authorities model a polder pump this way or with a cut-out level, and with "
                "which values, is an open question"
            ),
        },
        {
            "nl": (
                "De grootte van het cascade-effect hangt hieraan. De richting niet: op een "
                "gemeten ketting draait de rangorde van de maatregelen om zodra de "
                "opvoerhoogte onder ongeveer 5 m komt, en dat is de hele plausibele band "
                "voor een poldergemaal. Wat wel schuift is hoeveel het scheelt"
            ),
            "en": (
                "The size of the cascade effect hangs on this. The direction does not: on a "
                "measured chain the ranking of the measures flips as soon as the head drops "
                "below roughly 5 m, and that is the whole plausible band for a polder pump. "
                "What does move is how much it matters"
            ),
        },
    )


def _allocation_rule_caveat(input, extra) -> "ModelCaveat | None":
    """De regel binnen een categorie is een keuze, en de wet noemt een andere.

    Staat apart omdat hij alleen bij een verdelingsvraag bestaat: bij een losse aanvoervraag
    is er niets te verdelen, en dan is er ook geen regel om over te beslissen.
    """
    rule = extra.get("allocation_rule")
    if not rule:
        return None
    return _caveat(
        language_of(input),
        {"nl": "verdeling binnen een categorie", "en": "sharing within a category"},
        {
            "nl": (
                "De wettelijke verdringingsreeks (art. 3.14 Bkl) ordent de vier "
                "categorieen, en noemt binnen categorie 3 en 4 minimalisatie van de "
                "economische maatschappelijke schade als criterium. Dit model verdeelt "
                f"binnen een categorie {rule!r} - bij 'proportional' krijgt iedereen "
                "dezelfde dekkingsfractie"
            ),
            "en": (
                "The Dutch legal priority order (art. 3.14 Bkl) ranks the four categories, "
                "and within categories 3 and 4 names minimising economic and societal "
                f"damage as the criterion. This model shares within a category {rule!r} - "
                "under 'proportional' everyone gets the same coverage fraction"
            ),
        },
        {
            "nl": (
                "Dat is een proxy en niet het wettelijke criterium: zodra de schadefuncties "
                "per afnemer verschillen, wijkt gelijk verdelen daarvan af. De ORDENING "
                "tussen de categorieen is wel de wettelijke, en die is bindend - tussen "
                "categorie 3 en 4 is nadere prioritering niet mogelijk. Gebruik de verdeling "
                "binnen een schil dus als bandbreedte en niet als voorschrift"
            ),
            "en": (
                "That is a proxy and not the legal criterion: as soon as damage functions "
                "differ between consumers, equal sharing departs from it. The ORDER between "
                "the categories is the legal one and is binding - between categories 3 and 4 "
                "further prioritisation is not possible. So use the sharing within a shell "
                "as a range and not as a prescription"
            ),
        },
    )


def _allocation_source_caveat(input, extra) -> "ModelCaveat | None":
    """Waar het bronvolume vandaan komt, zit niet in dit model.

    Tenzij het uit de droogtestatistiek komt; dan neemt `_supply_source_statistic_caveat`
    het over, om dezelfde reden als bij aanvoeren.
    """
    if not extra.get("source_volume_given") or extra.get(
        "source_volume_from_statistic"
    ):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "herkomst van het bronvolume",
            "en": "where the source volume comes from",
        },
        {
            "nl": (
                "Het beschikbare volume is hier een INVOER. Hoe het tot stand komt - de "
                "landelijke waterverdeling, het Distributiemodel, de afvoer van de Rijn - "
                "zit niet in dit model"
            ),
            "en": (
                "The available volume is an INPUT here. How it comes about - the national "
                "water distribution, the Distribution Model, the discharge of the Rhine - is "
                "not in this model"
            ),
        },
        {
            "nl": (
                "Dit antwoord is dus voorwaardelijk: 'als er zoveel is, dan valt dit af'. "
                "Het is geen voorspelling van hoeveel er zal zijn. De trap in `theta_steps` "
                "is daarom bruikbaarder dan het ene getal: die laat zien vanaf welk aanbod "
                "het antwoord verandert, zonder dat er een aanbod voorspeld hoeft te worden. "
                "Lees een trede wel als een bereik - `coverage_at_low` tot "
                "`coverage_at_high` - en niet als een enkel getal"
            ),
            "en": (
                "This answer is therefore conditional: 'if there is this much, this is what "
                "falls short'. It is not a prediction of how much there will be. The "
                "staircase in `theta_steps` is more useful than the single number: it shows "
                "from which supply the answer changes, without anyone having to predict a "
                "supply. Do read a step as a range - `coverage_at_low` to `coverage_at_high` "
                "- and not as a single number"
            ),
        },
    )


def _raised_datum_caveat(input, extra) -> "ModelCaveat | None":
    """Peilopzet in een cascade telt in de stijging, maar niet in de opvoerhoogte."""
    nodes = getattr(input, "nodes", None) or []
    if not any(getattr(node, "target_level_rise_m", 0.0) for node in nodes):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "peilopzet en de koppeling tussen gebieden",
            "en": "a raised target level and the coupling between areas",
        },
        {
            "nl": (
                "De peilopzet van een gebied telt mee in de gerapporteerde stijging, want "
                "die wordt boven het oorspronkelijke peil gemeten. Wat het model NIET doet "
                "is de opvoerhoogte tussen twee gebieden aanpassen: een gebied dat 20 cm "
                "hoger staat pompt in werkelijkheid tegen 20 cm minder verval naar zijn "
                "benedenstrooms gebied, en dat verschil in nulpunt zit niet in de "
                "doorrekening"
            ),
            "en": (
                "An area's raised target level counts towards the reported rise, because "
                "that is measured above the original level. What the model does NOT do is "
                "adjust the head between two areas: an area standing 20 cm higher really "
                "pumps against 20 cm less head towards its downstream area, and that "
                "difference in datum is not in the computation"
            ),
        },
        {
            "nl": (
                "Het gemaal van een opgezet gebied wordt hier dus iets te pessimistisch "
                "gerekend zolang `head_max_m` is opgegeven. Bij een peilonafhankelijk gemaal "
                "maakt het niets uit, want dan speelt de opvoerhoogte geen rol"
            ),
            "en": (
                "The pump of a raised area is therefore computed slightly too "
                "pessimistically as long as `head_max_m` is given. For a head-independent "
                "pump it makes no difference, because then the head plays no role"
            ),
        },
    )


def _drought_statistic_caveat(input, extra) -> "ModelCaveat | None":
    """Wat een gekozen droogte uit STOWA 2025-23 wel en niet zegt.

    Gaat alleen af als de beller de statistiek heeft gebruikt; wie zijn tekort zelf opgeeft
    heeft deze twee grenzen niet, want dan is er geen karakteristiek jaar in het spel.
    """
    chosen = extra.get("drought_statistic")
    if not chosen:
        return None
    total = extra.get("cumulative_deficit_mm")
    period = chosen["drought_return_period"]
    # Twee vensters en niet een. `window_days` is het accumulatievenster van de STATISTIEK
    # en ligt vast op het groeiseizoen; `concentrated_over_days` is `length_days`, de keuze
    # van de aanroeper. Onder een naam levert dat bij `length_days: 90` de zin "uitgesmeerd
    # over 90 dagen. Dat venster is 1 april tot 1 oktober" op, die zichzelf tegenspreekt.
    window = extra.get("window_days")
    chosen_days = extra.get("concentrated_over_days", window)
    return _caveat(
        language_of(input),
        {"nl": "de gekozen droogte", "en": "the drought that was chosen"},
        {
            "nl": (
                f"Het tekort komt uit de statistiek: {total:.0f} mm bij een herhaaltijd van "
                f"{period} jaar, opgeteld over het groeiseizoen: een venster van {window} "
                f"dagen, 1 april tot 1 oktober. Hier is dat volume uitgesmeerd over "
                f"{chosen_days} dagen, en dat "
                "is een keuze van de aanroep en geen eigenschap van de bron. Het maximum "
                "wordt in de meeste jaren voor 1 oktober bereikt, dus het tekort per dag komt "
                "over het volle venster aan de milde kant uit"
            ),
            "en": (
                f"The deficit comes from the statistic: {total:.0f} mm at a return period of "
                f"{period} years, accumulated over the {window}-day growing season - 1 April "
                f"to 1 October. Here that volume is spread over {chosen_days} days, which is a "
                "choice made in the call and not a property of the source. In most years the "
                "maximum is reached before 1 October, so over the full window the deficit per "
                "day comes out at the mild end"
            ),
        },
        {
            "nl": (
                "Wil je het scherper, zet `length_days` dan korter; hetzelfde volume over "
                "minder dagen vraagt meer inlaatcapaciteit. En boven ongeveer T5 "
                "vertegenwoordigt een karakteristiek jaar niet alle droogte-indicatoren "
                "tegelijk, dus noem de herhaaltijd erbij en doe niet alsof dit hét droge "
                "jaar is"
            ),
            "en": (
                "For a sharper answer, set `length_days` shorter; the same volume over "
                "fewer days asks for more intake capacity. And above roughly T5 a single "
                "characteristic year does not represent all drought indicators at once, so "
                "name the return period and do not present this as THE dry year"
            ),
        },
    )


def _racmo_caveat(input, extra) -> "ModelCaveat | None":
    """De reeksen achter de droogtestatistiek zijn gesimuleerd en niet gemeten."""
    if not extra.get("drought_statistic"):
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "herkomst van de droogtereeks",
            "en": "where the drought record comes from",
        },
        {
            "nl": (
                "De statistiek is gefit op RACMO-klimaatreeksen: gesimuleerde jaren en geen "
                "gemeten geschiedenis. Een scenario is een consistent klimaat en geen "
                "voorspelling van een specifiek jaar"
            ),
            "en": (
                "The statistic is fitted on RACMO climate runs: simulated years and not a "
                "measured history. A scenario is a consistent climate and not a prediction "
                "of any particular year"
            ),
        },
        {
            "nl": (
                "Het verschil tussen twee jaren in zo'n reeks is weersvariatie en geen "
                "klimaatverandering; dat verschil zit tussen de SCENARIO's. Vergelijk dus "
                "'Referentie' met 'Hd_2050' en niet twee jaren binnen een scenario"
            ),
            "en": (
                "The difference between two years within such a run is weather variability "
                "and not climate change; that difference sits between the SCENARIOS. So "
                "compare 'Referentie' with 'Hd_2050' rather than two years within one"
            ),
        },
    )


PLAUSIBLE_RISE_M = 1.0
"""Boven deze stijging is de lineaire berging geen goede beschrijving meer [m].

De waterbalans rekent met een VAST open-wateroppervlak: elke kuub verhoogt de stand met
dezelfde centimeters. Dat klopt zolang het water in de watergang blijft. Zodra het over de
kant komt spreidt het zich over het land, groeit het bergende oppervlak met een orde, en
stijgt de stand veel langzamer dan dit model zegt.

Een meter is de ordegrootte waarop dat gebeurt: `delta_h_available` beschrijft de
drooglegging tot het laagste te beschermen perceel en noemt 0,2 tot 1,0 m als bandbreedte.
Daarboven staat het maaiveld al onder water en is de vraag niet meer "hoe hoog komt het"
maar "hoeveel land loopt onder".
"""


def _implausible_rise_caveat(input, extra) -> "ModelCaveat | None":
    """Een stijging die het model niet meer kan dragen, benoemd in plaats van gemeld.

    De systeemtools hebben bewust geen `status`-veld - er is geen maatvoering om haalbaar of
    onhaalbaar te noemen - en `converged` zegt alleen iets over de numeriek. Zonder deze
    regel is er dus niets dat een stijging van bijna vijf meter kán markeren, en komt die er
    even stellig uit als dertien centimeter.

    Een caveat en geen vlag, want dat is in dit systeem de vorm voor "hier houdt het model
    op". Hij zegt ook welke kant het op staat: een bovengrens, want spreiding over het land
    verlaagt de werkelijke stand.
    """
    rise = extra.get("worst_rise_m")
    if rise is None or rise <= PLAUSIBLE_RISE_M:
        return None
    return _caveat(
        language_of(input),
        {
            "nl": "de stijging valt buiten het bereik van het model",
            "en": "the rise falls outside the range of the model",
        },
        {
            "nl": (
                f"Er komt {rise * 100:.0f} cm stijging uit, en de waterbalans rekent met een "
                "vast open-wateroppervlak. Boven ongeveer een meter komt het water over de "
                "kant, spreidt het zich over het land en groeit het bergende oppervlak met "
                "een orde - dat zit hier niet in, net zomin als overstorten, inundatie van "
                "percelen of een gemaal dat afslaat"
            ),
            "en": (
                f"The computed rise is {rise * 100:.0f} cm, and the water balance uses a "
                "fixed open-water area. Above roughly one metre the water leaves the "
                "watercourse, spreads across the land and the storing area grows by an order "
                "of magnitude - that is not in this model, and neither are overflows, "
                "inundation of parcels or a pump that cuts out"
            ),
        },
        {
            "nl": (
                "Lees dit getal daarom als een BOVENGRENS en niet als een voorspelling: in "
                "werkelijkheid komt de stand lager uit doordat het land meebergt. Wat het "
                "wel zegt is dat het hier niet past - de vraag verschuift van 'hoe hoog "
                "komt het' naar 'hoeveel land loopt onder', en die beantwoordt dit model "
                "niet"
            ),
            "en": (
                "So read this number as an UPPER BOUND and not as a prediction: in reality "
                "the level comes out lower because the land stores water too. What it does "
                "tell you is that it does not fit here - the question shifts from 'how high "
                "does it get' to 'how much land floods', and this model does not answer that "
                "one"
            ),
        },
    )


def _own_storm_caveat(input, extra) -> "ModelCaveat | None":
    """De bui komt van de beller en niet uit de statistiek, en dat hoort in het antwoord.

    Een opgezochte bui draagt een herhaaltijd: je kunt zeggen hoe zeldzaam hij is en waar
    dat vandaan komt. Een opgegeven som draagt dat niet, terwijl het antwoord er verder
    identiek uitziet - zelfde velden, zelfde stelligheid. Deze regel is wat die twee uit
    elkaar houdt.
    """
    volume = getattr(input, "rain_volume_mm", None)
    if volume is None:
        return None
    return _caveat(
        language_of(input),
        {"nl": "de bui is opgegeven", "en": "the event was supplied"},
        {
            "nl": (
                f"De neerslagsom van {volume:g} mm komt uit deze aanroep en niet uit de "
                "STOWA-statistiek. Er hoort dus geen herhaaltijd bij: dit antwoord zegt "
                "wat er bij deze bui gebeurt, niet hoe zeldzaam die bui is"
            ),
            "en": (
                f"The rainfall total of {volume:g} mm comes from this call and not from "
                "the STOWA statistic. There is therefore no return period attached: this "
                "answer says what happens in this event, not how rare that event is"
            ),
        },
        {
            "nl": (
                "Noem de herkomst als je dit doorgeeft. Wil je de zeldzaamheid er wel bij, "
                "gebruik dan `return_period` in plaats van `rain_volume_mm`; ter ijking "
                "geeft de statistiek voor 96 uur in de zomer 59 mm bij T10 en 87 mm bij "
                "T100. De vorm van de bui en het neerslagverlies komen hoe dan ook uit het "
                "model en niet uit jouw getal"
            ),
            "en": (
                "Name that origin when you pass this on. If you do want the rarity, use "
                "`return_period` instead of `rain_volume_mm`; for calibration the statistic "
                "gives 59 mm at T10 and 87 mm at T100 for a 96-hour summer event. The shape "
                "of the event and the rainfall loss come from the model either way, not "
                "from your number"
            ),
        },
    )


def _own_deficit_caveat(input, extra) -> "ModelCaveat | None":
    """De droge tegenhanger: het tekort komt van de beller en niet uit de statistiek.

    Dezelfde stilte als bij een opgegeven bui, en dus dezelfde melding. Gaat niet af zodra
    er een droogte is gekozen; dan staat de herkomst al in `data.drought_statistic` en
    schrijft `_drought_statistic_caveat` op wat die keuze betekent.
    """
    if not extra.get("is_drought") or extra.get("drought_statistic"):
        return None
    deficit = getattr(input, "deficit_mm_per_day", None)
    if deficit is None:
        return None
    return _caveat(
        language_of(input),
        {"nl": "het tekort is opgegeven", "en": "the deficit was supplied"},
        {
            "nl": (
                f"Het neerslagtekort van {deficit:g} mm/dag komt uit deze aanroep en niet "
                "uit de droogtestatistiek. Er hoort dus geen herhaaltijd bij: dit antwoord "
                "zegt wat er bij deze droogte gebeurt, niet hoe zeldzaam die droogte is"
            ),
            "en": (
                f"The deficit of {deficit:g} mm/day comes from this call and not from the "
                "drought statistic. There is therefore no return period attached: this "
                "answer says what happens in this drought, not how rare that drought is"
            ),
        },
        {
            "nl": (
                "Noem de herkomst als je dit doorgeeft. Wil je de zeldzaamheid er wel bij, "
                "kies dan een droogte met `drought_region`, `drought_scenario` en "
                "`drought_return_period`; het tekort komt dan uit STOWA 2025-23 en zakt mee "
                "met het klimaatscenario"
            ),
            "en": (
                "Name that origin when you pass this on. If you do want the rarity, choose "
                "a drought with `drought_region`, `drought_scenario` and "
                "`drought_return_period`; the deficit then comes from STOWA 2025-23 and "
                "moves with the climate scenario"
            ),
        },
    )


CAVEAT_RULES = (
    _drought_statistic_caveat,
    _racmo_caveat,
    _allocation_rule_caveat,
    _allocation_source_caveat,
    _summer_loss_caveat,
    _event_length_caveat,
    _return_period_caveat,
    _cost_caveat,
    _supply_availability_caveat,
    _supply_source_origin_caveat,
    _supply_source_statistic_caveat,
    _demand_posts_caveat,
    _demand_share_resolution_caveat,
    _demand_post_category_caveat,
    _storage_is_full_at_the_start_caveat,
    _storage_place_caveat,
    _salinisation_caveat,
    _no_groundwater_caveat,
    _soil_store_caveat,
    _coupling_law_caveat,
    _raised_datum_caveat,
    _implausible_rise_caveat,
    _own_storm_caveat,
    _own_deficit_caveat,
)
"""De caveats, als lijst van regels die zelf beslissen of ze van toepassing zijn.

Een allowlist en geen scan: elke regel is een keuze dat déze beperking het antwoord genoeg
stuurt om te melden. Een nieuwe regel dwingt die keuze opnieuw af.
"""


def model_caveats(input, **extra) -> list[ModelCaveat]:
    """De structurele beperkingen die op dit antwoord van toepassing zijn."""
    found = (rule(input, extra) for rule in CAVEAT_RULES)
    return [caveat for caveat in found if caveat is not None]
