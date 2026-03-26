# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 07:18:09 2026

@author: botterhuis
"""

# import math
import os
from pathlib import Path
import pandas as pd

filepath = Path(__file__).parent.as_posix()
filename = "drainage.csv"
output = "__hidden__uitvoer_mtrBergen.csv"

# VB polder
totA = 4000  # ha
owA = 0.035 * totA  # ha open water (3,5%)
ovA = totA - owA  # ha overig
pmpQ = 5  # m3/s capaciteit

# maatregel Vasthouden
dT = 2  # dagen vertraging
prcAlst = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]  # % toename oppervlak open water
maxMtrLst = [
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
    -9.99,
]  # max peiloverschreiding maatregel
effect = pd.DataFrame(
    list(zip(prcAlst, maxMtrLst)), columns=["percA [%]", "dH_mtr [m]"]
)


def clcQ_ref(row):
    if row["drainage [l/s/ha]"] != "":
        return row["drainage [l/s/ha]"] * ovA / 1000
    return 0.0


totWlvl_ref = 0


def clcWlevel_ref(row):
    global totWlvl_ref
    if totWlvl_ref + (row["debiet_ref [m3/s]"] - pmpQ) * 3600 / owA / 1e4 > 0:
        totWlvl_ref += (row["debiet_ref [m3/s]"] - pmpQ) * 3600 / owA / 1e4
    else:
        totWlvl_ref = 0
    return totWlvl_ref


totWlvl_mtr = 0


def clcWlevel_mtr(row):
    global totWlvl_mtr
    owA_mtr = (1 + prcA / 100) * owA
    if totWlvl_mtr + (row["debiet_ref [m3/s]"] - pmpQ) * 3600 / owA_mtr / 1e4 > 0:
        totWlvl_mtr += (row["debiet_ref [m3/s]"] - pmpQ) * 3600 / owA_mtr / 1e4
    else:
        totWlvl_mtr = 0
    return totWlvl_mtr


prcA = 0


def clcMax(x, writeTimeseries):
    global prcA
    prcA = x

    # referentie
    Qd_file = pd.read_csv(rf"{filepath}/{filename}", sep=",", encoding="latin1")
    Qd_file["debiet_ref [m3/s]"] = Qd_file.apply(clcQ_ref, axis=1)
    Qd_file["ws_ref [m+ref]"] = Qd_file.apply(clcWlevel_ref, axis=1)
    # maatregel
    Qd_file["ws_mtr [m+ref]"] = Qd_file.apply(clcWlevel_mtr, axis=1)

    if writeTimeseries:
        Qd_file.to_csv(os.path.join(filepath, f"A{prcA}_{output}"), index=False)

    return Qd_file["ws_mtr [m+ref]"].max()


def main():
    effect["dH_mtr [m]"] = effect["percA [%]"].apply(lambda x: clcMax(x, False))
    effect.to_csv(os.path.join(filepath, output), index=False)

# Done 
if __name__ == "__main__":
    main()