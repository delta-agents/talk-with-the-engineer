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
output = "uitvoer_mtrVasthouden.csv"

# VB polder
totA = 4000  # ha
owA = 0.035 * totA  # ha open water (3,5%)
ovA = totA - owA  # ha overig
pmpQ = 5  # m3/s capaciteit

# maatregel Vasthouden
dT = 2  # dagen vertraging
prcAlst = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]  # % oppervlak met vertraging
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


def clcVertraging(row):
    if row["drainage [l/s/ha]"] != "":
        return row["drainage [l/s/ha]"] / (1 + dT)
    return 0.0


def clcResterend(row):
    if row["drainage [l/s/ha]"] != "":
        return (1 - prcA / 100) * row["drainage [l/s/ha]"] + prcA / 100 * row[
            "drainage1_mtr [l/s/ha]"
        ]
    return 0.0


def clcQ_mtr(row):
    if row["drainage2_mtr [l/s/ha]"] != "":
        return row["drainage2_mtr [l/s/ha]"] * ovA / 1000
    return 0.0


totWlvl_mtr = 0


def clcWlevel_mtr(row):
    global totWlvl_mtr
    if totWlvl_mtr + (row["debiet_mtr [m3/s]"] - pmpQ) * 3600 / owA / 1e4 > 0:
        totWlvl_mtr += (row["debiet_mtr [m3/s]"] - pmpQ) * 3600 / owA / 1e4
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
    Qd1 = Qd_file["drainage [l/s/ha]"][0]
    Qd2 = Qd_file["drainage [l/s/ha]"][24]
    Qd3 = Qd_file["drainage [l/s/ha]"][48]
    Qd4 = Qd_file["drainage [l/s/ha]"][72]
    Qd5 = Qd_file["drainage [l/s/ha]"][96]
    Qd6 = Qd_file["drainage [l/s/ha]"][120]
    Qd7 = Qd_file["drainage [l/s/ha]"][144]
    Qd_file["drainage1_mtr [l/s/ha]"] = 0.0
    Qd_file["drainage1_mtr [l/s/ha]"][0:24] = Qd1 / (1 + dT)
    Qd_file["drainage1_mtr [l/s/ha]"][24:48] = Qd1 / (1 + dT) + Qd2 / (1 + dT)
    Qd_file["drainage1_mtr [l/s/ha]"][48:72] = (
        Qd1 / (1 + dT) + Qd2 / (1 + dT) + Qd3 / (1 + dT)
    )
    Qd_file["drainage1_mtr [l/s/ha]"][72:96] = (
        Qd2 / (1 + dT) + Qd3 / (1 + dT) + Qd4 / (1 + dT)
    )
    Qd_file["drainage1_mtr [l/s/ha]"][96:120] = (
        Qd3 / (1 + dT) + Qd4 / (1 + dT) + Qd5 / (1 + dT)
    )
    Qd_file["drainage1_mtr [l/s/ha]"][120:144] = (
        Qd4 / (1 + dT) + Qd5 / (1 + dT) + Qd6 / (1 + dT)
    )
    Qd_file["drainage1_mtr [l/s/ha]"][144:168] = (
        Qd5 / (1 + dT) + Qd6 / (1 + dT) + Qd7 / (1 + dT)
    )
    Qd_file["drainage1_mtr [l/s/ha]"][168:192] = Qd6 / (1 + dT) + Qd7 / (1 + dT)
    Qd_file["drainage1_mtr [l/s/ha]"][192:216] = Qd7 / (1 + dT)
    Qd_file["drainage2_mtr [l/s/ha]"] = Qd_file.apply(clcResterend, axis=1)
    Qd_file["debiet_mtr [m3/s]"] = Qd_file.apply(clcQ_mtr, axis=1)
    Qd_file["ws_mtr [m+ref]"] = Qd_file.apply(clcWlevel_mtr, axis=1)

    if writeTimeseries:
        Qd_file.to_csv(os.path.join(filepath, f"A{prcA}_{output}"), index=False)

    return Qd_file["ws_mtr [m+ref]"].max()


effect["dH_mtr [m]"] = effect["percA [%]"].apply(lambda x: clcMax(x, False))
effect.to_csv(os.path.join(filepath, output), index=False)
