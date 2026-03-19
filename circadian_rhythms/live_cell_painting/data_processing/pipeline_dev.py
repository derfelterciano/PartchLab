# %% [markdown]
# # In this notebook we will actually be working on the pipeline for data processing!
#
# Theoretical planned steps:
# 1. collaps wells into mean, median, std. dev, quanitiles (.1, .25, .5, .75, .9) percentiles
# 2. for each feature and well apply the 2 pass sliding window average.
#     - technically we need to use a fourier transform to see the effects of our data
# 3. use jtk cycle for oscillation detection
# 4. use fourier transform on features to check for any distortion or artifacts in signal

# %%
import polars as pl
import duckdb as db
from pathlib import Path
from tqdm import tqdm

test_data = Path(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/analysis_ready_data/2026-03-10CelPaint_ChromaNoTreatDex.tsv"
)

# %%
lf = pl.scan_csv(test_data, separator="\t")

print(*lf.columns, sep="\n")

# %% [markdown]
# ## Let's try duckdb

# %%
con = db.connect(config={"threads": 15, "memory_limit": "32GB"})

# read file
rl = con.read_csv(
    path_or_buffer=str(test_data),
    delimiter="\t",
    parallel=True,
    na_values=["NaN", "nan", "NA", "N/A", "", "null", "NULL"],
)


feats = rl.columns
feat_cols = [c for c in feats if c not in ("WellName", "Timepoint")]

# print(*feat_cols, sep="\n")

rl.create_view("raw")

col_info = con.execute("DESCRIBE raw").pl()

varchar_cols = col_info.filter(pl.col("column_type") == "VARCHAR")[
    "column_name"
].to_list()
double_cols = col_info.filter(pl.col("column_type") != "VARCHAR")[
    "column_name"
].to_list()
feature_cols = [c for c in double_cols if c not in ("WellName", "Timepoint")]

# For VARCHAR columns, cast to DOUBLE (bad values become NULL)
# For already-DOUBLE columns, keep as is
select_exprs = (
    ['"WellName"', '"Timepoint"']
    + [
        f'TRY_CAST("{c}" AS DOUBLE) AS "{c}"'
        for c in varchar_cols
        if c not in ("WellName", "Timepoint")
    ]
    + [f'"{c}"' for c in feature_cols]
)
select_list = ",\n        ".join(select_exprs)

processed_data = con.execute(
    f"""
    SELECT
        WellName,
        Timepoint,
        feature,
        MEAN(value) AS mean,
        MEDIAN(value) as median,
        STDDEV(value) as stddev,
        QUANTILE_CONT(value, 0.00) AS q0,
        QUANTILE_CONT(value, 0.10) AS q10,
        QUANTILE_CONT(value, 0.25) AS q25,
        QUANTILE_CONT(value, 0.50) AS q50,
        QUANTILE_CONT(value, 0.75) AS q75,
        QUANTILE_CONT(value, 0.90) AS q90,
        QUANTILE_CONT(value, 1.00) AS q100
    FROM (
        UNPIVOT (
            SELECT {select_list} FROM raw
        )
        ON COLUMNS(* EXCLUDE (WellName, Timepoint))
        INTO NAME feature VALUE value
    )
    GROUP BY WellName, Timepoint, feature
    ORDER BY WellName, Timepoint, feature
"""
)

display(processed_data.pl().head(10))

# %% [markdown]
# ## Let's try polars!
#
# duckdb becam too complicated with aggregation when in polars this just a few lines

# %%
BATCH_SIZE = 500
all_cols = pl.scan_csv(test_data, separator="\t").collect_schema().names()
feats = [c for c in all_cols if c not in ("WellName", "Timepoint")]
batches = [feats[i : i + BATCH_SIZE] for i in range(0, len(feats), BATCH_SIZE)]
print(f"{len(feats)} features → {len(batches)} batches of {BATCH_SIZE}")

group_keys = ["WellName", "Timepoint"]

quantile_method = "linear"


batch_files = []
for i, batch in tqdm(enumerate(batches), total=len(batches), desc="batch progress"):
    # print(f"Batch {i+1}/{len(batches)}...")
    out = Path(f"./test_batches/batch{i}.parquet")

    aggr_exp = []
    for col in batch:
        aggr_exp.append(
            pl.struct(
                [
                    pl.col(col).mean().alias(f"mean"),
                    pl.col(col).median().alias(f"median"),
                    pl.col(col).std().alias(f"stddev"),
                    pl.col(col)
                    .quantile(0.00, interpolation=quantile_method)
                    .alias(f"q0"),
                    pl.col(col)
                    .quantile(0.10, interpolation=quantile_method)
                    .alias(f"q10"),
                    pl.col(col)
                    .quantile(0.25, interpolation=quantile_method)
                    .alias(f"q25"),
                    pl.col(col)
                    .quantile(0.50, interpolation=quantile_method)
                    .alias(f"q50"),
                    pl.col(col)
                    .quantile(0.75, interpolation=quantile_method)
                    .alias(f"q75"),
                    pl.col(col)
                    .quantile(0.90, interpolation=quantile_method)
                    .alias(f"q90"),
                    pl.col(col)
                    .quantile(1.00, interpolation=quantile_method)
                    .alias(f"q100"),
                ]
            ).alias(col)
        )

    print("Scanning and sinking")
    (
        pl.scan_csv(
            test_data, separator="\t", null_values=["NaN", "nan", "NA", "N/A", ""]
        )
        .select(group_keys + batch)
        .group_by(group_keys)
        .agg(aggr_exp)
        .unpivot(index=group_keys, variable_name="feature", value_name="stats")
        .with_columns(pl.col("stats").struct.unnest())
        .drop("stats")
        .sort(group_keys + ["feature"])
        .sink_parquet(out)
    )

    batch_files.append(out)

# %%
import glob

# read each file individually, cast, then concat
files = sorted(glob.glob("./test_batches/*.parquet"))

dfs = []
for f in files:
    df = pl.read_parquet(f).with_columns(
        [
            pl.col("mean").cast(pl.Float64),
            pl.col("median").cast(pl.Float64),
            pl.col("stddev").cast(pl.Float64),
            pl.col("q0").cast(pl.Float64),
            pl.col("q10").cast(pl.Float64),
            pl.col("q25").cast(pl.Float64),
            pl.col("q50").cast(pl.Float64),
            pl.col("q75").cast(pl.Float64),
            pl.col("q90").cast(pl.Float64),
            pl.col("q100").cast(pl.Float64),
        ]
    )
    dfs.append(df)

final = pl.concat(dfs).sort(["WellName", "Timepoint", "feature"])
# final.write_csv("/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/test_summaries.csv")
final.write_parquet(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/test_summaries.parquet"
)

# %%
# make sure that we have what have all the data
df = pl.read_parquet(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study/test_summaries.parquet"
)

display(df.select(["WellName", "Timepoint"]).unique().sort(["WellName", "Timepoint"]))

# %%
df = pl.read_parquet(
    "/home/derfelt/git_repos/PartchLab/circadian_rhythms/live_cell_painting/data_processing/test_batches/batch0.parquet"
)


# print(df.shape)

# display(df.select(['WellName']).unique())
# display(df)
