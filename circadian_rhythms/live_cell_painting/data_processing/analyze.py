#!/usr/bin/env python3

# %%

# This will be our official analysis

from IPython.display import display
from circadian_cell_painting import (
    detect,
    CosinorDetection,
    CosinorVisualize,
    OscillationResults,
)
import polars as pl
from pathlib import Path

# datasets
data_dir = Path(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/preprocessed_data"
)

# platemaps
pm_path = Path(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live"
    " Study/2026-03-16CellPaint_map.xlsx"
)
platemap = pl.read_excel(pm_path, engine="openpyxl")
# display(platemap)


analysis_results_dir = Path(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/results"
)

pickle_dir = Path("/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/pickles")

visual_results_dir = Path(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/visuals"
)

model = CosinorDetection(period=24, intervals=3, time_offset=24, start_index=1)

for dataset in data_dir.iterdir():
    print(dataset)

    file_name = dataset.stem
    print(file_name)

    out_file = analysis_results_dir / f"{file_name}._.RESULTS.parquet"

    result: OscillationResults = detect(
        file_path=dataset,
        platemap_path=platemap,
        out_file=out_file,
        well_column="WellName",
        feature_col="feature",
        timepoint_col="Timepoint",
        value_col="mean",
        stat="mean",
        correction_group=["cell line", "condition"],
        detector=model,
    )

    pickle_out = pickle_dir / f"{file_name}._.RESULT_OBJ.pickle"
    result.to_pickle(pickle_out)


# %%

for pickles, dataset in zip(pickle_dir.iterdir(), data_dir.iterdir()):

    result_obs = OscillationResults.load_pickle(pickles)

    dataset_name = dataset.stem
    visualize_out = visual_results_dir / dataset_name
    print(visualize_out)

    visualize = CosinorVisualize(result_obs)
    visualize.view(visualize_out)
