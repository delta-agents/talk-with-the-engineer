"""De handleiding-tool: uitleg op verzoek in plaats van in elke tooldefinitie.

Waarom een tool en geen langere beschrijvingen: de tien rekentools kosten samen al ongeveer
35.000 tokens aan definities, geladen voordat er iets gevraagd is. Deze uitleg daarbij zou
dat verdubbelen terwijl het meestal niet nodig is. Achter een tool betaal je hem alleen
wanneer je hem opvraagt, en dan alleen de module die je nodig hebt.

Deze tests bewaken niet de formulering - die mag veranderen - maar wat er in MOET staan: de
bronnen die het antwoord dragen, en de valkuilen die in deze codebase daadwerkelijk tot
verkeerde uitspraken hebben geleid.
"""

import pytest

from talk_with_the_engineer.models import ReadMeInput
from talk_with_the_engineer.models.modelset_rules_of_thumb.read_me import MODULES
from talk_with_the_engineer.tools import read_me


@pytest.mark.asyncio
async def test_no_module_gives_an_index_and_not_everything(test_context):
    """Zonder module een korte index, zodat één aanroep genoeg is om te weten wat er is.

    Alles teruggeven zou het doel ondergraven: dan betaal je alsnog de hele handleiding voor
    een vraag die misschien alleen over de bronnen ging.
    """
    result = await read_me(test_context, ReadMeInput())
    everything = await read_me(test_context, ReadMeInput(modules=list(MODULES)))

    assert set(result.available_modules) == set(MODULES)
    for module in MODULES:
        assert module in result.text, module
    assert len(result.text) < len(everything.text) / 5


@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_each_module_stands_on_its_own(test_context, module):
    result = await read_me(test_context, ReadMeInput(modules=[module]))
    assert len(result.text) > 500, module


@pytest.mark.asyncio
async def test_asking_for_two_modules_gives_both(test_context):
    result = await read_me(test_context, ReadMeInput(modules=["bronnen", "gebruik"]))
    assert "STOWA" in result.text
    assert "given_h" in result.text
    # en niet de rest
    assert "procentpunt" not in result.text


@pytest.mark.asyncio
async def test_the_sources_name_what_the_answer_rests_on(test_context):
    """De bronnen staan er met naam en nummer, niet als 'STOWA'.

    Inclusief dat STOWA 2024-37 de gebruikte statistiek uit 2019 BEVESTIGT - zonder die
    zin lijkt het alsof er op een verouderde bron wordt gerekend.
    """
    text = (await read_me(test_context, ReadMeInput(modules=["bronnen"]))).text

    assert "STOWA 2019" in text
    assert "2024-37" in text
    assert "STOWA 2025-23" in text
    # de rapportTITEL en niet de interne rapportcode: PR-nummers zijn intern en zeggen een
    # lezer buiten HKV niets
    assert "Waterveiligheidsperspectief IJsselmeer" in text
    assert "PR4991" not in text
    # geen interne bestandspaden: een agent kan die niet openen en heeft er niets aan
    assert ".json" not in text
    assert ".xlsx" not in text


@pytest.mark.asyncio
async def test_the_assumptions_that_drive_the_outcome_are_named(test_context):
    """De aannames die je niet uit een antwoord kunt aflezen.

    Elk van deze vier verschuift de uitkomst of de RANGORDE, en geen ervan is zichtbaar in
    de getallen die een tool teruggeeft.
    """
    text = (await read_me(test_context, ReadMeInput(modules=["vuistregels"]))).text

    assert "20 mm" in text  # het neerslagverlies, en dat het een open vraag is
    assert "lineair" in text  # kosten, en dat het de rangorde verandert
    assert "geen prijs" in text  # peilopzet, peilmarge, aanvoeren
    assert "grondwater" in text  # wat er niet in zit aan de droge kant


