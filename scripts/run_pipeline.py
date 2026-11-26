#!/usr/bin/env python
"""End-to-end pipeline.   python scripts/run_pipeline.py --mode demo --steps all"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agri import pipeline  # noqa: E402
from agri.config import load_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["demo", "real"], default="demo")
    ap.add_argument("--steps", default="all", help=f"comma list from {pipeline.STEPS + ['climate']} or 'all'")
    ap.add_argument("--list-istat-dataflows", action="store_true")
    ap.add_argument("--skip-climate", action="store_true", help="real mode: do not download ERA5 during 'collect'")
    a = ap.parse_args()
    cfg = load_config(a.mode)

    if a.list_istat_dataflows:
        from agri.ingestion import istat
        istat.list_dataflows(cfg)
        return
    steps = pipeline.STEPS if a.steps == "all" else a.steps.split(",")
    pipeline.run(cfg, steps, skip_climate=a.skip_climate)


if __name__ == "__main__":
    main()
