"""Extraheer de referentietabellen uit TttE_v03.xlsx naar tests/data/.

Eenmalig te gebruiken; de uitvoer is in de repo opgenomen zodat de testsuite niet van
Excel en openpyxl afhangt. Zie tests/data/README.md.
"""

import csv
from pathlib import Path

import openpyxl

ROOT = Path(__file__).parent.parent
WORKBOOK = ROOT / "scripts" / "scripts_Ton" / "TttE_v03.xlsx"
OUT = ROOT / "tests" / "data"

# blad -> (kolomnummers, kolomnamen); de sweeptabellen beginnen op rij 9
SWEEPS = {
    "bergen": ([8, 9], ["pct_open_water_fraction", "dh_max_m"]),
    "afvoeren": ([8, 9], ["pump_capacity_m3_per_sec", "dh_max_m"]),
    "vasthouden": ([11, 12], ["retention_pct", "dh_max_m"]),
}


def _read_until_blank(ws, cols, start_row):
    rows = []
    row = start_row
    while True:
        values = [ws.cell(row, col).value for col in cols]
        if any(value is None for value in values):
            return rows
        rows.append(values)
        row += 1


def main():
    workbook = openpyxl.load_workbook(WORKBOOK, data_only=True)
    OUT.mkdir(parents=True, exist_ok=True)

    for sheet, (cols, names) in SWEEPS.items():
        rows = _read_until_blank(workbook[sheet], cols, start_row=9)
        path = OUT / f"ton_sweep_{sheet}.csv"
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(names)
            writer.writerows(rows)
        print(f"{path.name}: {len(rows)} rijen")

    # de basis-afvoerreeks staat op elk blad in kolom A/B en begint op rij 3
    rows = _read_until_blank(workbook["bergen"], [1, 2], start_row=3)
    path = OUT / "ton_drainage_hourly.csv"
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["datetime", "drainage_l_s_ha"])
        writer.writerows([[str(stamp), value] for stamp, value in rows])
    print(f"{path.name}: {len(rows)} uren")


if __name__ == "__main__":
    main()