@pytest.mark.asyncio
async def test_the_reporting_module_names_the_traps_that_actually_happened(
    test_context,
):
    """De valkuilen die in deze codebase tot verkeerde uitspraken hebben geleid.

    Dit is geen bedachte lijst. `after` zonder `status` lezen levert bij een onhaalbaar doel
    het advies op om de hele polder onder water te zetten; procentpunten en relatief door
    elkaar halen geeft 1,1 tegen 31 voor hetzelfde ding; en peil en waterstand zijn in
    alledaags Nederlands synoniemen terwijl ze hier het verschil zijn tussen wat je afspreekt
    en wat je overkomt.
    """
    text = (await read_me(test_context, ReadMeInput(modules=["terugkoppelen"]))).text

    assert "status" in text and "action_infeasible" in text
    assert "procentpunt" in text.lower() and "relatief" in text.lower()
    assert "waterstand" in text and "peil" in text
    assert "scenario" in text.lower() and "strategie" in text.lower()
    # en het onderscheid is per veld gemaakt, niet alleen als regel
    assert "target_level_rise_m" in text
    assert "dh_reference_m" in text


@pytest.mark.asyncio
async def test_it_answers_the_question_a_water_engineer_actually_asks(test_context):
    """De vier vragen uit een echte mail over de droge kant.

    Letterlijk gesteld: *"Het probleem van wateroverlast wordt berekend door een Txx bui door
    te rekenen met neerslag-afvoer functie. Hoe heb je dit geïmplementeerd voor droogte? Ik
    kan me voorstellen dat we iets doen met statistiek van het neerslagtekort. Dat je een
    watervoorraad (grondwater + berging) in het studiegebied aan het eind van de winter
    aanneemt... Je moet je realiseren dat wateroverlast (event) en watertekort (groeiseizoen)
    andere tijdschalen hebben."*

    Drie van die vier gingen over aannames die dit model NIET maakt. Dat is precies het soort
    misverstand dat een antwoord onbruikbaar maakt zonder dat iemand het merkt, dus de
    handleiding moet ze expliciet weerleggen in plaats van erover te zwijgen.
    """
    text = (
        await read_me(test_context, ReadMeInput(modules=["vuistregels"]))
    ).text.lower()

    # 1. de tijdschalen verschillen, en dat staat er als zodanig
    assert "groeiseizoen" in text
    assert "48 tot 192 uur" in text

    # 2. een tekort is geen negatieve afvoer; de neerslag-afvoerrelatie geldt hier niet
    assert "negatieve afvoer" in text
    assert "days_to_discharge" in text and "niets" in text

    # 3. de voorraad is de sloot en niet de bodem: geen grondwater, geen beginvoorraad
    assert "grondwater" in text
    assert "beginvoorraad" in text

    # 4. de forcering is twee getallen en geen doorgerekend seizoensverloop
    assert "deficit_mm_per_day" in text
    assert "geen seizoensverloop" in text or "geen reeks" in text


@pytest.mark.asyncio
@pytest.mark.parametrize("module", MODULES)
async def test_nothing_an_agent_cannot_act_on(test_context, module):
    """Alles hier moet veranderen wat de agent DOET of ZEGT. De rest is ruis.

    De eerste versie faalde hierop. Er stond bijvoorbeeld "staat in
    `drought_statistics.json`, met een eigen meta-blok" - een agent kan dat bestand niet
    openen. En een paragraaf over validatie tegen een spreadsheet in de repo: niet te
    controleren, en niet iets dat je aan een waterbeheerder vertelt. En zinnen over het
    document zelf, in de trant van "dit is de meestgestelde vraag, dus hier staat het
    uitgeschreven".

    Deze test is het hek eromheen. Hij is grof - een bestandsnaam kan best legitiem zijn -
    maar terugglijden gaat sluipend, en dan is een grof hek beter dan geen.
    """
    text = (await read_me(test_context, ReadMeInput(modules=[module]))).text

    # interne bestanden en paden: onbereikbaar voor een agent
    for path_marker in (".json", ".xlsx", ".py", ".md", "scripts_Ton"):
        assert path_marker not in text, f"{module}: verwijst naar {path_marker}"

    # meta-commentaar over het document zelf
    for filler in ("hier staat het uitgeschreven", "meestgestelde vraag", "zie issue"):
        assert filler not in text.lower(), f"{module}: {filler!r}"
