#!/usr/bin/env bash

# (python -m circadian_cell_painting_analyzer.cli preprocess \
#     '/Users/dterciano/Desktop/PartchLabFiles/CircadianRhythms/Live Study/analysis_ready_data/2026-03-10CelPaint_ChromaNoTreatDex.tsv' \
#     '/Users/dterciano/Desktop/PartchLabFiles/CircadianRhythms/Live Study/preprocessed_data/2026-03-10CelPaint_ChromaNoTreatDex.parquet' \
#     -k "WellName" -k "Timepoint") & \
# (python -m circadian_cell_painting_analyzer.cli preprocess \
#     '/Users/dterciano/Desktop/PartchLabFiles/CircadianRhythms/Live Study/analysis_ready_data/2026-03-11CelPaint_PhenovNoTreatDex_HARMONY_FIXED.tsv' \
#     '/Users/dterciano/Desktop/PartchLabFiles/CircadianRhythms/Live Study/preprocessed_data/2026-03-11CelPaint_PhenovNoTreatDex_HARMONY_FIXED.parquet' \
#     -k "WellName" -k "Timepoint") & \
# wait

(python -m circadian_cell_painting_analyzer.cli preprocess \
	'/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/analysis_ready_data/2026-03-10CelPaint_ChromaNoTreatDex.tsv' \
    '/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/preprocessed_data/2026-03-10CelPaint_ChromaNoTreatDex.parquet' \
	-k "WellName" -k "Timepoint")

(python -m circadian_cell_painting_analyzer.cli preprocess \
    '/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/analysis_ready_data/2026-03-11CelPaint_PhenovNoTreatDex_HARMONY_FIXED.tsv' \
    '/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/preprocessed_data/2026-03-11CelPaint_PhenovNoTreatDex_HARMONY_FIXED.parquet' \
    -k "WellName" -k "Timepoint")
