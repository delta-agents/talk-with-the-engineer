"""Bouw demand_posts.json uit de werkopgave 2025 van het Deltaprogramma Zoetwater.

Bron: 'werkopgave 2025 herhalingstijden.xlsx', de getalsmatige zoetwateropgave van het
Deltaprogramma Zoetwater fase 3, afgeleid uit de Basisprognoses 2018. Dat bestand is een
lokale download en zit niet in de repo; zet het pad in WERKOPGAVE_XLSX of geef het als
argument mee. De uitvoer, `demand_posts.json`, is wel in de repo opgenomen.

Het tabblad `werkopgave_hht` bevat drie grootheden (Vraag, Levering, Tekort) maal zes posten
maal drie scenario's maal vier herhalingstijden maal 28 regio's, in Mm3 per zomer. Drie
identiteiten sluiten tot op de afronding van 1 Mm3 waarin het bestand is opgeslagen:

    Vraag - Levering = Tekort
    doorspoeling     = polders + boezem
    totaal           = doorspoeling + peilbeheer + beregening

**Wat hieruit wordt overgenomen zijn uitsluitend VERHOUDINGEN.** De werkopgave staat in Mm3
per DPZW-regio en onze eigen statistiek in mm over een gebied; zonder een gezaghebbende
tabel met regio-oppervlakken is dat niet om te rekenen, en die tabel is er niet. De
aandelen tussen posten, tussen regio's en tussen scenario's zijn dimensieloos en dus wel
overzetbaar. Er gaat daarom geen enkel absoluut volume de code in.

Drie afgeleide grootheden per (regio, scenario, herhaaltijd):

    demand_share     het aandeel van elke post in de totale watervraag
    coverage         Levering / Vraag per post: welke post werkelijk tekortkomt
    shortfall_share  het aandeel van elke post in het totale tekort

Gebruik:
    python scripts/build_demand_posts.py [pad/naar/werkopgave.xlsx]
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parents[1]
SRC = os.environ.get(
    "WERKOPGAVE_XLSX",
    str(
        REPO
        / "scratchpad"
        / "informatietool droogte"
        / "werkopgave 2025 herhalingstijden.xlsx"
    ),
)
OUT = REPO / "src/talk_with_the_engineer/core/stats/demand_posts.json"

SHEET = "werkopgave_hht"
POSTS = ("doorspoeling_boezem", "doorspoeling_polders", "peilbeheer", "beregening")
"""De vier posten die samen het totaal vormen.

`doorspoeling` zelf staat ook in het bestand en is de som van polders en boezem; die wordt
niet overgenomen, want dan zou het aandeel van doorspoeling twee keer in de som zitten.
"""

QUANTITIES = {"Vraag": "demand", "Levering": "delivered", "Tekort": "shortfall"}
NATIONAL = "Nederland"
"""De naam voor `Htotal`, de som over de zes hoofdregio's; die rij heeft er zelf geen."""


def region_key(name: str) -> str:
    """De regionaam als sleutel: geen spaties, geen accenten in de code.

    Zelfde vorm als de waterschapsnamen in de droogtestatistiek, zodat de twee lijsten in
    een schema naast elkaar leesbaar zijn.
    """
    cleaned = re.sub(r"[^0-9A-Za-z]+", "_", name.strip())
    return cleaned.strip("_")


def read_rows(path):
    """De rijen van `werkopgave_hht` als dicts, met de kopregel als sleutels."""
    book = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheet = book[SHEET]
    rows = sheet.iter_rows(values_only=True)
    header = [str(cell).strip() if cell is not None else "" for cell in next(rows)]
    value_column = next(name for name in header if name.startswith("waarde"))
    for row in rows:
        record = dict(zip(header, row))
        if record.get("variable") is None:
            continue
        yield record, value_column


def collect(path):
    """De ruwe volumes per regio, scenario, herhaaltijd, grootheid en post."""
    table = {}
    codes = {}
    for record, value_column in read_rows(path):
        variable = str(record["variable"])
        quantity, _, post = variable.partition("_")
        if quantity not in QUANTITIES or post not in ("totaal", *POSTS):
            continue
        code = str(record["regio_code"])
        name = record["regio_naam"]
        region = NATIONAL if code == "Htotal" else region_key(str(name))
        if code == "Stotal":
            # dezelfde som als Htotal, over de deelregio's opgeteld; een tweede naam voor
            # hetzelfde landelijke getal zou suggereren dat er twee landelijke opgaven zijn
            continue
        codes[region] = code
        period = int(str(record["herhalingstijd"]).lstrip("T"))
        key = (region, str(record["scenario"]), period)
        table.setdefault(key, {}).setdefault(QUANTITIES[quantity], {})[post] = float(
            record[value_column]
        )
    return table, codes


