# Referentiedata

Geëxtraheerd uit `scripts/scripts_Ton/TttE_v03.xlsx` zodat de testsuite niet van Excel en
`openpyxl` afhangt. Regenereren met `scripts/extract_ton_reference.py`.

## Referentiecasus

Alle bestanden hieronder horen bij één bui en één polder:

```
winter · T = 1000 jaar · 96 uur · patroon p1a · days_to_discharge = 4 · regime R
polder 4000 ha · 3,5 % open water (140 ha) · 5 m3/s gemaalcapaciteit
landoppervlak 3860 ha · waterstandstijging zonder maatregel 1,70233 m
```

Die parameters zijn niet in het rekenblad gedocumenteerd maar teruggerekend uit de
afvoerreeks: de L1-fout tussen `ton_drainage_hourly.csv` en de door
`get_rainfall` + `get_drainage` berekende reeks is 0,00 mm. Let op dat de defaults in
`RainfallInput` afwijken (`p1c`, `days_to_discharge=3`); met die defaults komt er 2,16 m
uit in plaats van 1,70 m.

## Bestanden

| bestand | inhoud |
|---|---|
| `ton_drainage_hourly.csv` | de basis-afvoerreeks, 288 uur, kolom B van elk blad |
| `ton_sweep_bergen.csv` | absolute fractie open water → maximale waterstandstijging |
| `ton_sweep_afvoeren.csv` | absolute gemaalcapaciteit [m3/s] → maximale waterstandstijging |
| `ton_sweep_vasthouden.csv` | percentage vastgehouden landoppervlak → maximale waterstandstijging, bij `days_to_retain = 2` |

`ton_sweep_bergen.csv` loopt door tot een fractie van 5,0 (500 % open water op een polder
van 4000 ha). Het rekenblad extrapoleert daar voorbij het fysiek haalbare; deze
implementatie rapporteert dat bereik als `INFEASIBLE`. De sweepwaarden blijven wel getest,
want de waterbalans zelf moet er nog steeds mee overeenkomen.

`ton_sweep_vasthouden.csv` is niet monotoon: het minimum ligt op 70 % (1,46183 m) en loopt
daarna terug op naar 1,51116 m bij 100 %. Dat is modelgedrag, geen fout in de data.
