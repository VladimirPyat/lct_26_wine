#!/usr/bin/env python3
"""CPU latency / peak RSS benchmark for image-encoder ONNX models (batch 1).

Run one model per process so peak RSS is attributable:
  uv run python scripts/bench_encoder_cpu.py \\
    bin/siglip2_wine_p1_epoch_3_int8.onnx --threads 2
"""

from __future__ import annotations

import argparse
import resource
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("onnx", type=Path)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--input-size", type=int, default=256)
    p.add_argument("--runs", type=int, default=5)
    args = p.parse_args()

    so = ort.SessionOptions()
    so.intra_op_num_threads = args.threads
    so.inter_op_num_threads = 1
    t0 = time.perf_counter()
    sess = ort.InferenceSession(str(args.onnx), so, providers=["CPUExecutionProvider"])
    load_s = time.perf_counter() - t0

    x = np.random.randn(1, 3, args.input_size, args.input_size).astype(np.float32)
    name = sess.get_inputs()[0].name
    sess.run(None, {name: x})
    times = []
    for _ in range(args.runs):
        t = time.perf_counter()
        sess.run(None, {name: x})
        times.append(time.perf_counter() - t)
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print(
        f"{args.onnx.name:40s} threads={args.threads} load={load_s:.1f}s "
        f"lat_med={np.median(times) * 1000:.0f}ms lat_min={min(times) * 1000:.0f}ms "
        f"peak_rss={rss_mb:.0f}MB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
