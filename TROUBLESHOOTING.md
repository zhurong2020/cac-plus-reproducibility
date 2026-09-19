# Troubleshooting

Scoped to what this package can actually run into. Each entry is an incident that happened
during the work the manuscript reports, not a hypothetical.

## The vendor-frozen environment

`requirements-vendor-frozen-cu116.txt` pins the environment used for the cross-stack check
(Online Methods M9). Two things about it are worth stating plainly:

**It is not byte-identical to the vendor's own pin.** The vendor's `requirements.txt` at release
`v1.0.0` pins `torch==1.12.1+cu113`. This file pins `1.12.1+cu116`, because cu113 wheels do not
run on the driver of the host used here. Same PyTorch and MONAI versions, different CUDA build.
The manuscript states this in M9 rather than claiming a match.

**`torch.cuda.is_available()` returning True does not mean cuDNN will load.** On WSL2, torch 1.12
with cuDNN 8 dies with `Could not load library libcudnn_cnn_infer.so.8 ... libcuda.so: cannot open
shared object file` and core-dumps, after reporting CUDA as available. Fix:

```bash
export LD_LIBRARY_PATH=/usr/lib/wsl/lib:$LD_LIBRARY_PATH
```

## MONAI 1.5.1 removed `SwinUNETR(img_size=...)`

The vendor's inference code passes `img_size` to `SwinUNETR`. MONAI 1.5.1 removed that argument,
so the vendor code raises on a modern stack. `patches/monai_1.5.1_compatibility.patch` restores
it without touching the weights or the network. Apply it only on the modern stack; the
vendor-frozen stack needs no patch.

## The vendor's default slice batch size can silently exhaust a small card

The vendor processes 16 slices per forward pass. On a 6 GB card that peaks at 11.73 GiB of
allocation, which a Windows display driver satisfies by spilling into host memory rather than
failing: the GPU reports full utilisation, host memory drops by roughly 6 GB, and one acquisition
takes 246 s instead of 14.5 s. **No error is raised and no score changes.** Measured at batch 16,
8, 4 and 2: 246.3, 145.5, 14.5 and 14.5 s, at peak allocation 11.73, 6.17, 3.38 and 1.99 GiB,
with an Agatston score of 1062.0 in all four. If inference is inexplicably slow, lower the batch
size before looking anywhere else.

## `pydicom.read_file` was removed in pydicom 3.x

The vendor code calls it. In pydicom 2.4.4 `read_file` is `dcmread`, verified by source
inspection, so aliasing the name back restores the original call exactly. The decoupled scorer
does this; nothing else in this package reads DICOM.

## The scripts that need no data, and the one that does

`benchmarks/byte_identity_synthetic.py`, `benchmarks/speedup_realct.py`,
`analysis/spacing_audit.py` and `analysis/speedup_intervals.py` run from the files in this
repository with no download. `analysis/agreement_panel.py` needs two CSVs the reader obtains
from their own COCA access: this package redistributes no patient-level data and no per-case
values from that cohort, because its research-use agreement does not permit it.

`scripts/reproduce_all.py` runs the four that need nothing and reports the fifth as skipped.
