#!/usr/bin/env pytho3

# %% [markdown]

# Here we will inspect all the data from the
# aggregation ProcessLookupError

# %%
import polars as pl
from pathlib import Path
from IPython.display import display

file_path = (
    "/Users/dterciano/Desktop/PartchLabFiles/CircadianRhythms"
    "/Live Study/preprocessed_data/2026-03-10CelPaint_ChromaNoTreatDex.parquet"
)
print(file_path)


# %%
lf = pl.scan_parquet(file_path)
print(*lf.collect_schema().names(), sep="\n")
display(lf.head(500).collect())
