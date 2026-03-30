#!/usr/bin/env python3

# We will be doing our detect our oscillations here

# %%
import polars as pl
from pathlib import Path
import numpy as np
from IPython.display import display
from scipy.optimize import curve_fit
from scipy.stats import f as f_dist
from numpy.typing import NDArray
from tqdm import tqdm
from statsmodels.stats.multitest import multipletests

file_path = Path(
    "/home/derfelt/PartchLabFiles/Circadian Rhythms/Live"
    " Study/preprocessed_data/2026-03-11CelPaint_PhenovNo"
    "TreatDex_HARMONY_FIXED.parquet"
)
print(file_path)
# %%
# this will be the defualt cosinor equation + the fitting function
# https://pmc.ncbi.nlm.nih.gov/articles/PMC3663600/#S4
# using the above paper to teach me


def cosinor(time: NDArray[np.float64], baseline: float, amplitude: float, phase: float):
    """Cosinor equation"""
    return baseline + (amplitude * np.cos(((2 * np.pi * time) / 24) - phase))


def fit_cosinor(timepoint: NDArray[np.float64], values: np.ndarray):
    try:
        popt, pcov = curve_fit(
            cosinor, timepoint, values, p0=[np.mean(values), np.std(values), 0]
        )
        residual_model = values - cosinor(timepoint, *popt)
        residual_null = values - np.mean(values)

        ss_model = np.sum(residual_model**2)
        ss_null = np.sum(residual_null**2)

        n = len(values)
        f_stat = ((ss_null - ss_model) / 2) / (ss_model / (n - 3))
        p_value = 1 - f_dist.cdf(f_stat, 2, n - 3)

        return {
            "baseline": popt[0],
            "amp": abs(popt[1]),
            "phase": popt[2] % (2 * np.pi),
            "p_value": p_value,
            "f_stat": f_stat,
            "ss_model": ss_model,
            "ss_null": ss_null,
            "fitted": cosinor(timepoint, *popt),
        }
    except RuntimeError:
        return None


# %%
# now lets retrieve some of our data
WELL = "G15"
STAT = "mean"

data = (
    pl.scan_parquet(file_path)
    .filter((pl.col("WellName") == WELL))
    .select(["Timepoint", "feature", STAT])
    .sort(["feature", "Timepoint"])
)

features = data.select("feature").unique().collect()["feature"].to_list()
time_points = (
    data.filter(pl.col("feature") == features[0])
    .collect()["Timepoint"]
    .to_numpy()
    .astype(np.float64)
) * 3

result = []
for feat in tqdm(features, desc="feature progess"):
    values = (
        data.filter(pl.col("feature") == feat)
        .collect()[STAT]
        .to_numpy()
        .astype(np.float64)
    )
    fit = fit_cosinor(time_points, values)
    if fit is not None:
        result.append(
            {
                "WellName": WELL,
                "feature": feat,
                "stat": STAT,
                "baseline": fit["baseline"],
                "amplitude": fit["amp"],
                "phase": fit["phase"],
                "p_value": fit["p_value"],
                "f_stat": fit["f_stat"],
                "ss_model": fit["ss_model"],
                "ss_null": fit["ss_null"],
            }
        )

result_df = pl.DataFrame(result)

# display(data.head(36).collect())

# %%

# now we need to adjust the p-values
ALPHA = 0.05
METHOD = "fdr_bh"
rejected, p_adjusted, _, _ = multipletests(
    result_df["p_value"].to_numpy(), alpha=ALPHA, method=METHOD
)

result_df = result_df.with_columns(pl.Series("p_adjusted", p_adjusted)).sort(
    "p_adjusted"
)

significant = result_df.filter(pl.col("p_adjusted") < ALPHA)

good_feats = significant["feature"].to_list()

display(significant)

# %%
print(good_feats)
# %%

import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

# get time series data for significant features only
plot_data = (
    data.collect()
    .filter(pl.col("feature").is_in(good_feats))
    .join(
        significant.select(["feature", "amplitude", "phase", "baseline", "p_adjusted"]),
        on="feature",
    )
)

with PdfPages(f"significant_features_{WELL}_{STAT}.pdf") as pdf:

    # page 1: summary heatmap of amplitudes
    fig, ax = plt.subplots(figsize=(11, max(4, len(good_feats) * 0.3)))
    heat_data = (
        significant.select(["feature", "amplitude", "phase", "p_adjusted"])
        .to_pandas()
        .set_index("feature")
    )
    sns.heatmap(heat_data, ax=ax, cmap="viridis", annot=True, fmt=".3f")
    ax.set_title(f"Significant Features Summary — Well {WELL} | {STAT}")
    plt.tight_layout()
    pdf.savefig(fig)
    plt.close(fig)

    # one page per feature — time series + fitted cosinor
    timepoints_hours = plot_data["Timepoint"].unique().sort().to_numpy() * 3
    t_fine = np.linspace(timepoints_hours.min(), timepoints_hours.max(), 500)

    for feat in tqdm(good_feats, desc="Plotting"):
        row = significant.filter(pl.col("feature") == feat)
        signal = (
            plot_data.filter(pl.col("feature") == feat)
            .sort("Timepoint")[STAT]
            .to_numpy()
        )
        p_adj = row["p_adjusted"][0]
        amp = row["amplitude"][0]
        phase = row["phase"][0]
        baseline = row["baseline"][0]

        fitted_fine = cosinor(t_fine, baseline, amp, phase)

        fig, ax = plt.subplots(figsize=(11, 4))
        ax.plot(
            timepoints_hours,
            signal,
            "-o",
            color="royalblue",
            markersize=4,
            label="data",
        )
        ax.plot(
            t_fine,
            fitted_fine,
            "-",
            color="firebrick",
            linewidth=2,
            label="cosinor fit",
        )
        ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
        ax.set_xlabel("Time (hours)")
        ax.set_ylabel(f"Detrended {STAT}")
        ax.set_title(
            f"{feat}\namp={amp:.4f}  phase={np.degrees(phase):.1f}°  p_adj={p_adj:.4e}"
        )
        ax.legend()
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

print(f"Done! {len(good_feats)} significant features plotted")
