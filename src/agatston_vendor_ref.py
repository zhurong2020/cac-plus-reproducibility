"""Reference (naive) Agatston implementation.

This is the straightforward, un-optimised computation of the Agatston score from a
Hounsfield-unit volume and a binary calcium mask. It mirrors the vendor VA AI-CAC
per-voxel reference logic (Hagopian et al., MIT-licensed) and is used only to
demonstrate that the vectorised implementation in ``agatston_vectorised`` produces
byte-identical scores while running faster.

Agatston definition used (standard, area-weighted, normalised to 3 mm slice):
  - a connected calcified object contributes  round(volume_mm3 * density_factor)
  - volume_mm3 = voxel_count * (sx * sy * sz / 3.0)
  - density_factor by the object's peak HU:
        130-199 -> 1 ; 200-299 -> 2 ; 300-399 -> 3 ; >=400 -> 4
Objects with <= ``min_object_voxels`` voxels are dropped (vendor default = 1).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def agatston_naive(hu: np.ndarray, mask: np.ndarray, spacing, min_object_voxels: int = 1) -> float:
    """Naive per-object Agatston. Same math as the vectorised version, no bincount."""
    sx, sy, sz = spacing
    voxel_vol = sx * sy * sz / 3.0
    labeled, n = ndimage.label(mask > 0)  # 3D 6-connectivity (default structure)
    total = 0.0
    for lab in range(1, n + 1):
        region = labeled == lab
        count = int(region.sum())
        if count <= min_object_voxels:
            continue
        object_max = float(hu[region].max())
        if object_max < 130:
            continue
        factor = (1 if object_max < 200 else
                  2 if object_max < 300 else
                  3 if object_max < 400 else 4)
        total += round(count * voxel_vol * factor)
    return float(total)
