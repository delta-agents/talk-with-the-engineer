"""Prijsloze posten: geen bedrag, wel een prijs.

Peilopzet kost drooglegging en aanvoeren kost verdringing. Een post zonder bedrag stil
weglaten maakt een pakket goedkoper dan het is; deze laag zorgt dat hij naast de prijs
komt te staan in plaats van erin te verdwijnen.

De regels kijken naar INVOERvelden, net als `CAVEAT_RULES`.
"""

# --- prijsloze posten: geen bedrag, wel een prijs -----------------------------------
#
# Peilopzet, peilmarge en aanvoeren kosten geen aanleg. Ze stonden daarom niet in `cost`,
# en er stond ook niets anders over ze in het antwoord - terwijl `read_me` belooft dat ze
# in `priceless` staan en niet op nul.
#
# Dat gemis is niet cosmetisch. Een peilmarge van 30 cm verlaagt op de referentiecasus
# (4000 ha, 3,5 % open water, gemaal 5 m3/s) de
# benodigde berging van 68 naar 38 ha en de kosten van 9,2 naar 5,1 miljoen euro. Een
# maatregel die de kosten zichtbaar verlaagt en niets zichtbaars verhoogt, leest als
# gratis winst; wat hij werkelijk kost is marge tot inundatie en bedrijfsvoering, en dat
# staat nergens in een getal omdat het geen getal IS.
#
# Dus geen bedrag maar een benoeming. Zelfde vorm als `CAVEAT_RULES`: een allowlist van
# regels die zelf beslissen of ze van toepassing zijn, zodat een beller alleen ziet wat
# hier geldt.


def _is_drought_input(input) -> bool:
    """Een droogte-invoer herken je aan `drawdown_available_m`.

    Die is daar de HELE peilband die je inzet, en de aanvoertools zetten hem dan ook als
    `level_margin_m` op de toestand. Een apart veld voor peilopzet kennen ze niet - een post
    daarover zou een prijs melden naast de post die diezelfde centimeters al noemt.
    """
    return getattr(input, "drawdown_available_m", None) is not None


def _target_level_rise_post(input, measure_nl):
    if _is_drought_input(input):
        return None
    rise = getattr(input, "target_level_rise_m", 0.0) or 0.0
    if not rise:
        return None
    return dict(
        topic="peilopzet",
        magnitude=f"{rise * 100:.0f} cm",
        what_it_costs="Drooglegging: een hoger streefpeil betekent landbouwschade en functiebeperking, "
        "en dat is een verdringingsvraagstuk en geen investeringspost. In dit antwoord "
        "betaal je hem bovendien al in de waterstand - de opzet telt mee in de gerapporteerde "
        "stijging, dus elke centimeter opzet is een centimeter minder marge tot inundatie.",
    )


def _level_margin_post(input, measure_nl):
    """De peilband onder het streefpeil, hoe de tool hem ook noemt.

    Op de natte kant heet hij `level_margin_m` en is hij de afspraak die voorbemaling
    mogelijk maakt; op de droge kant heet hij `drawdown_available_m` en is hij de buffer
    die je leegtrekt. Dat is dezelfde centimeter en dezelfde niet-monetaire prijs.
    """
    if _is_drought_input(input):
        margin = input.drawdown_available_m
        name = "drawdown_available_m"
    else:
        margin = getattr(input, "level_margin_m", 0.0) or 0.0
        name = "peilmarge"
    if not margin:
        return None
    if name == "peilmarge":
        # De natte lezing: het gemaal maalt vooruit, en het systeem daarachter is zelf een
        # investering. Wie de marge als gegeven opgeeft, hoort beide te zien.
        what_it_costs = (
            "Bedrijfsvoering en drooglegging: het gemaal maalt vooruit op een bui die "
            "nog niet is gevallen, en zolang het peil uitgezakt staat draagt het gebied "
            "de diepere drooglegging. Deze prijs heeft geen bedrag, maar de marge "
            "verlaagt het gemelde bedrag wel - noem deze post dus mee, anders leest de "
            "marge als gratis winst. En voorbemalen veronderstelt sturing - telemetrie, "
            "automatisering en protocollen - een investering die hier evenmin geprijsd is."
        )
    else:
        # De droge lezing van dezelfde centimeters: een buffer die je leegtrekt.
        what_it_costs = (
            "Voorraad en drooglegging: elke centimeter die je leegtrekt is zomervoorraad "
            "die op is zodra hij is gebruikt, en zolang het peil uitgezakt staat draagt "
            "het gebied de diepere drooglegging. Deze prijs heeft geen bedrag, maar hij "
            "bepaalt het antwoord wel - noem deze post mee."
        )
    return dict(
        topic="peilmarge"
        if name == "peilmarge"
        else "bruikbare diepte onder streefpeil",
        magnitude=f"{margin * 100:.0f} cm",
        what_it_costs=what_it_costs,
    )


