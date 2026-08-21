"""Foutmeldingen die de aanroeper daadwerkelijk bereiken.

De koppeling tussen FastMCP en pydantic-ai is gedocumenteerd, en hij loopt van server naar
client - niet andersom:

* **Serverkant (FastMCP).** `ToolError` is het contract voor "dit is een toolfout die de
  client mag zien". Andere excepties gaan door de generieke handler, die ze afhankelijk van
  `mask_error_details` kan inslikken en er een volledige traceback bij logt.
* **Clientkant (pydantic-ai).** `MCPToolset` heeft `tool_error_behavior`, met `'retry'` als
  default: *"Raises ModelRetry, sending the server error back to the model as a retry
  prompt."* De andere waarden zijn `'failed'` (opgenomen als toolresultaat met
  `outcome='failed'`) en `'error'` (propageert de exceptie en beëindigt de agent-run).

`ModelRetry` is dus een grootheid van de **client**. Een MCP-server hoort `ToolError` te
gooien; pydantic-ai maakt daar aan de andere kant zelf weer een `ModelRetry` van, zodat het
model zijn aanroep kan corrigeren. Onze tools raisen `ModelRetry` omdat ze ook direct door
een pydantic-ai-agent worden aangeroepen, en daar is het wél de juiste exceptie. Aan de
MCP-grens wordt hij daarom omgezet.

Aan de FastAPI-kant zet `main.py` beide op een 422 met het bericht in de body.

Zie https://pydantic.dev/docs/ai/mcp/client/ voor `tool_error_behavior`.
"""

from functools import wraps

from fastmcp.exceptions import ToolError
from pydantic_ai import ModelRetry


def as_tool_error(func):
    """Zet een `ModelRetry` uit de toolbody om in een `ToolError`.

    Alleen voor fouten die de tool zelf opwerpt, zoals een maatvoering die niet in het
    watersysteem past. Fouten uit de invoervalidators ontstaan eerder - bij het omzetten
    van de argumenten naar het model, buiten deze functie - en worden door FastMCP zelf
    gerapporteerd.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ModelRetry as exc:
            raise ToolError(str(exc)) from exc

    return wrapper
