# -*- coding: utf-8 -*-
"""
Created on Tue Mar 24 07:18:09 2026

@author: botterhuis
Edit: Haasnoot
"""


# --------------------------------------------------
# maatregel Vasthouden
# --------------------------------------------------


def clcQ_ref(row, ovA):
    if row["drainage [l/s/ha]"] != "":
        return row["drainage [l/s/ha]"] * ovA / 1000
    return 0.0


def clcWlevel_ref(row, owA, pmpQ, totWlvl_ref):
    if totWlvl_ref + (row["debiet_ref [m3/s]"] - pmpQ) * 3600 / owA / 1e4 > 0:
        totWlvl_ref += (row["debiet_ref [m3/s]"] - pmpQ) * 3600 / owA / 1e4
    else:
        totWlvl_ref = 0
    return totWlvl_ref


def clcWlevel_mtr(row, owA, pmpQ, prcA, totWlvl_mtr):
    pmpQ_mtr = (1 + prcA / 100) * pmpQ
    if totWlvl_mtr + (row["debiet_ref [m3/s]"] - pmpQ_mtr) * 3600 / owA / 1e4 > 0:
        totWlvl_mtr += (row["debiet_ref [m3/s]"] - pmpQ_mtr) * 3600 / owA / 1e4
    else:
        totWlvl_mtr = 0
    return totWlvl_mtr


def clcMax(x, Qd_file, prcA, totWlvl_ref, totWlvl_mtr, owA, ovA, pmpQ):
    prcA = x
    # referentie
    Qd_file["debiet_ref [m3/s]"] = Qd_file.apply(clcQ_ref, args=(ovA,), axis=1)
    Qd_file["ws_ref [m+ref]"] = Qd_file.apply(
        clcWlevel_ref, args=(owA, pmpQ, totWlvl_ref), axis=1
    )
    # maatregel
    Qd_file["ws_mtr [m+ref]"] = Qd_file.apply(
        clcWlevel_mtr, args=(owA, pmpQ, prcA, totWlvl_mtr), axis=1
    )

    return Qd_file["ws_mtr [m+ref]"].max()
