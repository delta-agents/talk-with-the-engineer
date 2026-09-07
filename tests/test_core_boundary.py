"""De laaggrens, als eigenschap in plaats van als belofte.

De repo heeft drie lagen en de afhankelijkheid loopt één kant op:

    interface  ->  epistemics  ->  core

`core/` is het world model: de toestand, de maatregelen, de transitie en wat erop leunt.
`epistemics/` zegt wat je van een antwoord mag geloven. `interface/` is de view - vandaag
MCP en FastAPI - en die is vervangbaar.

Deze test bestaat omdat een architectuurregel in een plan een belofte is. Dezelfde vorm als
`test_kern_properties.py`, waar `ast.parse` verbiedt dat `np.` in de primitieven staat: de
regel wordt een eigenschap doordat iets rood wordt als hij breekt.

Wat hij tegenhoudt is niet theoretisch. Vóór de herindeling importeerde `results.py` zijn
eigen epistemieklaag, en dat sloot een cirkel: results -> epistemics -> inverse -> results.
En `find_package.py` gaf een pydantic INVOERmodel als bui aan de kern door, waarmee de kern
aan de vorm van de MCP-interface hing.
"""

import ast
import pathlib

import pytest

PKG = pathlib.Path("src/talk_with_the_engineer")

CORE = PKG / "core"
EPISTEMICS = PKG / "epistemics"


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


@pytest.mark.parametrize("path", _modules(CORE), ids=lambda p: p.as_posix())
def test_the_core_does_not_reach_up_into_the_layers_above_it(path):
    """`core/` importeert niets uit `epistemics/` of `interface/`.

    Dit is de enige regel die de indeling echt draagt. Valt hij weg, dan is `core/` een map
    en geen laag: een kern die zijn eigen uitlegzinnen of zijn eigen caveats importeert kan
    niet meer zonder MCP bestaan, en dat is precies de eigenschap waarvoor de herindeling
    bestaat.

    Bewust GEEN verbod op `pydantic` in de kern. `PolderState`, `Action` en `Connection`
    zijn frozen pydantic-modellen en dat is een bestaande, onderbouwde keuze (validatie en
    onveranderlijkheid); daar is niets van de interface aan. Wat verboden is, is afhangen
    van de INVOERmodellen van de tools.
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


@pytest.mark.parametrize("path", _modules(EPISTEMICS), ids=lambda p: p.as_posix())
def test_the_epistemics_layer_does_not_reach_into_the_interface(path):
    """`epistemics/` importeert niets uit `interface/`.

    Deze laag hoort ook te werken voor een aanroeper die de kern direct gebruikt - een
    notebook, een script - en die wil dezelfde aannames, dezelfde spreiding en dezelfde
    caveats. Zodra hij een toolschema importeert, is hij een onderdeel van de MCP-laag
    geworden.

    De andere kant mag wel: `epistemics/uncertainty.py` roept `solve` en `evaluate` uit de
    kern aan om een antwoord meerdere keren door te rekenen, en dat is de toegestane pijl.
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
    """Een vangnet onder de twee tests hierboven.

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


@pytest.mark.xfail(
    reason=(
        "WP B1: de bui en het tekort komen nog duck-typed de kern binnen, dus een "
        "ontbrekend veld is stil een default in plaats van een fout. Deze test wordt "
        "groen zodra `core/exogenous/` een `Storm` en een `Deficit` levert."
    ),
    strict=True,
)
def test_the_forcing_arguments_are_typed_instead_of_duck_typed():
    """Geen `getattr(x, "veld", default)` op de forcering, en geen kaal forceringsargument.

    Dit is bevinding W1: `storm` en `deficit` zijn het enige lid van de tuple zonder type.
    Twee gevolgen, en ze zijn beide gemeten: `getattr(storm, "rain_volume_mm", None)` en
    `getattr(deficit, "available_source_volume_m3", np.inf)` maken een ontbrekend veld tot
    een stille aanname - en die tweede is de OUTSIDE-aanname uit `connection.py`, een tweede
    keer, op een andere plek, met een andere default.

    Staat als `xfail(strict=True)`, zodat hij omslaat naar rood zodra WP B1 klaar is en
    iemand vergeet deze test aan te zetten.
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
                and node.args[0].id in {"storm", "deficit", "boundary"}
            ):
                offences.append(f"{path.as_posix()}:{node.lineno}")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args:
                    if (
                        arg.arg in {"storm", "deficit", "boundary"}
                        and arg.annotation is None
                    ):
                        offences.append(f"{path.as_posix()}:{node.lineno} ({arg.arg})")

    assert not offences, (
        "de forcering komt nog ongetypeerd de kern binnen: "
        + ", ".join(sorted(offences))
    )
