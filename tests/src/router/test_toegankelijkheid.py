"""Het toegankelijkheidsbudget: wat een agent te zien krijgt, blijft begrensd.

De rekenkern mag moeilijk zijn; de toolset niet. Dit bestand dwingt dat af in plaats van
het te beloven, in dezelfde geest als de AST-test op de numpy-deelverzameling: een grens
die je kunt overschrijden is een grens die een test moet bewaken.

De budgetten zijn gekalibreerd op de meting van 2026-08-29 (11 tools, 92.821 tekens
totaal, grootste tool 14.357, diepste schema 8, meeste velden 30) met beperkte marge.
Wie een tool toevoegt of een invoermodel uitbreidt en tegen een grens loopt, heeft twee
nette uitwegen - tekst naar een `read_me`-module verplaatsen (het bestaande
progressive-disclosure-patroon, issue #9) of het schema versimpelen - en één die dit
bestand bewust duur maakt: het budget verhogen, zichtbaar in de diff, met een reden in
het commitbericht.
"""

import json

import pytest
from fastmcp import Client

from talk_with_the_engineer.interface.mcp.router import mcp

# Totaal over alle tools, in tekens van de geserialiseerde definitie (naam, beschrijving,
# invoerschema). Dit is wat elke conversatie betaalt voordat er iets gevraagd is; bij een
# ruwe vier tekens per token is het huidige totaal ~23k tokens. De marge is één ruime
# nieuwe tool - niet twee, want dat gesprek hoort hier gevoerd te worden.
TOTAAL_BUDGET_TEKENS = 115_000

# Per tool. De grootste is nu `calculate_supply_given_supply` (14.357); een tool die hier
# overheen wil, hoort zijn uitleg in `read_me` te zetten, niet in zijn definitie.
BUDGET_PER_TOOL_TEKENS = 16_000

# De beschrijving is wat het model leest om te kiezen; boven de ~1.500 tekens is het geen
# beschrijving meer maar een handleiding, en handleidingen zijn opvraagbaar.
BUDGET_BESCHRIJVING_TEKENS = 1_600

# Nestingsdiepte en veldental van het invoerschema: de maat voor hoe moeilijk het is om
# een geldige aanroep te construeren. De cascade- en allocatietools zitten op 8 diep en
# 30 velden; dieper of breder dan dit is een teken dat de tool twee vragen tegelijk
# probeert te zijn.
BUDGET_SCHEMA_DIEPTE = 9
BUDGET_SCHEMA_VELDEN = 36

# Het UITVOERschema staat ook in elke tooldefinitie op de draad, en is toolsetbreed groter
# dan alles hierboven samen. Wat een agent ervan betaalt verschilt per client - gemeten
# (zie het bevindingenrapport van de pakketzoeker en issue #69): Claude Code geeft het
# uitvoerschema helemaal niet door en stript ook de veldbeschrijvingen uit het
# invoerschema; pydantic-ai geeft alles ongewijzigd door. Het draadformaat is dus de
# bovengrens, en dat is wat hier wordt bewaakt.
#
# De grootste post is de pakketzoeker (21.342 tekens), en het mechanisme is de
# dereferentie-middleware van FastMCP: die inline-t elk hergebruikt genest model volledig,
# waardoor PackageReading er vier keer voluit in staat (met $refs zou het 15.677 zijn).
# De knop is FastMCP(dereference_schemas=False), maar de middleware bestaat juist voor
# clients die $ref niet aankunnen - dat is een compatibiliteitsafweging en geen
# budgetkwestie, dus hier wordt geteld wat er werkelijk verstuurd wordt.
TOTAAL_BUDGET_UITVOERSCHEMA_TEKENS = 160_000
BUDGET_UITVOERSCHEMA_PER_TOOL_TEKENS = 24_000


def _uitvoerschema(tool) -> str:
    return json.dumps(tool.outputSchema or {}, ensure_ascii=False)


def _definitie(tool) -> str:
    return json.dumps(
        {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.inputSchema,
        },
        ensure_ascii=False,
    )


def _diepte(node, d: int = 0) -> int:
    if isinstance(node, dict):
        return max([d] + [_diepte(v, d + 1) for v in node.values()])
    if isinstance(node, list):
        return max([d] + [_diepte(v, d) for v in node])
    return d


