#!/usr/bin/env python3
from pathlib import Path
import typer
from typing import Annotated
import logging
import shutil

from .preprocessing.preprocess import preprocess_aggregation
from .utils import clean_folder

logging.basicConfig(level=logging.INFO)


app = typer.Typer(
    name="Circadian Cell Painter Analyzer",
    help="This CLI runs the analysis needed for applying cell painting"
    "techniques onto circadian data",
    no_args_is_help=True,
    add_completion=False,
)

preprocess_data = typer.Typer(
    help="preprocesses cell painting data", no_args_is_help=True
)

app.add_typer(preprocess_data)


@preprocess_data.command()
def preprocess(
    input_path: Annotated[
        str, typer.Argument(help="path to data directory (tab delimited file)")
    ],
    output: Annotated[
        str,
        typer.Argument(
            help="output file name. " "(MUST END IN EITHER .parquet or .csv!"
        ),
    ],
    index_keys: Annotated[
        list[str],
        typer.Option(
            "--keys",
            "-k",
            help="specifies the index columns i.e. WellName, Timepoint, Row, "
            "or Column. You can specify more than 1 column",
        ),
    ],
):
    in_path = Path(input_path)
    out_path = Path(output)
    dump_dir = out_path.parent / ".temp_batches/"
    clean_folder(dump_dir)

    if in_path.is_file():
        preprocess_aggregation(in_path, index_keys, out_path, dump_dir)
    else:
        logging.error("Preprocess: this is something wrong with this input path!")
        shutil.rmtree(dump_dir)
        exit(1)

    # NOTE: We will figure this out later
    # if in_path.is_dir():
    #     for path in in_path.iterdir():
    #         if path.suffix in ('.tsv', '.txt'):
    #           pass
    # elif in_path.is_file():
    #     preprocess_aggregation(in_path, index_keys, out_path, dump_dir)
    # else:
    #     logging.error("Preprocess: this is something wrong with this input path!")
    #     shutil.rmtree(dump_dir)
    #     exit(1)

    shutil.rmtree(dump_dir)


if __name__ == "__main__":
    app()
