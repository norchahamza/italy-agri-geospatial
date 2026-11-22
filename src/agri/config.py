"""Configuration + path helpers."""
from __future__ import annotations
import os
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]


def _merge(base: dict, extra: dict) -> dict:
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(mode: str = "demo", path: str | Path | None = None) -> dict:
    cfg = yaml.safe_load(Path(path or ROOT / "config" / "sources.yml").read_text(encoding="utf-8"))
    _merge(cfg, (cfg.pop("mode_overrides", None) or {}).get(mode, {}))   # e.g. real: other years / ISTAT format
    cfg["mode"] = mode
    data_dir = Path(os.environ.get("AGRI_DATA_DIR", cfg["paths"]["data_dir"]))
    out_dir = Path(os.environ.get("AGRI_OUTPUT_DIR", cfg["paths"]["output_dir"]))
    cfg["paths"]["data_dir"] = data_dir if data_dir.is_absolute() else ROOT / data_dir
    cfg["paths"]["output_dir"] = out_dir if out_dir.is_absolute() else ROOT / out_dir
    cfg["fmt"] = os.environ.get("AGRI_TABLE_FORMAT", cfg["paths"]["table_format"])
    cfg["years"]["range"] = list(range(cfg["years"]["start"], cfg["years"]["end"] + 1))
    return cfg


def data_path(cfg: dict, *parts: str) -> Path:
    """data/<mode>/<parts...>"""
    return cfg["paths"]["data_dir"].joinpath(cfg["mode"], *parts)


def out_path(cfg: dict, *parts: str) -> Path:
    """outputs/<mode>/<parts...>"""
    p = cfg["paths"]["output_dir"].joinpath(cfg["mode"], *parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
