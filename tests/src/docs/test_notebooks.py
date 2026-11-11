"""De voorbeelden in de documentatie, getoetst tegen de invoerschema's van vandaag.

De notebooks in `docs/` worden door de CI uitgevoerd (`quarto render --execute`), dus een
voorbeeld dat niet meer klopt maakt de build rood. Dat is goed, maar het is een LANGZAME
manier om erachter te komen: de docs-build draait apart van de testsuite en duurt minuten.

Deze test doet dezelfde controle in milliseconden, en op de plek waar hij hoort. Hij voert
niets uit - hij leest de broncode van elke cel en kijkt of elk veld dat aan een invoermodel
wordt meegegeven op dat model bestaat.

Dat gat is echt: een veld dat uit een invoermodel verdwijnt maakt de testsuite niet rood,
want die voert de notebooks niet uit. De docs-build merkt het pas minuten later.
"""

import ast
import importlib
import json
import pkgutil
from operator import attrgetter
from pathlib import Path

import pytest

from talk_with_the_engineer.interface import schemas as schemas_package

NOTEBOOKS = sorted(Path("docs").rglob("*.ipynb"))


def _schema_modules():
    """Elke module in `interface/schemas/`.

    Sinds de herindeling is er geen her-exporteerlaag meer die alle invoermodellen op één
    plek bij elkaar zet, en dat is met opzet: `interface/mcp/router.py` importeert direct
    uit de module waar een model woont. Deze test wil ze juist wél allemaal, dus loopt hij
    het pakket zelf langs in plaats van te leunen op een lijst die kan verouderen.
    """
    for info in pkgutil.iter_modules(schemas_package.__path__):
        yield importlib.import_module(f"{schemas_package.__name__}.{info.name}")


# `"Input" in name` en niet `endswith`: de paren heten `SupplyInputGivenH` en
# `RetentionInputGivenArea`, dus de helft van de modellen eindigt op de vraagrichting.
INPUT_MODELS = {
    name: candidate
    for module in _schema_modules()
    for name in dir(module)
    if "Input" in name and hasattr(candidate := getattr(module, name), "model_fields")
}


def _code_cells(path: Path):
    notebook = json.loads(path.read_text())
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] == "code":
            yield index, "".join(cell["source"])


def _model_calls(source: str):
    """Elke aanroep van een invoermodel in deze cel, met de veldnamen die erin gaan."""
    try:
        # `PyCF_ALLOW_TOP_LEVEL_AWAIT`, want een notebookcel mag `await` op het hoogste
        # niveau en `ast.parse` niet. Zonder die vlag sloeg deze functie stil precies de
        # cellen over die een tool aanroepen - en dat zijn de enige die ertoe doen.
        # `test_the_documentation_actually_exercises_the_supply_tools` hieronder is het
        # vangnet dat dat aan het licht bracht.
        tree = compile(
            source,
            "<cel>",
            "exec",
            flags=ast.PyCF_ONLY_AST | ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
        )
    except SyntaxError:
        # een cel met IPython-magics is geen geldige Python; die bevat geen modelaanroep
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        model = INPUT_MODELS.get(node.func.id)
        if model is None:
            continue
        # `**payload` kunnen we niet statisch nakijken; die keywords hebben `arg is None`
        yield node.func.id, model, [kw.arg for kw in node.keywords if kw.arg]


@pytest.mark.skipif(not NOTEBOOKS, reason="geen notebooks in docs/")
@pytest.mark.parametrize("path", NOTEBOOKS, ids=attrgetter("name"))
def test_every_documented_call_matches_the_current_schema(path):
    """Elk veld in een voorbeeld bestaat nog op het model waaraan het wordt meegegeven."""
    unknown = []
    for cell_index, source in _code_cells(path):
        for name, model, fields in _model_calls(source):
            for field in fields:
                if field not in model.model_fields:
                    unknown.append(f"cel {cell_index}: {name}({field}=...)")

    assert not unknown, (
        f"{path} geeft velden mee die niet meer op het invoermodel staan:\n  "
        + "\n  ".join(unknown)
    )


@pytest.mark.skipif(not NOTEBOOKS, reason="geen notebooks in docs/")
def test_the_documentation_actually_exercises_the_supply_tools():
    """En de controle hierboven toetst pas iets als de aanvoertools er ook in staan.

    Zonder dit vangnet zou een notebook waaruit de aanvoervoorbeelden zijn verdwenen
    stilzwijgend slagen, en dan bewaakt de test hierboven precies het geval niet waarvoor
    hij is geschreven.
    """
    called = {
        name
        for path in NOTEBOOKS
        for _, source in _code_cells(path)
        for name, _, _ in _model_calls(source)
    }
    assert {"SupplyInputGivenH", "SupplyInputGivenSupply"} <= called