def _velden(schema) -> int:
    """Alle property-namen in het schema, genest meegeteld: wat een agent kan invullen."""
    count = 0
    stack = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            props = node.get("properties")
            if isinstance(props, dict):
                count += len(props)
            stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
        elif isinstance(node, list):
            stack.extend(node)
    return count


async def _tools():
    async with Client(mcp) as client:
        return sorted(await client.list_tools(), key=lambda tool: tool.name)


@pytest.mark.asyncio
async def test_de_toolset_blijft_binnen_het_totale_contextbudget():
    tools = await _tools()
    totaal = sum(len(_definitie(tool)) for tool in tools)
    assert totaal <= TOTAAL_BUDGET_TEKENS, (
        f"alle tooldefinities samen zijn {totaal} tekens en het budget is "
        f"{TOTAAL_BUDGET_TEKENS}; verplaats uitleg naar een read_me-module of maak de "
        f"verhoging zichtbaar in dit bestand, met de reden erbij"
    )


@pytest.mark.asyncio
async def test_geen_enkele_tool_is_in_zijn_eentje_een_handleiding():
    for tool in await _tools():
        definitie = len(_definitie(tool))
        assert definitie <= BUDGET_PER_TOOL_TEKENS, (
            f"{tool.name} is {definitie} tekens; boven {BUDGET_PER_TOOL_TEKENS} hoort "
            f"de uitleg in read_me, niet in de definitie"
        )
        beschrijving = len(tool.description or "")
        assert beschrijving <= BUDGET_BESCHRIJVING_TEKENS, (
            f"de beschrijving van {tool.name} is {beschrijving} tekens; dat is een "
            f"handleiding geworden, en handleidingen zijn opvraagbaar via read_me"
        )


@pytest.mark.asyncio
async def test_ook_het_uitvoerschema_blijft_binnen_zijn_budget():
    """Het draadformaat is meer dan wat een agent invult; ook de leeskant heeft een budget.

    De veldbeschrijvingen in het uitvoerschema zijn een kanaal - zo leert een agent wat
    `binding` betekent en dat `cost` niet de pakketprijs is zodra `priceless` gevuld is -
    dus krimpen door beschrijvingen te strippen is hier geen fix. Wat deze toets bewaakt
    is dat de leeskant niet stil meegroeit tot een handleiding per tool.
    """
    tools = await _tools()
    totaal = sum(len(_uitvoerschema(tool)) for tool in tools)
    assert totaal <= TOTAAL_BUDGET_UITVOERSCHEMA_TEKENS, (
        f"alle uitvoerschema's samen zijn {totaal} tekens en het budget is "
        f"{TOTAAL_BUDGET_UITVOERSCHEMA_TEKENS}; kijk eerst naar gedeelde geneste modellen "
        f"die door de dereferentie meermaals worden geinlined"
    )
    for tool in tools:
        omvang = len(_uitvoerschema(tool))
        assert omvang <= BUDGET_UITVOERSCHEMA_PER_TOOL_TEKENS, (
            f"het uitvoerschema van {tool.name} is {omvang} tekens; boven "
            f"{BUDGET_UITVOERSCHEMA_PER_TOOL_TEKENS} hoort de uitleg in read_me of in "
            f"minder herhaalde geneste modellen"
        )


@pytest.mark.asyncio
async def test_een_geldige_aanroep_blijft_construeerbaar():
    for tool in await _tools():
        diepte = _diepte(tool.inputSchema)
        velden = _velden(tool.inputSchema)
        assert diepte <= BUDGET_SCHEMA_DIEPTE, (
            f"het invoerschema van {tool.name} is {diepte} niveaus diep "
            f"(budget {BUDGET_SCHEMA_DIEPTE}); zo'n schema is voor een agent niet meer "
            f"te overzien"
        )
        assert velden <= BUDGET_SCHEMA_VELDEN, (
            f"het invoerschema van {tool.name} telt {velden} velden "
            f"(budget {BUDGET_SCHEMA_VELDEN}); overweeg of dit niet twee vragen in "
            f"één tool zijn"
        )