def shares(volumes):
    """De drie dimensieloze blokken uit de volumes van een (regio, scenario, herhaaltijd).

    `None` waar de noemer nul is: een regio zonder watervraag heeft geen postverdeling, en
    een regio zonder tekort heeft geen tekortverdeling. Nul zou daar een aandeel suggereren.

    **De aandelen delen door de som van de POSTEN en niet door het totaal uit het bestand.**
    Die twee verschillen tot enkele procenten omdat het bestand op hele Mm3 is afgerond, en
    aandelen die niet tot 1 sommeren zijn onbruikbaar zodra je er een vraag over verdeelt.
    Hoe grof die afronding voor deze regio is staat in `share_resolution`.
    """
    demand = volumes.get("demand", {})
    delivered = volumes.get("delivered", {})
    shortfall = volumes.get("shortfall", {})
    demand_parts = sum(demand.get(post, 0.0) for post in POSTS)
    shortfall_parts = sum(shortfall.get(post, 0.0) for post in POSTS)
    total_demand = demand.get("totaal", 0.0)

    def fraction(numerator, denominator, digits=4):
        return None if not denominator else round(numerator / denominator, digits)

    return {
        "demand_share": {
            post: fraction(demand.get(post, 0.0), demand_parts) for post in POSTS
        },
        "coverage": {
            post: fraction(delivered.get(post, 0.0), demand.get(post, 0.0))
            for post in POSTS
        },
        "shortfall_share": {
            post: fraction(shortfall.get(post, 0.0), shortfall_parts) for post in POSTS
        },
        "total_coverage": fraction(delivered.get("totaal", 0.0), total_demand),
        # de stapgrootte waarin een aandeel hier kan liggen: een regio met een vraag van
        # 6 Mm3 heeft aandelen in stappen van 17 procentpunt, en dan zegt het derde cijfer
        # niets meer
        "share_resolution": fraction(1.0, demand_parts, 3),
    }


