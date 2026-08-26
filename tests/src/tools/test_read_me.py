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
    assert "PR4991.10" in text


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
