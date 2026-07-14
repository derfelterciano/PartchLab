#!/usr/bin/env python3

import polars as pl
from pathlib import Path
import unicodedata
import os
import shutil
from time import sleep


def clean_folder(path: str, delete_folder: bool = False) -> None:
    if os.path.exists(path):
        shutil.rmtree(path)
        sleep(0.5)

    if not delete_folder:
        os.makedirs(path, exist_ok=True)


def clean_column(name):
    replacements = {
        "µ": "u",
        "μ": "u",
        "²": "2",
        "³": "3",
    }

    for char, replacement in replacements.items():
        name = name.replace(char, replacement)

    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")
    name = name.strip()
    name = name.strip("_")

    return name


def parse_harmony_dataset(root: Path) -> Path:
    """
    Parses a harmony file directory and yields the cell analysis file

    Args:
        root (Path): Top level folder where all the harmony datasets are located

    Yields:
        Path, str: yields a file path to the cell analysis AND the harmony dataset name

    **NOTE:** The harmony file structure is:

        raw name/
        ├─ Evaluation/
        │  ├─ PlateResult.txt
        │  ├─ Objects_Population - NoBorderObj.txt (this is analysis file)
        │  ├─ .ExportDone_CellListsToTxt
        ├─ indexfile.txt

    """

    for f in root.glob("*/*"):
        if f.is_file() and not f.name.startswith(".") and f.name != "PlateResults.txt":
            # print(f)
            yield f, f.relative_to(root).parts[0]