def _supply_post(input, measure_nl):
    if measure_nl != "aanvoeren":
        return None
    return dict(
        topic="aanvoeren",
        magnitude="de inlaat",
        what_it_costs="Het water, niet het kunstwerk. Wat aanvoer in een tekort kost is een "
        "verdelingsvraag - de verdringingsreeks rantsoeneert landelijk - en de "
        "aanvoercapaciteit van een verziltende polder wordt bovendien gedimensioneerd op "
        "doorspoeling en dus op waterkwaliteit. Een bedrag verzinnen zou hier erger zijn "
        "dan geen bedrag.",
    )


def _level_water_post(input, measure_nl):
    """Peilopzet kost ook water, en in een droog jaar is dat het schaarse goed.

    Twee prijzen op dezelfde centimeters, en beide zijn waar. `_target_level_rise_post` en
    `_level_margin_post` noemen de drooglegging; deze noemt het water. Een hoger peil
    handhaven vraagt aanvoer, want het verdampt en infiltreert weg - in veenweidegebieden
    ongeveer 4 % meer watervraag voor peilbeheer. Bij ons koopt peilopzet voorraad; in de
    landelijke werkopgave is hij een vraagpost.
    """
    if _is_drought_input(input):
        depth = input.drawdown_available_m
        if not depth:
            return None
        return dict(
            topic="water voor peilhandhaving",
            magnitude=f"{depth * 100:.0f} cm",
            what_it_costs="Water. Voor zover deze diepte peilopzet is, is die opzet niet alleen berging "
            "maar ook vraag: een verhoogd peil moet worden aangevuld omdat het verdampt en "
            "infiltreert, in veenweidegebieden met ongeveer 4 % meer watervraag voor "
            "peilbeheer. Dit antwoord telt de voorraad die de opzet oplevert en niet het "
            "water dat het handhaven ervan kost, en in een droog jaar is dat precies het "
            "schaarse goed.",
        )
    rise = getattr(input, "target_level_rise_m", 0.0) or 0.0
    if not rise:
        return None
    return dict(
        topic="water voor peilhandhaving",
        magnitude=f"{rise * 100:.0f} cm",
        what_it_costs="Water. Een verhoogd streefpeil moet worden aangevuld omdat het verdampt en "
        "infiltreert, in veenweidegebieden met ongeveer 4 % meer watervraag voor peilbeheer. "
        "Dat is de zomerse tegenrekening van de winterse berging die deze opzet oplevert, en "
        "hij staat in geen van beide antwoorden in een getal.",
    )


def _soil_measure_post(input, measure_nl):
    """De maatregel die de bodemvoorraad bereikbaar maakt, kost water.

    Zonder onderwaterdrainage of subirrigatie is de weerstand tussen sloot en bodem precies
    het plafond dat het antwoord meldt. Die maatregel verhoogt het plafond en vraagt zelf 6
    tot 77 mm per jaar aan extra infiltratie, afhankelijk van het gebied. Zet dat naast de
    voorraad die hij ontsluit - in veenweide 5,8 mm - dan kan de maatregel meer water vragen
    dan de voorraad die hij vrijmaakt.
    """
    store = getattr(input, "soil_store_mm", None)
    if not store:
        return None
    return dict(
        topic="de bodemvoorraad bereikbaar maken",
        magnitude=f"{store:.1f} mm voorraad",
        what_it_costs="Water, en in veen bovendien bodem. Het plafond in dit antwoord hoort bij de "
        "weerstand die er nu is; hoger komt hij met onderwaterdrainage of subirrigatie, en "
        "die vragen 6 tot 77 mm per jaar aan extra infiltratie. Dat kan meer zijn dan de "
        "voorraad die ze ontsluiten. In een droog jaar wordt de onttrekking via peilgestuurde "
        "drainage bovendien zelf gerantsoeneerd, en grondwaterstandsdaling in veen is "
        "onomkeerbaar: dat kost maaiveld.",
    )


PRICELESS_RULES = (
    _target_level_rise_post,
    _level_margin_post,
    _level_water_post,
    _soil_measure_post,
    _supply_post,
)


def priceless_posts(input, measure_nl: str | None = None) -> list:
    """De posten in dit antwoord die geen bedrag hebben maar wel een prijs.

    Levert dicts en geen `PricelessPost`, want die woont in `results.py` en dat bestand
    importeert dit bestand al. De regels horen hier omdat ze naar INVOERvelden kijken, net
    als `CAVEAT_RULES`.
    """
    found = (rule(input, measure_nl) for rule in PRICELESS_RULES)
    return [post for post in found if post is not None]
