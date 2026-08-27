"""Bouw drought_statistics.json uit de STOWA 2025-23 per-waterschap Excels.

Bron: STOWA 2025-23, 'Droogtestatistiek KNMI'23-klimaatscenario's', bijlage
'Karakteristieke jaren Waterschappen'. Die Excels zijn een lokale download (niet in de
repo); zet het pad in SRC_DIR of geef het als argument mee. De uitvoer,
`drought_statistics.json`, is wel in de repo opgenomen.

Per (waterschap, scenario) staan 240 RACMO-jaren met per jaar het maximaal cumulatief
neerslagtekort [mm] en de bijbehorende GEV-fit-herhaaltijd [jaar]. Omdat elk punt (D, T) al
op de GEV-curve ligt, reproduceert interpolatie langs die punten de fit. We lezen het
neerslagtekort af bij een vaste set doel-herhaaltijden.

Dezelfde rijen dragen ook de minimale 7-daagse Rijn- en Maasafvoer, en daaruit komt het
tweede blok: de BESCHIKBAARHEIDSFRACTIE, het aanbod bij deze droogte ten opzichte van een
normaal jaar. Zie `PLAN_BRON_UIT_DE_DROOGTESTATISTIEK.md` Sec. 2 voor waarom die
conditioneel wordt geschat en niet bij dezelfde herhaaltijd wordt afgelezen. Kort: de
rivierafvoer heeft hier zijn eigen GEV-fit, dus die marginaal bestaat - maar twee marginalen
bij gelijke T in een scenario stoppen veronderstelt dat ze in hetzelfde jaar vallen, en dat
doen ze maar deels. Een T10-tekort samen met een T10-lage afvoer is eens per 34 jaar en niet
eens per 10.

Gebruik:
    python scripts/build_drought_statistics.py [pad/naar/Excels]
"""

import glob
import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import openpyxl

REPO = Path(__file__).resolve().parents[1]
SRC_DIR = os.environ.get(
    "DROUGHT_XLSX_DIR",
    str(REPO / "scratchpad" / "Karakterstieke jaren Waterschappen + handreiking"),
)
OUT = (
    REPO
    / "src/talk_with_the_engineer/tools/toolset_rules_of_thumb/drought_statistics.json"
)

TARGET_RETURN_PERIODS = [2, 5, 10, 25, 50, 100]
COL_DEFICIT = 1  # Maximaal cumulatief neerslagtekort (mm)
COL_RETURN = 3  # Herhaaltijd Neerslagtekort GEV-fit (jaren)
COL_DISCHARGE = {
    "Rijn": 9,  # Minimale 7-daagse Rijnafvoer (m3/s)
    "Maas": 11,  # Minimale 7-daagse Maasafvoer (m3/s)
}
SCENARIO_RENAME = {"Referentie Scenario": "Referentie"}
REFERENCE_SCENARIO = "Referentie"
SKIP_SHEETS = ("Handreiking (Lees mij) ", "30-jarige reeks")


def deficit_at_return_periods(pairs):
    """pairs: list of (T, D). Geef {T_target: D} via interpolatie langs de GEV-curve."""
    num = [
        (float(t), float(d))
        for t, d in pairs
        if isinstance(t, (int, float)) and isinstance(d, (int, float))
    ]
    by_t = {}
    for t, d in num:
        by_t.setdefault(t, []).append(d)
    ts = np.array(sorted(by_t))
    ds = np.array([np.mean(by_t[t]) for t in ts])
    logt = np.log(ts)
    out = {}
    for target in TARGET_RETURN_PERIODS:
        if target < ts.min() or target > ts.max():
            out[str(target)] = None  # niet extrapoleren buiten de reeks
        else:
            out[str(target)] = round(float(np.interp(np.log(target), logt, ds)), 1)
    return out


