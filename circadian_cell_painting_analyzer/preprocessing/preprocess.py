#!/usr/env/bin python3

from .aggregate import *


def preprocess_aggregation(
    input_data: Path, index_keys: list[str], out_file: Path, dump_path: Path
) -> None:
    paths = batch_summaries(input_data, index_keys, dump_path)
    paths = [str(p) for p in paths]
    _ = merge_batches(batch_files=paths, out_file=out_file, index_keys=index_keys)
    return None
