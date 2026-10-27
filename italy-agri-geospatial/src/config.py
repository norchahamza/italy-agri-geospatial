"""Project-wide settings. Change them here, not inside the modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"

YEAR_START, YEAR_END = 1992, 2022

# ESA CCI land-cover classes that count as cropland under each rule (three rules, see README).
CROPLAND_RULES = {
    "strict": {10, 11, 12, 20},            # rainfed + irrigated cropland
    "with_mosaic": {10, 11, 12, 20, 30},   # + cropland/natural vegetation mosaic (>50% cropland)
    "broad": {10, 11, 12, 20, 30, 40},     # + natural vegetation/cropland mosaic (<50% cropland)
}
