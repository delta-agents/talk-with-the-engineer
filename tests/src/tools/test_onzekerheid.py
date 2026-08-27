"""De onzekerheid in de uitvoer: spreiding, caveats, en de precisie die daaruit volgt.

De massabalans is exact, de maatregelen zijn vuistregels, en de uitvoer gaf die twee
dezelfde status. Wat hier wordt vastgelegd is de discipline eromheen:

* parametrische onzekerheid is BEREKEND en staat als bereik in `sensitivity`;
* structurele onzekerheid is NIET berekend en staat als benoemde term in `caveats`;
* de tekst noemt niet meer cijfers dan de spreiding toestaat;
* en er staat nergens een foutmarge die niet uit een berekening komt.
"""

import re

import pytest

from talk_with_the_engineer.models import (
    DischargeInputGivenH,
    RetentionInputGivenH,
    StoreInputGivenArea,
    StoreInputGivenH,
    SupplyInputGivenH,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.base_rule_of_thumb import (
    FIELD_RANGES,
    supported_digits,
)
from talk_with_the_engineer.models.modelset_rules_of_thumb.results import (
    SolveStatus,
    round_significant,
)
from talk_with_the_engineer.tools import (
    calculate_discharge_given_h,
    calculate_retention_given_h,
    calculate_store_given_area,
    calculate_store_given_h,
    calculate_supply_given_h,
)

BARE = {"area_ha": 4000, "discharge_capacity_l_s_ha": 1.25, "return_period": 100}
FULL = {
    **BARE,
    "percentage_open_water": 3.5,
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "rainfall_regime": "R",
    "name_rainfall_pattern": "p1a",
    "days_to_discharge": 4,
}
# de afvoertool vraagt de huidige capaciteit in m3/s en niet in l/s/ha
BARE_DISCHARGE = {
    "area_ha": 4000,
    "discharge_capacity_m3_per_sec": 5.0,
    "return_period": 100,
}
FULL_DISCHARGE = {
    **BARE_DISCHARGE,
    "percentage_open_water": 3.5,
    "time_of_year": "winter",
    "length_event_hrs": 96.0,
    "rainfall_regime": "R",
    "name_rainfall_pattern": "p1a",
    "days_to_discharge": 4,
}


# --- de spreiding is berekend, niet beweerd -----------------------------------------


@pytest.mark.asyncio
async def test_a_bare_call_reports_the_spread_of_its_own_answer(test_context):
    """`ASSUMPTION_NOTES` zegt "dit veld doet veel"; dit zegt hoeveel, hier.

    Bij een kale aanroep loopt de benodigde berging van 13 tot 128 ha over het seizoen
    alleen. Dan is een antwoord van 12,71 ha een getal dat zijn eigen precisie tegenspreekt.
    """
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**BARE, delta_h_available=1.0)
    )
    reported = {item.field for item in result.sensitivity}
    assert reported == {item.field for item in result.assumptions} & set(FIELD_RANGES)
    assert reported, "een kale aanroep hoort spreiding te melden"

    season = next(i for i in result.sensitivity if i.field == "time_of_year")
    assert season.low_value == "summer" and season.high_value == "winter"
    # winter vraagt een orde meer dan zomer; dat is de dominante onzekerheid
    assert season.high_answer > 5 * season.low_answer


@pytest.mark.asyncio
async def test_a_fully_specified_call_reports_no_spread(test_context):
    """Wat de beller zelf invulde weet hij; daar een bandbreedte om verzinnen wij niet."""
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**FULL, delta_h_available=1.0)
    )
    assert result.assumptions == []
    assert result.sensitivity == []


@pytest.mark.asyncio
async def test_a_variant_that_changes_the_status_gets_a_note_and_no_number(
    test_context,
):
    """ "Geen maatregel nodig" is geen kleine maatvoering maar een ander antwoord.

    Het als 0 in een bereik zetten zou die omslag verstoppen, en juist die omslag is bij een
    kale aanroep het waarschijnlijkste gevolg van een aanname: in 64 % van de combinaties
    slaat de status om.
    """
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**BARE, delta_h_available=1.0)
    )
    with_notes = [
        item for item in result.sensitivity if item.low_note or item.high_note
    ]
    assert with_notes, "bij deze invoer hoort minstens een rand van een andere soort"
    for item in with_notes:
        assert item.low_answer is None or item.high_answer is None
        # en elke opmerking hoort bij de kolom die leeg is, en alleen bij die kolom
        assert (item.low_note is None) == (item.low_answer is not None)
        assert (item.high_note is None) == (item.high_answer is not None)


