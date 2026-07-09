#!/usr/bin/env bash

ccellpaint dct \
"/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/enVision/enVision_formatted/2026-06-01EnVision_20xRep._.FORMATTED.tsv" \
"/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/platemaps/2026_05_26_JUNE-EXP_plate_map.xlsx" \
"/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/DCT_test_run" \
-w "Well" -t "Timepoint" -e "CalcResultI" -g "MoleculeID" -g "Human_Readable_Name" \
-i 0.5 
