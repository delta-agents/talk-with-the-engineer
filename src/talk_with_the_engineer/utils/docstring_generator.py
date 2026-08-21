"""Docstringgeneratie voor de MCP-tools.

De docstring van een toolfunctie wordt door FastMCP de `description` van de tool. Die
description bevatte hier eerder ook de volledige parameterlijst en alle retourvelden,
opgebouwd uit de pydantic-modellen. Dat is duplicatie: FastMCP stuurt `inputSchema` en
`outputSchema` toch al mee, compleet met beschrijvingen, eenheden en grenzen per veld.

De prijs van die duplicatie was hoog. De description liep op tot ruim 5600 tekens, en
clients die tooldefinities comprimeren kapten hem af - in de praktijk precies over de
laatste parameters heen, waaronder `delta_h_available`, dat verplicht is en geen
standaardwaarde heeft. Een lezer die alleen de description zag, zag dus juist het veld
niet waarover hij moest beslissen.

Wat overblijft is de beschrijving plus het voorbeeld: het enige dat niet al in het schema
staat.

Het omgekeerde komt ook voor. Een client die de tooldefinities comprimeert kan juist het
*schema* uitkleden: waargenomen bij Claude Code, dat de veldbeschrijvingen weghaalde en de
`enum` van numerieke velden liet vallen, terwijl de tooldescription onaangetast doorkwam.
De server publiceert in beide gevallen hetzelfde volledige schema - dit valt buiten zijn
invloed. Wat wel binnen zijn invloed valt, is over welke kanalen de beslissende informatie
verdeeld is:

* de tooldescription, kort genoeg om niet afgekapt te worden - `SHARED_FOOTER` hieronder;
* het schema, met de details per veld, voor de client die het volledig doorgeeft;
* het antwoord zelf, in `assumptions`, want data wordt niet gecomprimeerd.

Alleen het laatste kanaal is echt onvoorwaardelijk. Maar de verdeling over die kanalen
is niet vrij: de description wordt gelezen als instructie, niet als documentatie.

Dat is gemeten, en het ging mis. Om de fallbackwaarden te bewaren nadat ze uit het schema
verdwenen, stonden ze een tijd lang voluit in `SHARED_FOOTER` - `time_of_year=summer,
percentage_open_water=2, ...`. Een agent nam dat rijtje over in zijn aanroep, samen met de
velden uit het voorbeeld, dat toen nog een volledig gevulde call was. Daarmee was
server-side elk veld opgegeven, bleef `assumptions` leeg bij elke aanroep, en presenteerde
het antwoord de standaardwaarden als gekozen invoer. Het duurste veld - het seizoen, hier
een factor 2,3 in de investering - verdween onderweg zelfs uit de opsomming.

De verdeling is daarom: de *waarden* staan in het schema en in het antwoord, de
description bevat alleen de gedragsregel. En het voorbeeld is de minimale geldige aanroep,
zodat het weglaten voordoet in plaats van invullen.
"""

from typing import Callable, TypeVar

T = TypeVar("T")

SHARED_FOOTER = (
    "Vul geen veld in dat je niet weet: laat het weg in plaats van het te schatten. De "
    "tool rekent dan met een vaste waarde en meldt in `assumptions` welke dat waren, met "
    "per veld wat de keuze doet. Geef die aannames door aan de gebruiker - ze verschuiven "
    "het antwoord aanzienlijk, en een geschatte waarde die je zelf invult verschijnt daar "
    "niet in."
)

# Ruim onder de grens waarboven clients afkappen; de vorige generator zat op 5600 tekens
# en verloor daar `delta_h_available` mee. `test_mcp_schema.py` bewaakt dit budget.
MAX_DESCRIPTION_CHARS = 1500


def auto_docstring(description: str = ""):
    """Zet de tooldescription: beschrijving plus, indien aanwezig, een invoervoorbeeld."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        input_model = None
        for param_name, param_type in getattr(func, "__annotations__", {}).items():
            if param_name != "return" and hasattr(param_type, "model_json_schema"):
                input_model = param_type
                break

        doc_parts = []
        if description:
            doc_parts.append(description.strip())

        if input_model is not None:
            example = generate_json_example(input_model)
            if example is not None:
                doc_parts.append("\nExample input:")
                doc_parts.append("```json")
                doc_parts.append(example)
                doc_parts.append("```")

        doc_parts.append("\n" + SHARED_FOOTER)

        existing_doc = func.__doc__ or ""
        func.__doc__ = "\n".join([existing_doc.strip(), *doc_parts]).strip()
        return func

    return decorator


def generate_json_example(model_class) -> str | None:
    """Geef het voorbeeld dat het model zelf meebrengt, of niets.

    Eerder werden hier waarden verzonnen op basis van het veldtype: "example_value" voor
    elke string, 10 voor elk getal. Dat leverde een voorbeeld op dat de tool zelf
    afwijst - `language: "example_value"`, `days_to_discharge: 10`, alle vier de
    afvoercapaciteitsvelden tegelijk - en een LLM die het overnam kreeg dus een
    foutmelding. Een fout voorbeeld is slechter dan geen voorbeeld.

    Nu wordt alleen het voorbeeld gebruikt dat in `model_config` staat onder
    `json_schema_extra["example"]`. Ontbreekt dat, dan komt er geen voorbeeldblok in de
    docstring. `test_mcp_schema.py` controleert dat elk voorbeeld ook echt geaccepteerd
    wordt.
    """
    import json

    extra = (model_class.model_config or {}).get("json_schema_extra") or {}
    example = extra.get("example") if isinstance(extra, dict) else None
    if not example:
        return None
    return json.dumps({"input": example}, indent=2)