def _numbers(rows, column):
    """De numerieke waarden van een kolom; niet-numeriek is hier '<2' en geen fout."""
    return [float(row[column]) for row in rows if isinstance(row[column], (int, float))]


def source_availability(rows, normal, deficit_table):
    """De beschikbaarheidsfractie per doel-herhaaltijd, per rivier.

    Conditioneel geschat en niet bij gelijke herhaaltijd afgelezen. Niet omdat de marginaal
    ontbreekt - de rivierafvoer heeft in hetzelfde bestand zijn eigen GEV-herhaaltijd - maar
    omdat die bij gelijke T paren neerkomt op de aanname dat de twee gebeurtenissen in
    hetzelfde jaar vallen; gemeten is dat eens per 34 jaar en niet eens per 10. De vraag die
    bij het etiket "T10-droogte" hoort is een andere: "wat deed de rivier in de jaren waarin
    dit waterschap een tekort van deze zeldzaamheid had". Per jaar staan die twee naast
    elkaar, dus die vraag kan de data beantwoorden. Dat wordt een regressie in log-log:

        ln Q_min7 = a + b * ln T_tekort

    over de jaren met een numerieke herhaaltijd - dezelfde jaren die
    `deficit_at_return_periods` gebruikt, want '<2' staat voor een jaar onder de reeks.

    Twee klemmen, allebei omdat het model niets mag zeggen wat de statistiek niet draagt:

    * `b <= 0`. Bij een handvol combinaties (bijna allemaal Maas) is de helling licht
      positief, en dat is ruis bij `r` rond -0,3. Ongeklemd zou de tabel zeggen dat een
      zeldzamere droogte MEER aanvoer oplevert; geklemd zegt hij "de herhaaltijd doet hier
      niets".
    * `fractie <= 1`. Het normaaljaar is de mediaan over alle 240 jaren, natte inbegrepen,
      dus een tweejaarlijkse droogte komt binnen de ruis op 1 uit. Erboven leest in een
      droogtetool als een fout.

    `deficit_table` bepaalt waar een fractie mag staan: waar het tekort `null` is valt de
    herhaaltijd buiten de reeks van dit scenario, en dan hoort er ook geen aanbod te staan.
    """
    pairs = [
        (float(row[COL_RETURN]), row)
        for row in rows
        if isinstance(row[COL_RETURN], (int, float))
    ]
    out = {}
    for river, column in COL_DISCHARGE.items():
        usable = [
            (period, float(row[column]))
            for period, row in pairs
            if isinstance(row[column], (int, float))
        ]
        log_t = np.log(np.array([period for period, _ in usable]))
        log_q = np.log(np.array([value for _, value in usable]))
        slope, intercept = np.polyfit(log_t, log_q, 1)
        correlation = float(np.corrcoef(log_t, log_q)[0, 1])
        if slope > 0:
            slope, intercept = 0.0, float(log_q.mean())
        residual = log_q - (intercept + slope * log_t)
        fractions = {}
        for target in TARGET_RETURN_PERIODS:
            key = str(target)
            if deficit_table.get(key) is None:
                fractions[key] = None  # geen droogte hier, dus ook geen aanbod
                continue
            fitted = float(np.exp(intercept + slope * np.log(target)))
            fractions[key] = round(min(fitted / normal[river], 1.0), 3)
        out[river] = {
            "return_periods": fractions,
            "spread_factor": [
                round(float(np.exp(np.percentile(residual, 10))), 2),
                round(float(np.exp(np.percentile(residual, 90))), 2),
            ],
            "fit_r": round(correlation, 2),
        }
    return out


