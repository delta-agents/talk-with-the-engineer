"""Foutmeldingen die de aanroeper daadwerkelijk bereiken.

De tools raisen `ModelRetry` uit pydantic-ai om te zeggen: je aanroep was fout, dit is
waarom, probeer het opnieuw. Dat werkt binnen pydantic-ai, maar aan de twee andere
grenzen niet vanzelf.

FastMCP garandeert alleen voor `ToolError` dat de tekst bij de client terechtkomt; andere
excepties gaan door de generieke handler, die ze afhankelijk van `mask_error_details` kan
inslikken en er een volledige traceback bij logt. Een LLM die de tool aanroept moet juist
kunnen lezen wélke waarden geldig zijn, dus wordt `ModelRetry` hier omgezet naar
`ToolError`.

Aan de FastAPI-kant zet `main.py` beide op een 422 met het bericht in de body.
"""

from functools import wraps

from fastmcp.exceptions import ToolError
from pydantic_ai import ModelRetry


def as_tool_error(func):
    """Zet een `ModelRetry` uit de toolbody om in een `ToolError`.

    Alleen voor fouten die de tool zelf opwerpt, zoals een maatvoering die niet in het
    watersysteem past. Fouten uit de invoervalidators ontstaan eerder - bij het omzetten
    van de argumenten naar het model, buiten deze functie - en worden door FastMCP zelf
    gerapporteerd; zie de opmerking in PLAN_TOOLS_REFACTOR.md over `ModelRetry` in
    validators.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ModelRetry as exc:
            raise ToolError(str(exc)) from exc

    return wrapper
