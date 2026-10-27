"""Land-cover change from two classified rasters (numpy arrays of ESA CCI class codes)."""
import numpy as np
import pandas as pd
from src.config import CROPLAND_RULES


def cropland_mask(classes: np.ndarray, rule: str = "strict") -> np.ndarray:
    """Boolean mask: True where the pixel is cropland under the chosen rule."""
    if rule not in CROPLAND_RULES:
        raise ValueError(f"Unknown rule '{rule}'. Choose from {list(CROPLAND_RULES)}")
    return np.isin(classes, list(CROPLAND_RULES[rule]))


def change_summary(classes_t0, classes_t1, rule="strict", pixel_area_ha=1.0) -> dict:
    """Persistence, gross gain, gross loss and net change of cropland between two dates (in ha)."""
    a, b = cropland_mask(classes_t0, rule), cropland_mask(classes_t1, rule)
    if a.shape != b.shape:
        raise ValueError("Rasters must have the same shape")
    persistence = (a & b).sum() * pixel_area_ha
    gain = (~a & b).sum() * pixel_area_ha
    loss = (a & ~b).sum() * pixel_area_ha
    return {"persistence_ha": persistence, "gain_ha": gain, "loss_ha": loss,
            "net_ha": gain - loss, "cropland_t0_ha": a.sum() * pixel_area_ha,
            "cropland_t1_ha": b.sum() * pixel_area_ha}


def transition_matrix(classes_t0, classes_t1, pixel_area_ha=1.0, classes=None) -> pd.DataFrame:
    """Area (ha) of each from-class (rows) to to-class (columns) transition."""
    a, b = np.asarray(classes_t0).ravel(), np.asarray(classes_t1).ravel()
    if a.shape != b.shape:
        raise ValueError("Rasters must have the same shape")
    classes = sorted(set(a) | set(b)) if classes is None else list(classes)
    idx = {c: i for i, c in enumerate(classes)}
    m = np.zeros((len(classes), len(classes)))
    for x, y in zip(a, b):
        if x in idx and y in idx:
            m[idx[x], idx[y]] += 1
    return pd.DataFrame(m * pixel_area_ha, index=classes, columns=classes)


def change_by_zone(classes_t0, classes_t1, zones: np.ndarray, rule="strict", pixel_area_ha=1.0) -> pd.DataFrame:
    """Same summary per zone (e.g. province ids rasterised on the same grid). Zone 0 or negative is ignored."""
    a, b = cropland_mask(classes_t0, rule).ravel(), cropland_mask(classes_t1, rule).ravel()
    z = np.asarray(zones).ravel()
    keep = z > 0
    a, b, z = a[keep], b[keep], z[keep]
    ids = np.unique(z)
    rows = []
    for zid in ids:
        s = z == zid
        rows.append({"zone": zid, "persistence_ha": (a[s] & b[s]).sum() * pixel_area_ha,
                     "gain_ha": (~a[s] & b[s]).sum() * pixel_area_ha,
                     "loss_ha": (a[s] & ~b[s]).sum() * pixel_area_ha})
    df = pd.DataFrame(rows)
    df["net_ha"] = df["gain_ha"] - df["loss_ha"]
    return df