def normal_year_discharge(paths):
    """De mediane minimale 7-daagse afvoer in het huidige klimaat, per rivier [m3/s].

    De rivierafvoer is LANDELIJK: elk waterschapsbestand draagt dezelfde 240 jaren met
    dezelfde afvoeren, en alleen het neerslagtekort is regionaal. Het normaaljaar is daarom
    een getal per rivier en niet per waterschap, en het is de mediaan over alle 240 jaren van
    het Referentie-scenario - natte jaren inbegrepen, want dat is wat "normaal" betekent.

    Dat elk bestand hetzelfde zegt wordt hier gecontroleerd en niet aangenomen; liepen ze
    uiteen, dan zou de fractie stil van het waterschap afhangen waarmee we toevallig
    normaliseren.
    """
    medians = {}
    for path in paths:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet = next(
            name
            for name in wb.sheetnames
            if SCENARIO_RENAME.get(name, name) == REFERENCE_SCENARIO
        )
        rows = list(wb[sheet].iter_rows(min_row=2, values_only=True))
        for river, column in COL_DISCHARGE.items():
            medians.setdefault(river, []).append(
                float(np.median(_numbers(rows, column)))
            )
        wb.close()
    out = {}
    for river, values in medians.items():
        spread = max(values) - min(values)
        if spread > 1e-6:
            raise SystemExit(
                f"de {river}afvoer verschilt tussen de waterschapsbestanden "
                f"({spread:.3f} m3/s); dan is er geen landelijk normaaljaar"
            )
        out[river] = round(values[0], 1)
    return out


def region_key(path):
    return os.path.basename(path).replace("_resultaten_Karakteristieke_jaren.xlsx", "")


