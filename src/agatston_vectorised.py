"""Vectorised (Tier 1+2) Agatston implementation — the CAC Plus optimisation.

Mathematically identical to ``agatston_vendor_ref.agatston_naive`` but replaces the
interpreted per-object loop with:
  - a single ``scipy.ndimage.label`` pass for connected components, and
  - ``numpy.bincount`` for per-object voxel counts,
processing all objects with vectorised array operations. This is the source of the
C2 speedup reported in the paper (median 2.87x synthetic / 1.97x real CT) with 100%
Agatston identity to the reference. The 5.87x this docstring carried until 2026-09-19
was withdrawn in manuscript v1.1.0: that benchmark passed the vendor an F-contiguous,
transposed CT while the production scorer receives a C-contiguous buffer, and the vendor
loop is strongly layout-sensitive.

Ported from cardiac-ai-cac ``cac_scorer/core/processing_optimized.py``
(``compute_agatston_optimized_tier1``), reduced to the scoring core.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def agatston_vectorised(hu: np.ndarray, mask: np.ndarray, spacing, min_object_voxels: int = 1) -> float:
    """Vectorised Agatston. Returns the same score as the naive reference, faster."""
    sx, sy, sz = spacing
    voxel_vol = sx * sy * sz / 3.0

    labeled, n = ndimage.label(mask > 0)
    if n == 0:
        return 0.0

    # per-object voxel counts in one vectorised pass
    region_sizes = np.bincount(labeled.ravel())
    valid = np.where(region_sizes > min_object_voxels)[0]
    valid = valid[valid > 0]  # drop background label 0
    if valid.size == 0:
        return 0.0

    # per-object peak HU via labeled maximum (vectorised over all labels at once)
    max_hu = ndimage.maximum(hu, labels=labeled, index=valid)

    total = 0.0
    for lab, object_max in zip(valid, np.atleast_1d(max_hu)):
        if object_max < 130:
            continue
        factor = (1 if object_max < 200 else
                  2 if object_max < 300 else
                  3 if object_max < 400 else 4)
        total += round(region_sizes[lab] * voxel_vol * factor)
    return float(total)
