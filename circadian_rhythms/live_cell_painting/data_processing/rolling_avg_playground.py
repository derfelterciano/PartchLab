#!/usr/bin/env pytho3

# %% [markdown]

# Here we will inspect all the data from the
# aggregation ProcessLookupError

# %%
from tokenize import group
import polars as pl
from pathlib import Path
from IPython.display import display

# file_path = Path(
#     "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live Study"
#     "/preprocessed_data/2026-03-10CelPaint_ChromaNoTreatDex.parquet"
# )

file_path = Path(
    "/Users/dterciano/Desktop/PartchLabFiles/CircadianRhythms"
    "/Live Study/preprocessed_data/2026-03-10CelPaint_ChromaNoTreatDex.parquet"
)
print(file_path)

# %% [markdown]
### This will be for converting parquet to csv

# %%
lf = pl.scan_parquet(file_path)
lf.sink_csv(
    "/Users/dterciano/Desktop/PartchLabFiles/CircadianRhythms/Live"
    " Study/preprocessed_data/2026-03-10CelPaint_ChromaNoTreatDex.csv"
)


# %%
lf = pl.scan_parquet(file_path)
print(*lf.collect_schema().names(), sep="\n")
# display(lf.head(500).collect())

# %% [markdown]
## Lets do 2-pass detrendign static method

# %%
index_keys = ["WellName", "Timepoint"]
grouping_keys = ["WellName", "feature"]
stat_cols = [
    c
    for c in lf.collect_schema().names()
    if c not in (set(index_keys) | set(grouping_keys))
]
print(stat_cols)
window_size = 8

# first rolling avg pass
pass1 = [
    pl.col(stat)
    .rolling_mean(window_size, center=True, min_samples=window_size)
    .over(grouping_keys)
    .alias(f"{stat}_pass1")
    for stat in stat_cols
]

# second rolling avg pass
pass2 = [
    pl.col(f"{stat}_pass1")
    .rolling_mean(window_size, center=True, min_samples=window_size)
    .over(grouping_keys)
    .alias(f"{stat}_pass2")
    for stat in stat_cols
]

# subtract noise from raw signal
detrending_process = [
    (pl.col(stat) - pl.col(f"{stat}_pass2")).alias(stat) for stat in stat_cols
]

# remove temp cols
temp_cols = [f"{stat}_pass1" for stat in stat_cols] + [
    f"{stat}_pass2" for stat in stat_cols
]

# %%
# Lets process the expressions

result = (
    lf.sort(["WellName", "feature", "Timepoint"])
    .with_columns(pass1)
    .with_columns(pass2)
    .with_columns(detrending_process)
    .drop(temp_cols)
    .drop_nulls(subset=stat_cols)
    .sort(["WellName", "Timepoint", "feature"])
)
# print(result.select(["Timepoint"]).unique().sort("Timepoint").collect())
display(result.head(250).collect())
result.sink_parquet("detrend_data.parquet")


# %% [markdown]
## Let's figure out what fourier thinks of our analysis

# %%
import polars as pl
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from tqdm import tqdm

# NOTE: TAKE FOURIER TRANSFORM OF NOISE NOT CLEAN SIGNAL

# ── Config ────────────────────────────────────────────────────────────────────
TOP_N = 250
WELL = "F7"
STAT = "median"  # ← change this to 'median', 'stddev', 'q0', etc.
output_pdf = f"qc_fft_{WELL}_{STAT}.pdf"
source_path = Path(
    "/Users/dterciano/Desktop/PartchLabFiles/CircadianRhythms"
    "/Live Study/preprocessed_data/2026-03-11CelPaint_PhenovNoTreatDex_"
    "HARMONY_FIXED.parquet"
)

# ── Load data ─────────────────────────────────────────────────────────────────
df = (
    pl.scan_parquet(source_path)
    .filter(
        (pl.col("WellName") == WELL) & (~pl.col("feature").str.contains("Intensity"))
    )
    .select(["Timepoint", "feature", STAT])
    .sort(["feature", "Timepoint"])
    .collect()
)

features = df["feature"].unique().sort().to_list()
sampling_interval = 3
target_period = 24

# ── Compute FFT for all features ──────────────────────────────────────────────
fft_results = {}
for feat in features:
    signal = df.filter(pl.col("feature") == feat)[STAT].to_numpy()
    n = len(signal)
    fft = np.fft.rfft(signal)
    freqs = np.fft.rfftfreq(n, d=sampling_interval)
    amps = np.abs(fft) / n

    target_freq = 1 / target_period
    idx_24hr = np.argmin(np.abs(freqs - target_freq))

    fft_results[feat] = {
        "signal": signal,
        "freqs": freqs,
        "amps": amps,
        "amp_24": amps[idx_24hr],
        "periods": np.where(freqs > 0, 1 / freqs, np.inf),
    }

# rank and take top N
ranked = sorted(features, key=lambda f: fft_results[f]["amp_24"], reverse=True)
top_feats = ranked[:TOP_N]
timepoints = df.filter(pl.col("feature") == top_feats[0])["Timepoint"].to_numpy()
hours = timepoints * sampling_interval

# ── Generate PDF ──────────────────────────────────────────────────────────────
with PdfPages(output_pdf) as pdf:

    # ── Page 1: summary ranking of top 20 ────────────────────────────────────
    fig, ax = plt.subplots(figsize=(11, 8.5))
    top20 = ranked[:20]
    top20_amps = [fft_results[f]["amp_24"] for f in top20]
    short_names = [f[-60:] for f in top20]

    ax.barh(short_names[::-1], top20_amps[::-1], color="seagreen")
    ax.set_xlabel("24hr FFT Amplitude")
    ax.set_title(f"Top 20 Features by 24hr Amplitude — Well {WELL} | stat: {STAT}")
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # ── One page per feature ──────────────────────────────────────────────────
    for i, feat in enumerate(tqdm(top_feats, desc="Generating pages")):
        r = fft_results[feat]
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
        fig.suptitle(f"[{i+1}/{TOP_N}] {feat}", fontsize=8, wrap=True)

        # time series
        ax1.plot(
            hours,
            r["signal"],
            color="royalblue",
            linewidth=1.5,
            marker="o",
            markersize=3,
        )
        ax1.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        ax1.set_xlabel("Time (hours)")
        ax1.set_ylabel(f"Detrended {STAT}")
        ax1.set_title("Time Series")

        # FFT
        mask = (r["periods"] >= 4) & (r["periods"] <= 48)
        ax2.plot(r["periods"][mask], r["amps"][mask], color="firebrick", linewidth=1.5)
        ax2.axvline(24, color="gray", linewidth=1, linestyle="--", label="24hr")
        ax2.set_xlabel("Period (hours)")
        ax2.set_ylabel("Amplitude")
        ax2.set_title(f'FFT Spectrum  |  24hr amp: {r["amp_24"]:.4f}')
        ax2.legend(fontsize=8)

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    d = pdf.infodict()
    d["Title"] = f"FFT QC Report — Well {WELL} | {STAT}"
    d["Subject"] = "Circadian rhythm FFT exploration"

print(f"Done! PDF saved to {output_pdf}")
