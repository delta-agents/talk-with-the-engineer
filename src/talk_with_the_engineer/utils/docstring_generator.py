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

Alleen het laatste kanaal is echt onvoorwaardelijk. Daarom staat de enige aanname die
stilzwijgend fout kan gaan - een weggelaten veld dat toch is ingevuld - in alle drie.
"""

from typing import Callable, TypeVar

T = TypeVar("T")

SHARED_FOOTER = (
    "Elk veld dat je weglaat wordt ingevuld met een vaste waarde: time_of_year=summer, "
    "percentage_open_water=2, length_event_hrs=96, rainfall_regime=R, "
    "name_rainfall_pattern=p1c, days_to_discharge=3, days_to_retain_discharge=2. Dat "
    "verschuift het antwoord aanzienlijk. Deze waarden staan bewust niet als `default` in "
    "het schema - dan kan een client ze in de aanroep invullen en weet de server niet meer "
    "wat jij hebt weggelaten. De tool meldt in `assumptions` welke het heeft gebruikt; "
    "geef ze op zodra je ze kent."
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
