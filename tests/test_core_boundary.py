"""De laaggrens, als eigenschap in plaats van als belofte.

De repo heeft drie lagen en de afhankelijkheid loopt een kant op:

    interface  ->  epistemics  ->  core

`core/` is het world model: de toestand, de maatregelen, de forcering, de transitie en wat
erop leunt. `epistemics/` zegt wat je van een antwoord mag geloven. `interface/` is de view -
vandaag MCP en FastAPI - en die is vervangbaar.

Dezelfde vorm als `test_kern_properties.py`, waar `ast.parse` verbiedt dat `np.` in de
primitieven staat: een regel wordt een eigenschap doordat er iets rood wordt als hij breekt.
"""

import ast
import pathlib

import pytest

PKG = pathlib.Path("src/talk_with_the_engineer")

CORE = PKG / "core"
EPISTEMICS = PKG / "epistemics"

FORCING_ARGUMENTS = frozenset({"storm", "deficit", "boundary"})
"""De argumentnamen waarin de forcering de kern binnenkomt."""


def _modules(root):
    return sorted(p for p in root.rglob("*.py") if p.name != "__init__.py")


def _imported_modules(path):
    """Elke module waaruit dit bestand importeert, ook binnen een functie."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name


@pytest.mark.parametrize("path", _modules(CORE), ids=pathlib.Path.as_posix)
def test_the_core_does_not_reach_up_into_the_layers_above_it(path):
    """`core/` importeert niets uit `epistemics/` of `interface/`.

    Dit is de regel die de indeling draagt. Valt hij weg, dan is `core/` een map en geen
    laag: een kern die zijn eigen uitlegzinnen of zijn eigen caveats importeert kan niet
    meer zonder MCP bestaan, en dat is precies de eigenschap waarvoor de indeling bestaat.

    De faalmodus is bovendien niet alleen conceptueel. `epistemics` leunt op `solve` en
    `evaluate` uit de kern, dus een import de andere kant op maakt een cykel: de een kan
    niet laden zonder de ander.

    Bewust GEEN verbod op `pydantic` in de kern. `PolderState`, `Action` en `Connection`
    zijn frozen pydantic-modellen, en dat is een keuze over validatie en onveranderlijkheid;
    daar is niets van de interface aan. Wat verboden is, is afhangen van de INVOERmodellen
    van de tools.
    """
    forbidden = {
        module
        for module in _imported_modules(path)
        if module.startswith("talk_with_the_engineer.epistemics")
        or module.startswith("talk_with_the_engineer.interface")
    }
    assert not forbidden, (
        f"{path.as_posix()} importeert uit een laag erboven: {sorted(forbidden)}. "
        "De kern definieert het model; de lagen erboven hangen ervan af en niet andersom."
    )


@pytest.mark.parametrize("path", _modules(EPISTEMICS), ids=pathlib.Path.as_posix)
def test_the_epistemics_layer_does_not_reach_into_the_interface(path):
    """`epistemics/` importeert niets uit `interface/`.

    Deze laag hoort ook te werken voor een aanroeper die de kern direct gebruikt - een
    notebook, een script - en die wil dezelfde aannames, dezelfde spreiding en dezelfde
    caveats. Zodra hij een toolschema importeert, is hij een onderdeel van de MCP-laag
    geworden.

    De andere kant mag wel: `uncertainty.py` roept `solve` en `evaluate` aan om een antwoord
    meerdere keren door te rekenen, en dat is de toegestane richting.
    """
    forbidden = {
        module
        for module in _imported_modules(path)
        if module.startswith("talk_with_the_engineer.interface")
    }
    assert not forbidden, (
        f"{path.as_posix()} importeert uit de interface: {sorted(forbidden)}. "
        "De richting is interface -> epistemics -> core, en geen pijl terug."
    )


def test_the_layers_all_exist_and_are_not_empty():
    """Een vangnet onder de tests hierboven.

    `_modules()` levert een lege lijst als een map wordt hernoemd of verdwijnt, en
    `parametrize` over een lege lijst is groen. Zonder deze test zou de laagregel dus stil
    verdwijnen op precies het moment dat de indeling verandert.
    """
    for root, minimum in ((CORE, 10), (EPISTEMICS, 4), (PKG / "interface", 10)):
        assert root.is_dir(), f"{root.as_posix()} bestaat niet"
        assert len(_modules(root)) >= minimum, (
            f"{root.as_posix()} heeft {len(_modules(root))} modules, minder dan de "
            f"verwachte {minimum} - is de indeling veranderd?"
        )


def test_the_forcing_arrives_typed_and_not_duck_typed():
    """De forcering is een `Storm`, een `Deficit` of een `BoundaryCondition`, en geannoteerd.

    Twee regels in een, want ze bewaken hetzelfde: dat de kern weet wat er binnenkomt.

    1. **Geen `getattr(storm, "veld", default)`.** Een ontbrekend veld hoort een fout te
       zijn en geen stille aanname. Die vorm kwam op meerdere rekenpaden voor met
       verschillende standaardwaarden - `float("inf")` op het ene pad en `np.inf` op het
       andere - en dan maakt hetzelfde model op twee plekken een andere aanname zonder dat
       het aan de uitkomst te zien is.
    2. **Elk forceringsargument is geannoteerd.** Zonder annotatie is "de bui" wat er
       toevallig langskomt: een invoermodel van een tool, of een object dat een script zelf
       in elkaar zet. Dan hangt de kern aan de vorm van zijn aanroepers.

    Alleen de namen uit `FORCING_ARGUMENTS`, en niet elke parameter in de kern. Dit is geen
    typecheck-regel maar een grensregel: hij bewaakt het lid van de tuple waar de
    afhankelijkheid ooit de verkeerde kant op liep.
    """
    offences = []
    for path in _modules(CORE):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) == 3
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in FORCING_ARGUMENTS
            ):
                offences.append(
                    f"{path.as_posix()}:{node.lineno} getattr op "
                    f"`{node.args[0].id}` met een standaardwaarde"
                )
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args:
                    if arg.arg in FORCING_ARGUMENTS and arg.annotation is None:
                        offences.append(
                            f"{path.as_posix()}:{node.lineno} `{node.name}` neemt "
                            f"`{arg.arg}` zonder annotatie"
                        )

    assert not offences, (
        "de forcering komt ongetypeerd de kern binnen:\n  "
        + "\n  ".join(sorted(offences))
    )
