# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 07:18:09 2026

@author: botterhuis
Edit: Haasnoot
"""

import pandas as pd

# --------------------------------------------------
# maatregel discharge =  afvoeren
# --------------------------------------------------


def clcQ_ref(row, ovA):
    if row["drainage [l/s/ha]"] != "":
        return row["drainage [l/s/ha]"] * ovA / 1000
    return 0.0


def compute_wlevel_ref(Qd_file: pd.DataFrame, owA, pmpQ):
    totWlvl_ref = 0
    results = []
    for _, row in Qd_file.iterrows():
        delta = (row["debiet_ref [m3/s]"] - pmpQ) * 3600 / owA / 1e4
        if totWlvl_ref + delta > 0:
            totWlvl_ref += delta
        else:
            totWlvl_ref = 0
        results.append(totWlvl_ref)
    return results


def compute_wlevel_mtr_discharge(Qd_file: pd.DataFrame, owA, pmpQ, prcA):
    totWlvl_mtr = 0
    pmpQ_mtr = (1 + prcA / 100) * pmpQ  # deze regel is afwijkend voor begen/afvoeren
    results = []
    for _, row in Qd_file.iterrows():
        delta = (row["debiet_ref [m3/s]"] - pmpQ_mtr) * 3600 / owA / 1e4
        if totWlvl_mtr + delta > 0:
            totWlvl_mtr += delta
        else:
            totWlvl_mtr = 0
        results.append(totWlvl_mtr)
    return results


def clcMax_discharge(x, Qd_file: pd.DataFrame, owA, ovA, pmpQ):
    prcA = x
    # referentie
    Qd_file["debiet_ref [m3/s]"] = Qd_file.apply(clcQ_ref, args=(ovA,), axis=1)
    Qd_file["ws_ref [m+ref]"] = compute_wlevel_ref(Qd_file, owA, pmpQ)
    # maatregel
    Qd_file["ws_mtr [m+ref]"] = compute_wlevel_mtr_discharge(Qd_file, owA, pmpQ, prcA)

    return Qd_file["ws_mtr [m+ref]"].max()


# --------------------------------------------------------------------------------
# Store = Bergen
# --------------------------------------------------------------------------------


def compute_wlevel_mtr_store(Qd_file: pd.DataFrame, owA, pmpQ, prcA):
    totWlvl_mtr = 0
    owA_mtr = (1 + prcA / 100) * owA  # deze regel is afwijkend voor begen/afvoeren
    results = []
    for _, row in Qd_file.iterrows():
        delta = (row["debiet_ref [m3/s]"] - pmpQ) * 3600 / owA_mtr / 1e4
        if totWlvl_mtr + delta > 0:
            totWlvl_mtr += delta
        else:
            totWlvl_mtr = 0
        results.append(totWlvl_mtr)
    return results


def clcMax_store(x, Qd_file: pd.DataFrame, owA, ovA, pmpQ):
    prcA = x
    # referentie
    Qd_file["debiet_ref [m3/s]"] = Qd_file.apply(clcQ_ref, args=(ovA,), axis=1)
    Qd_file["ws_ref [m+ref]"] = compute_wlevel_ref(Qd_file, owA, pmpQ)
    # maatregel
    Qd_file["ws_mtr [m+ref]"] = compute_wlevel_mtr_store(Qd_file, owA, pmpQ, prcA)

    return Qd_file["ws_mtr [m+ref]"].max()


# --------------------------------------------------------------------------------
# maatregel retain = vasthouden
# --------------------------------------------------------------------------------


def compute_drainage1_mtr(Qd_file: pd.DataFrame, dT):
    """Compute the delayed drainage values per 24h block."""
    Qd1 = Qd_file["drainage [l/s/ha]"].iloc[0]
    Qd2 = Qd_file["drainage [l/s/ha]"].iloc[24]
    Qd3 = Qd_file["drainage [l/s/ha]"].iloc[48]
    Qd4 = Qd_file["drainage [l/s/ha]"].iloc[72]
    Qd5 = Qd_file["drainage [l/s/ha]"].iloc[96]
    Qd6 = Qd_file["drainage [l/s/ha]"].iloc[120]
    Qd7 = Qd_file["drainage [l/s/ha]"].iloc[144]

    factor = 1 / (1 + dT)
    Qd_file["drainage1_mtr [l/s/ha]"] = 0.0
    Qd_file.loc[0:24, "drainage1_mtr [l/s/ha]"] = Qd1 * factor
    Qd_file.loc[24:48, "drainage1_mtr [l/s/ha]"] = (Qd1 + Qd2) * factor
    Qd_file.loc[48:72, "drainage1_mtr [l/s/ha]"] = (Qd1 + Qd2 + Qd3) * factor
    Qd_file.loc[72:96, "drainage1_mtr [l/s/ha]"] = (Qd2 + Qd3 + Qd4) * factor
    Qd_file.loc[96:120, "drainage1_mtr [l/s/ha]"] = (Qd3 + Qd4 + Qd5) * factor
    Qd_file.loc[120:144, "drainage1_mtr [l/s/ha]"] = (Qd4 + Qd5 + Qd6) * factor
    Qd_file.loc[144:168, "drainage1_mtr [l/s/ha]"] = (Qd5 + Qd6 + Qd7) * factor
    Qd_file.loc[168:192, "drainage1_mtr [l/s/ha]"] = (Qd6 + Qd7) * factor
    Qd_file.loc[192:216, "drainage1_mtr [l/s/ha]"] = Qd7 * factor
    return Qd_file


def compute_drainage2_mtr(Qd_file: pd.DataFrame, prcA):
    """Combine original and delayed drainage based on measure percentage."""
    results = []
    for _, row in Qd_file.iterrows():
        if row["drainage [l/s/ha]"] != "":
            val = (1 - prcA / 100) * row["drainage [l/s/ha]"] + prcA / 100 * row[
                "drainage1_mtr [l/s/ha]"
            ]
        else:
            val = 0.0
        results.append(val)
    return results


def clcQ_mtr_retain(row, ovA):
    if row["drainage2_mtr [l/s/ha]"] != "":
        return row["drainage2_mtr [l/s/ha]"] * ovA / 1000
    return 0.0


def compute_wlevel_mtr_retain(Qd_file: pd.DataFrame, owA, pmpQ):
    totWlvl_mtr = 0
    results = []
    for _, row in Qd_file.iterrows():
        delta = (row["debiet_mtr [m3/s]"] - pmpQ) * 3600 / owA / 1e4
        if totWlvl_mtr + delta > 0:
            totWlvl_mtr += delta
        else:
            totWlvl_mtr = 0
        results.append(totWlvl_mtr)
    return results


def clcMax_retain(x, Qd_file: pd.DataFrame, owA, ovA, pmpQ, dT):
    prcA = x
    # referentie
    Qd_file["debiet_ref [m3/s]"] = Qd_file.apply(clcQ_ref, args=(ovA,), axis=1)
    Qd_file["ws_ref [m+ref]"] = compute_wlevel_ref(Qd_file, owA, pmpQ)
    # maatregel
    Qd_file = compute_drainage1_mtr(Qd_file, dT)
    Qd_file["drainage2_mtr [l/s/ha]"] = compute_drainage2_mtr(Qd_file, prcA)
    Qd_file["debiet_mtr [m3/s]"] = Qd_file.apply(clcQ_mtr_retain, args=(ovA,), axis=1)
    Qd_file["ws_mtr [m+ref]"] = compute_wlevel_mtr_retain(Qd_file, owA, pmpQ)

    return Qd_file["ws_mtr [m+ref]"].max()
