#!/usr/bin/env python3
"""Dynamic int8 quantization of the SigLIP2 image encoder for CPU serving.

Only weight MatMuls are quantized (attention QK^T / attn·V stay fp32). A few MLP
layers carry activation outliers that break per-tensor uint8 activation quantization
(full int8: cosine vs fp32 ≈ 0.05); they are kept fp32 via ``--exclude``.

Sensitivity (cosine vs fp32 when only this node is int8, Dev-B crops):
  layers.0/mlp/fc1 0.03, layers.9/mlp/fc2 0.88, layers.0/mlp/fc2 0.94;
  all others ≥ 0.996.

Use the result for **queries only**; keep catalog embeddings from the fp32 model
(asymmetric: no rank changes on Dev-A/Dev-B, eval_119 R@5 equal to fp32).

  uv run python scripts/quantize_encoder.py \\
    --src bin/siglip2_wine_p1_epoch_3.onnx --dst bin/siglip2_wine_p1_epoch_3_int8.onnx
"""

from __future__ import annotations

import argparse
from pathlib import Path

from onnxruntime.quantization import QuantType, quantize_dynamic

_DEFAULT_EXCLUDE = (
    "/vision/encoder/layers.0/mlp/fc1/MatMul",
    "/vision/encoder/layers.0/mlp/fc2/MatMul",
    "/vision/encoder/layers.9/mlp/fc2/MatMul",
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src", type=Path, required=True, help="fp32 ONNX (not fp16)")
    p.add_argument("--dst", type=Path, required=True)
    p.add_argument(
        "--exclude",
        nargs="*",
        default=list(_DEFAULT_EXCLUDE),
        help="ONNX node names kept in fp32",
    )
    args = p.parse_args()

    quantize_dynamic(
        str(args.src),
        str(args.dst),
        weight_type=QuantType.QInt8,
        op_types_to_quantize=["MatMul", "Gemm"],
        nodes_to_exclude=args.exclude,
        extra_options={"MatMulConstBOnly": True},
    )
    size_mb = args.dst.stat().st_size / 1e6
    print(f"wrote {args.dst} ({size_mb:.0f} MB), fp32 nodes kept: {len(args.exclude)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
