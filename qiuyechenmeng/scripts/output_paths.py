"""Keep generated companion files in the book's organized directories."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def output_path(directory, filename):
    folder = ROOT / directory
    folder.mkdir(exist_ok=True)
    return folder / filename
