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
    pmpQ_mtr = (1 + prcA / 100) * pmpQ # deze regel is afwijkend voor begen/afvoeren
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
    owA_mtr = (1 + prcA / 100) * owA # deze regel is afwijkend voor begen/afvoeren
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


