"""Geen bouwgeschiedenis in de code, en dat geldt voor élk commentaar.

`test_uitlegbaarheid.py` houdt de bouwgeschiedenis uit de tekst die een AGENT leest -
veldbeschrijvingen en tooldocstrings. Deze test doet hetzelfde voor de tekst die een
ONTWIKKELAAR leest: elke docstring en elk comment in `src/` en `tests/`.

**Waarom dat geen dubbelop is.** Een agent moet ervan af omdat het contextruimte kost en
hij er niets mee kan. Een ontwikkelaar moet ervan af om een andere reden: een comment die
vertelt wat er ooit anders was, veroudert op een manier die niemand opmerkt. Wie de code
leest ziet niet dat de vergelijking niet meer klopt, en gaat een verhaal geloven over een
versie die niet bestaat.

**Wat er dan WEL hoort te staan.** De reden die vandaag nog geldt. Bijna elke passage die
deze test tegenhoudt draagt zo'n reden - hij zit alleen verpakt in een anekdote over een
vorige versie. Zo'n anekdote is bijna altijd om te schrijven naar de vorm "X geeft Y, en
daarom doen we Z": dezelfde kennis, en hij blijft waar zonder dat de lezer de code van toen
hoeft te kennen.

Wat deze test bewust NIET verbiedt:

* verwijzingen naar CODE - die kan de lezer openen, en ze verouderen niet los van de tekst;
* verwijzingen naar een issue in een comment. Dat is een lopende discussie en geen
  geschiedenis. Voor agent-tekst is hij wél verboden; zie `BUILD_TALK` daar;
* GEMETEN getallen met hun herkomst, ook als die meting in het verleden is gedaan. "Op de
  referentiecasus betaalt 3800 ha 44 % meer" is een eigenschap van het model.
"""

import ast
import pathlib
import re

import pytest

ROOTS = (pathlib.Path("src"), pathlib.Path("tests"))

HISTORY = re.compile(
    r"""
      \bvoorheen\b
    | \beerder\s+(werd|werden|stond|stonden|als)\b
    | \b(stond|stonden)\s+(er|hier|daar|eerder|nergens)\b
    | \been\s+eerdere\s+versie\b
    | \bheette\s+eerder\b
    | \bis\s+vervallen\b
    | \bhier\s+zat\s+een\b
    | \bWP\s?\d
    | \bSec\.\s?\d
    | \bdezelfde\s+stilte\s+bestond\b
    | \bvervangt\s+`                       # "Vervangt `state_before`"
    """,
    re.IGNORECASE | re.VERBOSE,
)
"""Formuleringen die over een VORIGE versie van de code gaan.

Smal gehouden en op vaste woordcombinaties, niet op losse woorden als "was" of "eerder":
die staan in legitieme zinnen over het watersysteem, en een test die daarop afgaat wordt
weggeklikt in plaats van gevolgd.
"""


def _python_files():
    for root in ROOTS:
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path


def _prose(path):
    """Elke docstring en elk comment in dit bestand, met zijn regelnummer.

    Docstrings via `ast` en comments via een regelscan. Alleen PROZA, dus geen stringliteral
    die als waarde wordt gebruikt: een veldbeschrijving is proza voor een agent en wordt door
    `test_uitlegbaarheid.py` bewaakt, en die twee regels zijn niet gelijk.
    """
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc:
            yield getattr(node, "lineno", 1), doc

    for number, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            yield number, stripped


@pytest.mark.parametrize("path", list(_python_files()), ids=pathlib.Path.as_posix)
def test_no_comment_tells_the_story_of_a_previous_version(path):
    """Geen docstring en geen comment vertelt wat er ooit anders was.

    De melding noemt het regelnummer en de gevonden formulering, zodat de plek meteen te
    vinden is. Het herschrijven is bijna altijd hetzelfde: haal de anekdote weg en laat de
    reden staan die er in zit.
    """
    offences = [
        f"{path.as_posix()}:{number} ...{match.group(0)!r}..."
        for number, prose in _prose(path)
        if (match := HISTORY.search(prose))
    ]
    assert not offences, (
        "bouwgeschiedenis in commentaar - schrijf de reden op zonder de vorige versie:\n  "
        + "\n  ".join(offences)
    )


def test_the_sweep_actually_reads_something():
    """Vangnet: `parametrize` over een lege lijst is groen.

    Zonder deze test verdwijnt de regel stil zodra `src/` of `tests/` van plek verandert of
    `_prose` niets meer oplevert.
    """
    files = list(_python_files())
    assert len(files) > 50, f"maar {len(files)} bestanden gevonden"

    prose = [text for path in files for _, text in _prose(path)]
    assert len(prose) > 500, f"maar {len(prose)} stukken commentaar gevonden"
