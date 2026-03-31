#!/usr/bin/env python3

# %%

# We will use this for the analysis library

from IPython.display import display
from circadian_cell_painting_analyzer.osc_detection.detect import detect
from circadian_cell_painting_analyzer.osc_detection.cosinor import CosinorDetection
from circadian_cell_painting_analyzer.utils import OscillationResults
import polars as pl
from pathlib import Path

data_path = Path(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/"
    "preprocessed_data/2026-03-11CelPaint_PhenovNoTreatDex_HARM"
    "ONY_FIXED.parquet"
)
pm_path = Path(
    "/home/derfelt/PartchLabFiles/Circadian"
    " Rhythms/Live Study/2026-03-16CellPaint_map.xlsx"
)

out_path = Path(
    "/home/derfelt/PartchLabFiles/Circadian"
    " Rhythms/Live Study/results/2026-03-11CelPaint_PhenovNoTreatDex_HARM"
    "ONY_FIXED._.RESULTS.parquet"
)

pm = pl.read_excel(pm_path, engine="openpyxl")
print(pm)

# %%

model = CosinorDetection(period=24, intervals=3)

result: OscillationResults = detect(
    file_path=data_path,
    platemap_path=pm,
    out_file=out_path,
    well_column="WellName",
    feature_col="feature",
    timepoint_col="Timepoint",
    value_col="mean",
    stat="mean",
    correction_group=["cell line", "condition"],
    detector=model,
)

# %%
if result is not None:
    print(result)
    # print(result.scan_results().head(2).collect())
# %%
lf = pl.scan_parquet(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/results/2026-03-11CelPaint_PhenovNoTreatDex_HARMONY_FIXED._.RESULTS.parquet"
)

display(lf.head(10).collect())
# %%
result.to_pickle(
    Path(
        "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live "
        "Study/pickles/2026-03-11CelPaint_PhenovNoTreatDex_HARM"
        "ONY_FIXED._.RESULT_OBJ.pickle"
    )
)

# %%

detection_results = OscillationResults.load_pickle(
    Path(
        "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live "
        "Study/pickles/2026-03-11CelPaint_PhenovNoTreatDex_HARM"
        "ONY_FIXED._.RESULT_OBJ.pickle"
    )
)

print(detection_results.correction_group)
display(detection_results.scan_results().filter(pl.col("p_adjusted") <= 0.05).collect())