@pytest.mark.asyncio
async def test_the_forward_tool_varies_the_water_level_and_not_the_measure(
    test_context,
):
    """Bij een voorwaartse tool is het gemelde antwoord de stijging, dus dat varieert."""
    result = await calculate_store_given_area(
        test_context, StoreInputGivenArea(**BARE, area_available_ha=100)
    )
    answers = [
        value
        for item in result.sensitivity
        for value in (item.low_answer, item.high_answer)
        if value is not None
    ]
    assert answers, "ook de voorwaartse tool hoort spreiding te melden"
    # waterstanden in meters, geen hectares
    assert all(0.0 <= value < 20.0 for value in answers)


# --- de precisie volgt uit de spreiding ---------------------------------------------


@pytest.mark.parametrize(
    "spread,value,expected",
    [
        (40.0, 68.18, 1),  # 59 % spreiding: een cijfer
        (7.0, 68.18, 2),  # 10 %: twee
        (0.7, 68.18, 3),  # 1 %: drie
        (0.0, 68.18, None),  # geen informatie: laat de formattering zoals hij was
        (5.0, 0.0, None),  # geen antwoord om aan te relateren
    ],
)
def test_the_supported_precision_follows_the_spread(spread, value, expected):
    assert supported_digits(spread, value) == expected


@pytest.mark.asyncio
async def test_the_text_does_not_claim_more_digits_than_the_spread_allows(test_context):
    """De agent leest de zin voor, niet het veld. Daar moet de eerlijkheid dus zitten."""
    bare = await calculate_store_given_h(
        test_context, StoreInputGivenH(**BARE, delta_h_available=1.0)
    )
    # een significant cijfer in de tekst, vier in de data
    assert "10 ha extra open water" in bare.description
    assert bare.data["delta_open_water_ha"] != 10


@pytest.mark.asyncio
async def test_the_discharge_text_also_obeys_the_spread(test_context):
    """Drie van de vijf eenheden sloegen de precisiediscipline over.

    `_rounded` werd netjes toegepast op hectares, maar de twee debieten en de peilmarge
    hadden hun opmaak hardgecodeerd op `:.2f` respectievelijk `:.0f`. Daardoor stond er bij
    een kale aanroep "2.91 m3/s" terwijl de spreiding over de aangenomen velden geen twee
    decimalen toestond - precies de valse precisie uit issue #30, en de machinerie om het
    te voorkomen bestond al.
    """
    bare = await calculate_discharge_given_h(
        test_context, DischargeInputGivenH(**BARE_DISCHARGE, delta_h_available=1.0)
    )
    magnitude = bare.data["extra_discharge_capacity_m3_per_sec_required"]
    spread = max(
        abs(v - magnitude)
        for item in bare.sensitivity
        for v in (item.low_answer, item.high_answer)
        if v is not None
    )
    digits = supported_digits(spread, magnitude)
    assert digits is not None and digits < 3, "anders toetst deze test niets"

    # de tekst noemt het afgeronde getal, en niet het volledige uit `data`
    reported = re.search(r"([\d.]+) m3/s extra gemaalcapaciteit", bare.description)
    assert reported, bare.description
    assert float(reported.group(1)) == pytest.approx(
        round_significant(magnitude, digits)
    )
    assert reported.group(1) != f"{magnitude:.2f}"


@pytest.mark.asyncio
async def test_a_fully_specified_call_keeps_the_old_discharge_formatting(test_context):
    """Zonder gemeten spreiding blijft de opmaak zoals hij was: twee decimalen.

    Dat is dezelfde discipline als bij `supported_digits`: heeft de beller alles ingevuld,
    dan is er geen parametrische onzekerheid die WIJ kennen, en dan gaan we er ook geen
    cijfers aan toevoegen of afhalen.
    """
    full = await calculate_discharge_given_h(
        test_context, DischargeInputGivenH(**FULL_DISCHARGE, delta_h_available=1.0)
    )
    magnitude = full.data["extra_discharge_capacity_m3_per_sec_required"]
    assert full.sensitivity == []
    assert f"{magnitude:.2f} m3/s extra gemaalcapaciteit" in full.description


@pytest.mark.asyncio
async def test_the_text_names_the_range_and_its_cause(test_context):
    """Een bereik zonder oorzaak is een disclaimer; met oorzaak is het bruikbaar."""
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**BARE, delta_h_available=1.0)
    )
    assert "Reken op" in result.description
    assert "afhankelijk van time_of_year" in result.description