def build(src_dir):
    paths = sorted(
        glob.glob(os.path.join(src_dir, "*_resultaten_Karakteristieke_jaren.xlsx"))
    )
    if not paths:
        raise SystemExit(f"geen Excels gevonden in {src_dir!r}")
    normal = normal_year_discharge(paths)
    regions = {}
    for path in paths:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        scen = {}
        for sheet in wb.sheetnames:
            if sheet in SKIP_SHEETS:
                continue
            rows = list(wb[sheet].iter_rows(min_row=2, values_only=True))
            pairs = [(r[COL_RETURN], r[COL_DEFICIT]) for r in rows]
            deficit = deficit_at_return_periods(pairs)
            scen[SCENARIO_RENAME.get(sheet, sheet)] = {
                "return_periods": deficit,
                "source_availability": source_availability(rows, normal, deficit),
            }
        regions[region_key(path)] = scen
        wb.close()
    return regions, normal


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else SRC_DIR
    regions, normal = build(src_dir)
    doc = {
        "meta": {
            "source": "STOWA 2025-23, Droogtestatistiek KNMI'23-klimaatscenario's "
            "(Glas & Pezij (HKV), Van den Brink (KNMI))",
            "isbn": "978.94.6479.114.3",
            "indicator": "maximaal cumulatief neerslagtekort",
            "unit": "mm",
            "season": "1 april - 1 oktober (groeiseizoen)",
            "return_period_unit": "jaar",
            "value_meaning": "het maximaal cumulatief neerslagtekort [mm] bij de gegeven herhaaltijd",
            "method": "per RACMO-jaar (D, GEV-fit-herhaaltijd); D afgelezen bij de doel-herhaaltijd "
            "via interpolatie langs de GEV-curve in log(T); null = herhaaltijd buiten de "
            "240-jarige reeks",
            "scenarios": "Referentie = huidig klimaat (1991-2020); Hd/Hn/Ld/Ln + zichtjaar = "
            "KNMI'23 (H/L uitstoot, d/n droog/nat)",
            "regions": "per waterschap; ruimtelijke variatie noord-zuid > 30%, dus regiokeuze is "
            "niet optioneel",
            "caveats": [
                "RACMO-reeksen zijn synthetisch, niet historisch; weersvariatie tussen jaren is "
                "geen klimaatverandering",
                "een karakteristiek jaar dekt de gecombineerde droogte-indicatoren maar tot ~T5; "
                "hoger lopen de indicatoren uiteen",
                "twee indicatoren: het neerslagtekort (de vraag) en de minimale 7-daagse "
                "Rijn/Maas-afvoer (het aanbod); de 45-daagse neerslagsom en het aantal droge "
                "dagen staan hier niet in",
                "de beschikbaarheidsfractie is een index van de RIVIER en niet het volume bij "
                "een specifieke inlaat; het verdeelnetwerk, het Distributiemodel en de "
                "verdringingsreeks zitten er niet in",
            ],
            "source_availability": {
                "indicator": "minimale 7-daagse rivierafvoer",
                "unit": "fractie van een normaal jaar (dimensieloos)",
                "normal_year_m3_per_sec": normal,
                "normal_year_meaning": "mediaan van de minimale 7-daagse afvoer over de 240 "
                "RACMO-jaren van het Referentie-scenario; de rivierafvoer is landelijk en dus "
                "niet per waterschap",
                "method": "log-log-regressie van de minimale 7-daagse afvoer op de "
                "GEV-herhaaltijd van het NEERSLAGTEKORT in dit waterschap, over de jaren met "
                "een numerieke herhaaltijd; helling geklemd op <= 0 en fractie op <= 1",
                "why_not_the_same_return_period": "de rivierafvoer heeft zelf ook een "
                "GEV-fit, maar twee marginalen bij gelijke herhaaltijd paren veronderstelt dat "
                "ze in hetzelfde jaar vallen; gemeten correleren tekort en rivierafvoer met "
                "ongeveer -0,3 en is een T10-tekort met een T10-lage afvoer eens per 34 jaar "
                "(Hd_2100: 48). Dat scenario is geldig maar draagt dan een T10-etiket dat drie "
                "keer te mild is; de marginale lezing valt binnen de p10-p90-band hieronder",
                "spread_factor_meaning": "p10 en p90 van de residuen van de fit, als factor op "
                "de fractie; bij deze correlatie is een puntwaarde te weinig",
                "fit_r_meaning": "correlatie van de fit in log-log; hoe dichter bij nul, hoe "
                "minder de herhaaltijd over het aanbod zegt",
                "conservative": "de indicator is de DIEPSTE week; als index op een volume over "
                "een heel groeiseizoen valt hij aan de lage kant uit",
            },
            "extracted": date.today().isoformat(),
            "build_script": "scripts/build_drought_statistics.py",
        },
        "regions": regions,
    }
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    ref = (
        regions.get("Rijn_en_IJssel", {})
        .get("Referentie", {})
        .get("return_periods", {})
    )
    print(f"geschreven: {OUT}")
    print(f"regions: {len(regions)}")
    print(f"Rijn_en_IJssel Referentie neerslagtekort [mm] per T: {ref}")
    bad = 0
    for reg, scens in regions.items():
        for sc, body in scens.items():
            vals = [v for v in body["return_periods"].values() if v is not None]
            if any(a > b + 1e-6 for a, b in zip(vals, vals[1:])):
                bad += 1
                print(f"  NIET-MONOTOON: {reg}/{sc}: {body['return_periods']}")
    print(f"niet-monotone (region,scenario)-paren: {bad}")

    print(f"normaaljaar (mediane minimale 7-daagse afvoer): {normal}")
    src = (
        regions.get("Rijn_en_IJssel", {})
        .get("Referentie", {})
        .get("source_availability", {})
    )
    for river, body in src.items():
        print(f"Rijn_en_IJssel Referentie {river}: {body}")
    rising = 0
    for reg, scens in regions.items():
        for sc, body in scens.items():
            for river, block in body["source_availability"].items():
                vals = [v for v in block["return_periods"].values() if v is not None]
                if any(a < b - 1e-9 for a, b in zip(vals, vals[1:])):
                    rising += 1
                    print(f"  STIJGEND AANBOD: {reg}/{sc}/{river}: {vals}")
    print(f"(region,scenario,rivier) met stijgend aanbod: {rising}")


if __name__ == "__main__":
    main()
