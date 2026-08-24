"""Bouw drought_statistics.json uit de STOWA 2025-23 per-waterschap Excels.

Bron: STOWA 2025-23, 'Droogtestatistiek KNMI'23-klimaatscenario's', bijlage
'Karakteristieke jaren Waterschappen'. Die Excels zijn een lokale download (niet in de
repo); zet het pad in SRC_DIR of geef het als argument mee. De uitvoer,
`drought_statistics.json`, is wel in de repo opgenomen.

Per (waterschap, scenario) staan 240 RACMO-jaren met per jaar het maximaal cumulatief
neerslagtekort [mm] en de bijbehorende GEV-fit-herhaaltijd [jaar]. Omdat elk punt (D, T) al
op de GEV-curve ligt, reproduceert interpolatie langs die punten de fit. We lezen het
neerslagtekort af bij een vaste set doel-herhaaltijden.

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
OUT = REPO / "src/talk_with_the_engineer/tools/toolset_rules_of_thumb/drought_statistics.json"

TARGET_RETURN_PERIODS = [2, 5, 10, 25, 50, 100]
COL_DEFICIT = 1          # Maximaal cumulatief neerslagtekort (mm)
COL_RETURN = 3           # Herhaaltijd Neerslagtekort GEV-fit (jaren)
SCENARIO_RENAME = {"Referentie Scenario": "Referentie"}
SKIP_SHEETS = ("Handreiking (Lees mij) ", "30-jarige reeks")


def deficit_at_return_periods(pairs):
    """pairs: list of (T, D). Geef {T_target: D} via interpolatie langs de GEV-curve."""
    num = [(float(t), float(d)) for t, d in pairs
           if isinstance(t, (int, float)) and isinstance(d, (int, float))]
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


def region_key(path):
    return os.path.basename(path).replace("_resultaten_Karakteristieke_jaren.xlsx", "")


def build(src_dir):
    regions = {}
    paths = sorted(glob.glob(os.path.join(src_dir, "*_resultaten_Karakteristieke_jaren.xlsx")))
    if not paths:
        raise SystemExit(f"geen Excels gevonden in {src_dir!r}")
    for path in paths:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        scen = {}
        for sheet in wb.sheetnames:
            if sheet in SKIP_SHEETS:
                continue
            ws = wb[sheet]
            pairs = [(r[COL_RETURN], r[COL_DEFICIT])
                     for r in ws.iter_rows(min_row=2, values_only=True)]
            scen[SCENARIO_RENAME.get(sheet, sheet)] = {
                "return_periods": deficit_at_return_periods(pairs)
            }
        regions[region_key(path)] = scen
        wb.close()
    return regions


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else SRC_DIR
    regions = build(src_dir)
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
                "alleen de indicator neerslagtekort; de andere STOWA-indicatoren (45-daagse som, "
                "droge dagen, Rijn/Maas-afvoer) staan hier niet in",
            ],
            "extracted": date.today().isoformat(),
            "build_script": "scripts/build_drought_statistics.py",
        },
        "regions": regions,
    }
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")

    ref = regions.get("Rijn_en_IJssel", {}).get("Referentie", {}).get("return_periods", {})
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


if __name__ == "__main__":
    main()