@pytest.mark.asyncio
async def test_no_range_sentence_when_there_is_nothing_to_report(test_context):
    result = await calculate_store_given_h(
        test_context, StoreInputGivenH(**FULL, delta_h_available=1.0)
    )
    assert "Reken op" not in result.description


# --- de caveats zijn conditioneel en benoemd ---------------------------------------


@pytest.mark.asyncio
async def test_summer_triggers_the_double_counting_caveat(test_context):
    """V3 staat open en schuift de zomeruitkomsten tot een derde; dat hoort in het antwoord.

    De caveat heet naar het GEBIED en niet naar de bui: het neerslagverlies is een
    eigenschap van het oppervlak, en dat de zomertak hem aanzet betekent alleen dat het
    model hem daar toepast. Zie `SUMMER_LOSS_MM` in `utils_rainfall`.
    """
    summer = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(**{**FULL, "time_of_year": "summer"}, delta_h_available=1.0),
    )
    winter = await calculate_store_given_h(
        test_context, StoreInputGivenH(**FULL, delta_h_available=1.0)
    )
    assert "neerslagverlies van dit gebied" in {c.topic for c in summer.caveats}
    assert "neerslagverlies van dit gebied" not in {c.topic for c in winter.caveats}

    # en de caveat zegt van wie die eigenschap is, en met welke andere hij niet verward
    # moet worden; dat is de correctie uit de terugkoppeling van augustus 2026
    text = " ".join(
        f"{c.what} {c.consequence}"
        for c in summer.caveats
        if c.topic == "neerslagverlies van dit gebied"
    )
    assert "eigenschap van het GEBIED" in text
    assert "bergingscoefficient" in text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "return_period,expected", [(10, False), (100, False), (200, True), (1000, True)]
)
async def test_an_extreme_return_period_triggers_the_extrapolation_caveat(
    test_context, return_period, expected
):
    result = await calculate_store_given_h(
        test_context,
        StoreInputGivenH(
            **{**FULL, "return_period": return_period}, delta_h_available=1.0
        ),
    )
    topics = {c.topic for c in result.caveats}
    assert ("extrapolatie van de statistiek" in topics) is expected


@pytest.mark.asyncio
async def test_a_price_in_the_output_triggers_the_cost_form_caveat(test_context):
    """De kostenvorm bepaalt de rangorde, dus hij hoort te staan waar een prijs staat."""
    result = await calculate_discharge_given_h(
        test_context, DischargeInputGivenH(**FULL, delta_h_available=1.0)
    )
    assert result.cost is not None
    assert "kostenvorm" in {c.topic for c in result.caveats}


@pytest.mark.asyncio
async def test_the_supply_tool_reports_the_availability_assumption(test_context):
    """Het antwoord is niet fout; er zit een dragende aanname onder die niemand ziet.

    Zie PLAN_UITWISSELING_EN_NETWERK.md V11. Het volume staat erbij omdat een debiet
    haalbaar klinkt: 1,81 m3/s is een pompje, 4,68 miljoen m3 in een maand is een vraag aan
    het regionale systeem.
    """
    result = await calculate_supply_given_h(
        test_context,
        SupplyInputGivenH(
            area_ha=4000,
            percentage_open_water=1.0,
            deficit_mm_per_day=4,
            length_days=30,
            drawdown_available_m=0.30,
        ),
    )
    topics = {c.topic for c in result.caveats}
    assert "beschikbaarheid van aanvoerwater" in topics
    assert "alleen oppervlaktewater" in topics

    availability = next(
        c for c in result.caveats if c.topic == "beschikbaarheid van aanvoerwater"
    )
    assert "4.68 miljoen m3" in availability.consequence
    # en de wateroverlast-tools melden hem niet: de zee neemt je water wel aan
    wet = await calculate_store_given_h(
        test_context, StoreInputGivenH(**FULL, delta_h_available=1.0)
    )
    assert "beschikbaarheid van aanvoerwater" not in {c.topic for c in wet.caveats}


# --- de discipline: geen verzonnen foutmarge ---------------------------------------


@pytest.mark.asyncio
async def test_no_caveat_states_an_error_margin_that_is_not_computed(test_context):
    """Een gefabriceerd "+/- 15 %" is erger dan een gefabriceerd puntgetal.

    De caveats mogen een richting en een orde noemen die uit een gemeten geval komt - "tot
    een derde lager", "een factor twee bandbreedte" - maar geen foutmarge op het antwoord
    zelf, want die is niet berekend. Deze test bewaakt de vorm: geen enkele caveat mag zich
    voordoen als een berekende marge op dit antwoord.
    """
    everything = []
    for period in (100, 1000):
        for season in ("summer", "winter"):
            result = await calculate_discharge_given_h(
                test_context,
                DischargeInputGivenH(
                    **{**FULL, "return_period": period, "time_of_year": season},
                    delta_h_available=1.0,
                ),
            )
            everything.extend(result.caveats)

    assert everything
    for caveat in everything:
        text = f"{caveat.what} {caveat.consequence}".lower()
        assert "±" not in text
        assert "+/-" not in text
        # "onzekerheid van X %" op het antwoord zelf zou een verzonnen marge zijn
        assert "onzekerheid van" not in text


