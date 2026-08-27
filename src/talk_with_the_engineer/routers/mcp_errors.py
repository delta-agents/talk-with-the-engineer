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

import logging
from functools import wraps

from fastmcp.exceptions import ToolError
from pydantic import ValidationError
from pydantic_ai import ModelRetry

logger = logging.getLogger("AI_agent")


def as_tool_error(func):
    """Zet een fout uit de toolbody om in een `ToolError` die de aanroeper kan gebruiken.

    Alleen voor fouten die de tool zelf opwerpt, zoals een maatvoering die niet in het
    watersysteem past. Fouten uit de INVOERvalidators ontstaan eerder - bij het omzetten
    van de argumenten naar het model, buiten deze functie - en worden door FastMCP zelf
    gerapporteerd. Dat is daar ook het goede gedrag: die meldingen noemen het veld dat de
    beller zelf heeft ingevuld en de waarden die het wel aankan.

    Twee soorten, en het verschil zit in wie de fout kan lezen:

    * **`ModelRetry`** is een melding die voor de beller is geschreven, in het Nederlands en
      met een handelingsperspectief. Die gaat woordelijk mee.
    * **`ValidationError`** hoort hier niet te ontstaan. Komt hij er toch uit, dan is het
      een INTERN model dat afketst - `PolderState`, `SystemState` - en dan lekt de ruwe
      uitvoer de klassenaam, een veldnaam die niet is wat de beller invulde, en een link
      naar errors.pydantic.dev. Dat kwam er ook echt uit: `days_to_retain_discharge: -5`
      leverde "1 validation error for PolderState / days_to_retain" op (B12). De ruwe tekst
      gaat naar het log, waar hij thuishoort, en de aanroeper krijgt een melding waar hij
      iets mee kan.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ModelRetry as exc:
            raise ToolError(str(exc)) from exc
        except ValidationError as exc:
            logger.exception("intern model afgekeurd in %s", func.__name__)
            raise ToolError(
                "Deze combinatie van invoerwaarden levert een watersysteem op dat niet "
                "bestaat, en de tool kan er dus niet mee rekenen. Controleer de "
                "getalswaarden - een negatief aantal dagen, een oppervlak of capaciteit "
                "onder nul - en probeer het opnieuw met waarden binnen de grenzen die in "
                "het invoerschema staan."
            ) from exc

    return wrapper
