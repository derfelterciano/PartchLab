#!/usr/bin/env python

import pandas as pd, numpy as np
import os, sys
from time import time


def getPairwiseCorr(df: pd.DataFrame, method="pearson"):
    has_nan = np.any(np.isnan(df.values))
    has_inf = np.any(np.isinf(df.values))

    if method == "pearson" and not (has_nan or has_inf):
        df_cols = df.columns
        corrDf = np.corrcoef(df.T)
        corrDf = pd.DataFrame(corrDf, index=df_cols, columns=df_cols)
    else:
        corrDf = df.corr(method=method)

    corrDf_copy = corrDf.copy()
    corrDf_copy = corrDf_copy.where(
        np.tril(np.ones(corrDf_copy.shape), k=-1).astype(bool)
    )

    pairwiseDf = corrDf_copy.stack().reset_index()
    pairwiseDf.columns = ["pairA", "pairB", "corr"]

    return corrDf, pairwiseDf


def getHighCorrPair(corrRow, sortedCorrPairs):
    pairA = corrRow["pairA"]
    pairB = corrRow["pairB"]

    if sortedCorrPairs.get_loc(pairA) > sortedCorrPairs.get_loc(pairB):
        return pairA
    else:
        return pairB


def excludeFeats(
    cellDf: pd.DataFrame, method="pearson", threshold=0.9, features: list = "all"
):
    if features == "all":
        features = cellDf.columns.tolist()

    cellDf = cellDf[features]

    corrDf, pairwiseDf = getPairwiseCorr(df=cellDf, method=method)

    varCorSum = corrDf.sum().sort_values().index
    pairwiseDf = pairwiseDf[pairwiseDf["corr"] >= threshold]

    if pairwiseDf.shape[0] == 0:
        return []

    exclude = pairwiseDf.apply(lambda x: getHighCorrPair(x, varCorSum), axis=1)

    return list(set(exclude.tolist()))


class CommandLine:
    def __init__(self, inOpts=None) -> None:
        import argparse

        self.parser = argparse.ArgumentParser(
            description="Reduce the number of features in a given dataset",
            prog="featureReducer.py",
            prefix_chars="-",
            add_help="True",
            usage="python %(prog)s -[flag] <argument>",
        )

        self.parser.add_argument(
            "-i",
            "--input",
            required=True,
            action="store",
            nargs="?",
            type=str,
            help="Input path of cell data",
        )

        self.parser.add_argument(
            "-o",
            "--output",
            action="store",
            required=True,
            nargs="?",
            type=str,
            help="Output path of reduced features csv file",
        )
        self.parser.add_argument(
            "-t",
            "--threshold",
            action="store",
            required=False,
            nargs="?",
            type=float,
            default=0.9,
            help="Correlation threshold (def: 0.9)",
        )
        self.parser.add_argument(
            "-d",
            "--debug",
            required=False,
            action="store_true",
            default=False,
            help="Enables debug testing mode (Note: a full dataset must be given)",
        )

        if inOpts is None:
            self.args = self.parser.parse_args()
        else:
            self.args = self.parser.parse_args(inOpts)


def writeFeatures(feats: list, out: str):
    with open(out, "w") as f:
        print(*feats, sep="\n", file=f)


def main():
    cl = CommandLine()
    dfPath = cl.args.input
    # dfPath = "/mnt/c/Users/derfelt/Desktop/LokeyLabFiles/TargetMol/Datasets/1umData/TargetMol_DMSO+PMA_HistDiff_concat_UPDATED-20231026.csv"
    df = pd.read_csv(dfPath, index_col=0)

    featSubset1 = ["SER-Spot", "SER-Edge", "SER-Ridge", "SER-Dark"]
    featSubset2 = ["SER-Hole", "SER-Saddle", "SER-Bright"]

    basic = featSubset1 + featSubset2
    standard = featSubset1

    if cl.args.debug:
        basicDf = df.loc[:, ~df.columns.str.contains("|".join(basic))].copy()
        standardDf = df.loc[:, ~df.columns.str.contains("|".join(standard))].copy()

        basicFeatLen = basicDf.shape[1]
        standardFeatLen = standardDf.shape[1]
        fullFeatLen = df.shape[1]

        thresholds = [0.75, 0.8, 0.85, 0.9, 0.95, 0.99]

        featureSummaryDict = {
            f"extensive": [],
            f"standard": [],
            f"basic": [],
        }

        start = time()
        for thresh in thresholds:
            basicExclude = excludeFeats(cellDf=basicDf, threshold=thresh)
            standardExclude = excludeFeats(cellDf=standardDf, threshold=thresh)
            fullExclude = excludeFeats(cellDf=df, threshold=thresh)

            outPath = os.path.splitext(cl.args.output)[0]

            basicFeatsKept = list(set(basicDf.columns.tolist()) - set(basicExclude))
            writeFeatures(feats=basicFeatsKept, out=f"{outPath}_basic_{thresh}.txt")

            standardHeatsKept = list(
                set(standardDf.columns.tolist()) - set(standardExclude)
            )
            writeFeatures(
                feats=standardHeatsKept, out=f"{outPath}_standard_{thresh}.txt"
            )

            fullFeatsKept = list(set(df.columns.tolist()) - set(fullExclude))
            writeFeatures(feats=fullFeatsKept, out=f"{outPath}_full_{thresh}.txt")

            featureSummaryDict["basic"].append(basicFeatLen - len(basicExclude))
            featureSummaryDict["standard"].append(
                standardFeatLen - len(standardExclude)
            )
            featureSummaryDict["extensive"].append(fullFeatLen - len(fullExclude))

        print(f"Completion time: {time() - start}", file=sys.stderr)

        res = pd.DataFrame(featureSummaryDict, index=thresholds)
        res.columns = [
            f"Extensive ({fullFeatLen} features)",
            f"Standard ({standardFeatLen} features)",
            f"Basic ({basicFeatLen} features)",
        ]
        res.index.name = "thresholds"
        res.to_csv(cl.args.output)
    else:
        excludedFeats = excludeFeats(cellDf=df, threshold=cl.args.threshold)
        reducedDf = df.drop(columns=excludedFeats)
        reducedDf.to_csv(cl.args.output)

    # print(reducedDf)
    # reducedDf.to_csv("redFeat_cytominer.csv")
    # feats = 302


if __name__ == "__main__":
    main()