@pytest.mark.asyncio
async def test_the_output_survives_the_mcp_transport(test_context):
    """Data wordt niet gecomprimeerd, en dat is het enige onvoorwaardelijke kanaal.

    De spreiding en de caveats staan daarom in de uitvoer en niet alleen in de tekst.
    """
    from fastmcp import Client

    from talk_with_the_engineer.routers.tools_router_RulesOfThumb import mcp

    async with Client(mcp) as client:
        response = await client.call_tool(
            "calculate_store_given_h",
            {"input": {**BARE, "delta_h_available": 1.0}},
        )
    content = response.structured_content
    assert content["sensitivity"], "spreiding hoort de transportlaag te overleven"
    assert content["caveats"], "caveats horen de transportlaag te overleven"
    assert {"field", "low_value", "high_value"} <= set(content["sensitivity"][0])
    assert {"topic", "what", "consequence"} <= set(content["caveats"][0])


# --- elke gevoeligheidsrij is nagerekend, geen enkele echoot het basisantwoord ---------


SENSITIVITY_CASES = [
    pytest.param(
        calculate_retention_given_h,
        RetentionInputGivenH,
        {**BARE_DISCHARGE, "delta_h_available": 1.0},
        id="retention_given_h",
    ),
    pytest.param(
        calculate_store_given_h,
        StoreInputGivenH,
        {**BARE, "delta_h_available": 1.0},
        id="store_given_h",
    ),
    pytest.param(
        calculate_discharge_given_h,
        DischargeInputGivenH,
        {**BARE_DISCHARGE, "delta_h_available": 1.0},
        id="discharge_given_h",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool,model,kwargs", SENSITIVITY_CASES)
async def test_every_sensitivity_row_matches_a_real_recalculation(
    test_context, tool, model, kwargs
):
    """Elke rand van elke rij is dezelfde aanroep met dat veld expliciet ingevuld.

    Dit is het vangnet uit B3. Daar meldde de rij voor `days_to_retain_discharge` bij 0 en
    bij 4 dagen exact het basisantwoord van 1266 ha, terwijl 0 dagen het doel met deze
    maatregel helemaal onhaalbaar maakte en 4 dagen op 461 ha uitkwam. De oorzaak was een
    override die op het invoermodel landde en de toestand nooit bereikte, en zo'n override
    is van BUITEN niet te onderscheiden van een veld zonder effect - tenzij je hem naast een
    echte doorrekening legt, en dat is precies wat hier gebeurt.

    Bewust niet als runtime-assertie in `sensitivity_of`: een veld dat werkelijk niets doet
    bestaat ook (`rainfall_regime` LL en R hebben in de zomer dezelfde correctiefactor), en
    dat zou dan als vals alarm langskomen. In een test kan het exact, want hier is de
    vergelijking niet "beweegt het" maar "klopt het getal".
    """
    base = await tool(test_context, model(**kwargs))
    assert base.sensitivity, "een kale aanroep hoort spreiding te melden"

    for item in base.sensitivity:
        low_value, high_value = FIELD_RANGES[item.field]
        for value, answer, note in (
            (low_value, item.low_answer, item.low_note),
            (high_value, item.high_answer, item.high_note),
        ):
            variant = await tool(
                test_context, model(**{**kwargs, item.field: value})
            )
            where = f"{item.field}={value}"
            if answer is None:
                # geen getal betekent: bij deze waarde is het antwoord van een andere SOORT
                assert note, f"{where}: een lege rand hoort een opmerking te hebben"
                assert variant.status is not SolveStatus.EXACT, (
                    f"{where}: de rij meldt een andere soort antwoord, "
                    f"maar de doorrekening geeft {variant.status}"
                )
            else:
                assert variant.status is SolveStatus.EXACT, (
                    f"{where}: de rij meldt {answer}, maar de doorrekening geeft "
                    f"status {variant.status}"
                )
                assert variant.measure.delta == pytest.approx(answer), (
                    f"{where}: de rij meldt {answer}, de doorrekening "
                    f"{variant.measure.delta}"
                )
