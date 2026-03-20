#!/usr/bin/env python3
"""
A file of utilitis for this project
"""

from pathlib import Path
import shutil
from time import sleep


def clean_folder(dir: Path) -> None:
    if dir.exists():
        shutil.rmtree(dir)
        sleep(0.5)
    dir.mkdir(parents=True, exist_ok=True)
