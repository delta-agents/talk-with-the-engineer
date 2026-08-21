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
"""

from typing import Callable, TypeVar

T = TypeVar("T")


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