def check_identities(table):
    """De drie identiteiten, op de volumes en niet op de aandelen.

    Ze sluiten tot op de afronding van 1 Mm3 waarin het bestand is opgeslagen, dus de
    tolerantie is 1 Mm3 per opgetelde term en niet een relatieve marge.
    """
    problems = []
    for key, volumes in sorted(table.items()):
        demand = volumes.get("demand", {})
        delivered = volumes.get("delivered", {})
        shortfall = volumes.get("shortfall", {})
        for name, block in (
            ("Vraag", demand),
            ("Levering", delivered),
            ("Tekort", shortfall),
        ):
            parts = sum(block.get(post, 0.0) for post in POSTS)
            if abs(parts - block.get("totaal", 0.0)) > 2.5:
                problems.append(f"{key} {name}: posten {parts} tegen totaal {block}")
        for post in ("totaal", *POSTS):
            balance = (
                demand.get(post, 0.0)
                - delivered.get(post, 0.0)
                - shortfall.get(post, 0.0)
            )
            if abs(balance) > 1.5:
                problems.append(f"{key} {post}: Vraag - Levering - Tekort = {balance}")
    return problems


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else SRC
    table, codes = collect(path)

    problems = check_identities(table)
    for problem in problems:
        print(f"  IDENTITEIT: {problem}")
    print(f"identiteiten die niet sluiten: {len(problems)}")

    regions = {}
    for (region, scenario, period), volumes in sorted(table.items()):
        block = regions.setdefault(region, {}).setdefault(
            scenario, {"return_periods": {}}
        )
        block["return_periods"][str(period)] = shares(volumes)
    for region, body in regions.items():
        body_codes = codes[region]
        for scenario in body:
            body[scenario]["region_code"] = body_codes

    payload = {
        "meta": {
            "source": (
                "Werkopgave 2025 met herhalingstijden, Deltaprogramma Zoetwater fase 3, "
                "afgeleid uit de Basisprognoses 2018 (BP18)"
            ),
            "status": (
                "grofstoffelijk gevalideerd volgens het bronbestand zelf; nadere validatie "
                "volgt"
            ),
            "unit": "dimensieloos (aandeel); de bron staat in Mm3 per zomer",
            "share_normalisation": (
                "de aandelen zijn gedeeld door de som van de vier posten en niet door het "
                "totaal uit het bestand; die twee verschillen tot enkele procenten door de "
                "afronding op hele Mm3. `share_resolution` zegt per regio hoe grof die "
                "afronding is: 0,17 betekent aandelen in stappen van 17 procentpunt"
            ),
            "why_only_ratios": (
                "de bron staat in Mm3 per DPZW-regio en dit model in mm over een gebied; "
                "zonder een gezaghebbende tabel met regio-oppervlakken is dat niet om te "
                "rekenen, en die tabel is niet gevonden. Verhoudingen tussen posten zijn "
                "dimensieloos en dus wel overzetbaar"
            ),
            "posts": {
                "doorspoeling_boezem": "doorspoelen van de boezem tegen verzilting",
                "doorspoeling_polders": "doorspoelen van de polders",
                "peilbeheer": (
                    "het opzetten van het peil EN het aanvullen ervan doordat water "
                    "verdampt en infiltreert; dat tweede stuk overlapt met de "
                    "open-waterverdamping die dit model al kent"
                ),
                "beregening": (
                    "beregening van gewassen; dit is de post die het verdampingstekort in "
                    "dit model bedient"
                ),
            },
            "climate": (
                "BP18 rust op de Deltascenario's 2015 en daarmee op KNMI'14; de "
                "droogtestatistiek in dit model rust op KNMI'23. Het cumulatief "
                "neerslagtekort onder KNMI'23 gedeeld door dat onder KNMI'14 loopt van "
                "0,94 tot 1,42 en valt in de meeste regio's hoger uit bij T5 en T10"
            ),
            "scenarios": (
                "REF2017 = referentie; S2050 en S2100 zijn het Stoom-scenario, in 2024 "
                "hernoemd naar Stoom/Vlug/Ruim/Warm"
            ),
            "return_period_method": (
                "per regio en scenario is een frequentiecurve afgeleid van het TOTALE "
                "watertekort; per herhaaltijd zijn de vier jaren met de dichtstbijzijnde "
                "herhaaltijd geselecteerd en per variabele gemiddeld. De herhaaltijd hoort "
                "dus bij het totaal en niet bij de losse post, en T20 is de bovengrens van "
                "wat de reeks draagt"
            ),
            "regions": (
                "zes hoofdregio's (H1-H6), 21 DPZW-deelregio's (S1-S21, waarvan S13 "
                "Waddeneilanden ontbreekt) en Nederland als som over de hoofdregio's. Deze "
                "indeling is vanaf 2023 gelijkgetrokken met de bestuurlijke regio-indeling "
                "en valt samen met de zes RDO-regio's"
            ),
            "caveats": [
                "BP24, de doorrekening met KNMI'23, is om modeltechnische redenen niet "
                "geschikt bevonden voor de knelpuntenanalyse; BP18 blijft de basis",
                "BP18 onderschat de zoutproblematiek in de Rijn-Maasmonding; voor "
                "beleidsanalyses hoort met hogere frequenties en duur van verzilting "
                "gerekend te worden",
                "voor zichtjaar 2100 draagt de reeks 32 jaar en wordt lineair "
                "geinterpoleerd; T20 is daar het gewogen gemiddelde van het T16,5- en het "
                "T33-tekort",
            ],
            "extracted": date.today().isoformat(),
            "build_script": "scripts/build_demand_posts.py",
        },
        "regions": regions,
    }

    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"geschreven: {OUT} ({OUT.stat().st_size / 1024:.0f} kB)")
    print(f"regio's: {len(regions)}")

    west = regions["West"]["REF2017"]["return_periods"]["20"]
    print(f"West REF2017 T20 aandelen: {west['demand_share']}")
    national = regions[NATIONAL]["REF2017"]["return_periods"]["20"]
    print(f"Nederland REF2017 T20 aandelen: {national['demand_share']}")

    for region, body in regions.items():
        for scenario, scenario_body in body.items():
            for period, block in scenario_body["return_periods"].items():
                parts = [
                    value
                    for value in block["demand_share"].values()
                    if value is not None
                ]
                if parts and abs(sum(parts) - 1.0) > 0.01:
                    print(
                        f"  SOM NIET 1: {region}/{scenario}/T{period}: {sum(parts):.3f}"
                    )


if __name__ == "__main__":
    main()
