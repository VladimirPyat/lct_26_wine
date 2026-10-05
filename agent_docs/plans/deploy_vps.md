# Plan: VPS deployment (2 vCPU / 4 GB RAM) + dev/vps profiles + CI/CD

Status: steps 1–4 DONE (2026-10-05); docs + CI/CD → backlog TICKET-DEPLOY-001 / TICKET-DEPLOY-002.

Implementation notes (deviations from the sections below):
- Asset manifest lives in `scripts/deploy/assets.lock` (no new top-level `deploy/`); cache + state in
  `data/tmp/deploy/` (gitignored). Hosting = Google Drive (§0a), not GitHub Release.
- VPS compose project `vine-vps`, external DB volume `vine_vps_pgdata` (override `VINE_PG_VOLUME`) —
  separate from the local `vine` stack. Replacing an existing volume requires `--yes` (backup volume kept).
- One-command entry point: `scripts/deploy/deploy_vps.sh` (fetch → restore → `up -d --build` → `/health`).
- Concurrency gate is inside `DinoOnnxEncoder` (`compute.max_concurrent_inference`), not around YOLO.
- Local verification: CPU image 2.06 GB (GPU 6.89 GB); stack on test volume/port 8090 → `/health`
  `profile=vps`, owner_eval set 2 top-1 25/25, latency median 1.6 s (max 3.0 s, includes LLM OCR),
  app ≈1.13 GB, db ≈36 MB; restore rerun = skip, replace without `--yes` = refused, with `--yes` = backup + restore.
Context: int8 encoder ready — `bin/siglip2_wine_p1_epoch_3_int8.onnx`, `scripts/quantize_encoder.py`,
results in `data/tmp/quant_eval/` (batch-1 queries vs fp32 catalog: Dev-A/Dev-B/eval_119 R@5 = fp32).

## 0. Owner decisions (2026-10-05)

| # | Question | Decision |
|---|---|---|
| D1 | Where to host models + catalog bundle | GitHub Release `assets-vN` on the public repo; `wget` + sha256 check |
| D2 | DB delivery | **tar of the Docker Postgres volume** (`pgdata.tar.zst`) as a release asset |
| D3 | Where the Docker image is built | GitHub Actions → GHCR; VPS only pulls |
| D4 | Deploy trigger | `workflow_dispatch` button only |
| D5 | Domain / HTTPS | none for now: plain HTTP on server IP, app published on `:80` |
| D6 | Split PHOCR into a separate extra | no — CPU image keeps current deps, only `onnxruntime-gpu` → `onnxruntime` |

Notes:
- D1: repo is PUBLIC → fine-tuned model, catalog dump and images are public. Git LFS rejected
  (1 GB/month bandwidth, int8 model = 468 MB).
- D2 constraints (volume tar is a raw PG data dir):
  - same Postgres major + pgvector build on both sides → pin exact image tag in **both** compose files
    (e.g. `pgvector/pgvector:0.8.x-pg16`, not floating `pg16`); same CPU arch (x86_64);
  - export only from a cleanly stopped `db` container (no hot copy);
  - the source DB must hold **fp32** catalog embeddings (encoded locally on GPU): int8 queries vs
    fp32 catalog is the validated setup; int8-encoded catalog is worse;
  - the volume carries dev credentials/roles → VPS uses the same `vine` user; password is internal
    (port not published).
- D6: image stays large (PHOCR + datasets); PHOCR is not built on VPS (no CUDA → LLM OCR), weights
  are never downloaded there.

## 0a. assets-v1 (2026-10-05) — hosted on Google Drive (owner choice, replaces GitHub Release for now)

Scripted download URL (no `gdown`, works anonymously, verified with curl):
`https://drive.usercontent.google.com/download?id=<ID>&export=download&confirm=t`
(Drive is flaky → `curl --retry 4 --retry-all-errors --connect-timeout 30`, then `sha256sum -c`).

| Asset | Drive ID | Bytes | sha256 | Dest |
|---|---|---:|---|---|
| `siglip2_wine_p1_epoch_3_int8.onnx` | `1M6itqqPzi9UT-8QkuHM1N3zIqPgHikRE` | 490066998 | `e9c7d456a13172b0ea439ab8c5757a7b5c75bc9594cb7aa39d21f282be8c96cf` | `bin/` |
| `pgdata.tar.zst` | `1lRHCCUWxVG8tkDqUyWKz-EFW5XMRxsLY` | 33958780 | `e26a08648daa4cef8007ff4bbeb5fe8ad814385d48cc4f7d9d1885383eab6b39` | volume `vine_pgdata` |
| `images.tar.zst` (flat, 2091 webp) | `1jCET4T0Q5J09Q1c64piKoEtPPGacUX1i` (availability + size + zstd magic checked) | 131205944 | `d468f9bff29dfc032b39eb035d6316ddbe319a3451190a91723bd97a4b356310` | `static/wines/` |
| `yolo_detect_labels_2.onnx` | `1uKGYwkL7Ycm5QMgsWDl5KrTOpwwtCrtg` (from quickstart) | — | `60c92574e47021e2228e5b91e0d9dde8e018b1d2379e9696c5404551ac5b517c` | `bin/` |

Verified: model size matches local; `pgdata.tar.zst` from Drive sha256 == local; old `images.zip`
content == `static/wines/` (0 mismatches). Local files: `data/tmp/deploy/`.

## 1. Config profiles: `APP_ENV=dev|vps`

Switch: one line in `.env` (`APP_ENV=vps`) or env var. Default `dev` (= current behaviour).

Layout:
```
config/*.yaml                    # base = dev (unchanged)
config/profiles/vps/*.yaml       # overlays: only keys that differ, deep-merged over base
```

Changes:
1. `src/core/env.py` — move minimal `.env` loader from `src/db/session.py`; `app_env()` → `dev|vps`
   (validated; unknown value → fail fast).
2. `src/core/config.py::_load_yaml_mapping` — after base load, deep-merge
   `config/profiles/{APP_ENV}/{same filename}` if present (dicts merge, lists/scalars replace).
3. Log active profile at startup; add `profile` to `/health`.
4. Concurrency gate for the image encoder (new key `compute.max_concurrent_inference`, dev 0 = off,
   vps 1): `threading.Semaphore` around encoder/YOLO calls. Today requests go through
   `run_in_threadpool` (up to 40 threads) → parallel ORT runs oversubscribe 2 cores and spike RAM.
5. Tests: merge semantics, unknown profile, vps overlay values load.

VPS overlay contents:

| File | Keys |
|---|---|
| `database.yaml` | `dino_model_path: bin/siglip2_wine_p1_epoch_3_int8.onnx`, `dino.encode_batch_size: 1` |
| `compute_cropper.yaml` | `compute.device: cpu`, `ort_threads: 2`, `cv_threads: 1`, `max_concurrent_inference: 1`, `cropper.device: cpu` |
| `ocr_rerank.yaml` | `ocr.engine: llm` (auto-fallback already exists, explicit is clearer); optional −0.01 on `margin_tiers` / confidence after recalibration |
| `product.yaml` | none for now |

## 2. Docker

1. `Dockerfile` → build arg / two targets: `runtime-cpu` (`onnxruntime`, no CUDA libs, no
   `LD_LIBRARY_PATH`) and `runtime-gpu` (current). Same deps otherwise (D6). Models, catalog images,
   data are mounted, not baked.
2. `docker-compose.vps.yml`:
   - `db`: pinned `pgvector/pgvector:<exact tag>` (same as dev compose, D2), external volume
     `vine_pgdata` (created from the tar), `mem_limit: 512m`, `shared_buffers=128MB`,
     `max_connections=20`, port not published.
   - `app`: `ghcr.io/vladimirpyat/lct_26_wine:${VINE_TAG:-latest}`, `APP_ENV=vps`, `mem_limit: 2500m`,
     single uvicorn worker, ports `80:8080`, healthcheck, `restart: unless-stopped`,
     json-file log rotation.
   - cleanup of `data/tmp/search_queries` (10-day retention): daily run of
     `scripts/cleanup_search_queries.py` (host cron installed by bootstrap).
3. `.env.vps.example`: `APP_ENV=vps`, `DATABASE_URL=...@db:5432/vine`, `VINE_TAG`, LLM key names only.
4. Firewall (bootstrap): allow 22, 80 only.

## 3. Assets: models + catalog bundle

1. `deploy/assets.lock` (tracked) — **single source of truth for download links**:
   `name  url  sha256  dest` per line:
   `siglip2_wine_p1_epoch_3_int8.onnx → bin/`, `yolo_detect_labels_2.onnx → bin/`,
   `pgdata.tar.zst → deploy/state/`, `images.zip → static/wines/`.
   All four live in **one** release tag `assets-vN` (DB volume and images must come from the same
   catalog version). Google Drive links in `manuals/quickstart.md` stay for the dev/GPU manual path;
   they are not used by scripts (Drive >100 MB needs a confirm page / `gdown`, not plain `wget`).
   Site bottle images are **not** in git (`static/wines/*` ignored); they are byte-identical to
   `data/owner_database/images/` (existing `images.zip`), so the same zip is reused.
   Building the catalog on the VPS is rejected: images must be shipped anyway (they are the input),
   and fp16/fp32 encoding needs ~2.8–2.9 GB RSS + ~1 h on 2 vCPU (OOM risk on 4 GB).
   After restore, `scripts/catalog_prepare/verify_catalog_assets.py`-style check: DB slugs == files.
   **assets-v1 DB built 2026-10-05:** `data/tmp/deploy/pgdata.tar.zst` (34 MB, sha256
   `e26a08648daa4cef8007ff4bbeb5fe8ad814385d48cc4f7d9d1885383eab6b39`) from volume `vine_pgdata`
   (stopped cleanly): 2091 wines, `vector(1152)` SigLIP2 fp32-space (cos vs fp32 eval median 1.0000),
   alembic `0002_embedding_dim`, PG 16.15, pgvector 0.8.6, image
   `pgvector/pgvector:pg16@sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b`
   → pin this digest in `docker-compose.vps.yml`. Restore verified in a throwaway container.
2. `scripts/deploy/export_catalog.sh` (local, GPU machine):
   `docker compose stop db` → `docker run --rm -v <dev pgdata volume>:/data:ro -v $PWD/deploy/out:/out
   alpine tar -C /data -c . | zstd` → `pgdata.tar.zst`; `images.zip` of `static/wines/*.webp`; `sha256sum`;
   `docker compose start db`. Refuses if `db` image tag differs from the pinned one.
3. `scripts/deploy/publish_assets.sh` (local): `gh release create/upload assets-vN`, rewrite `assets.lock`.
4. `scripts/deploy/fetch_assets.sh` (server/CI): `wget -c` → `sha256sum -c` → unpack images;
   idempotent (skips files whose hash already matches).
5. `scripts/deploy/restore_db_volume.sh` (server): only if volume `vine_pgdata` is missing or
   `pgdata.tar.zst` hash differs from `deploy/state/pgdata.restored`:
   stop `db` → rename old volume to `vine_pgdata_bak_<date>` (no delete) → create volume →
   untar via `alpine` → start `db` → wait healthy → `alembic upgrade head` (no-op if schema matches).
   Catalog update = new tar + Deploy; the backup volume allows rollback.

## 4. One-shot server bootstrap

`scripts/deploy/vps_bootstrap.sh` (idempotent, Ubuntu/Debian):
1. Install Docker + compose plugin if missing; create 2 GB swap if none.
2. Clone / pull repo into `/opt/vine`; create `.env` from `.env.vps.example`
   (prompt for LLM key once).
3. `fetch_assets.sh` → `docker compose -f docker-compose.vps.yml pull` → `restore_db_volume.sh` →
   `up -d` (db + app); install cleanup cron; firewall 22/80.
4. Wait for `/health`; smoke `POST /v1/eval/predict` on one bundled image; print URL.
5. Optional: `scripts/bench_encoder_cpu.py` to record real latency on this CPU.

Result: `curl -fsSL .../vps_bootstrap.sh | bash` (or `git clone && ./scripts/deploy/vps_bootstrap.sh`).

## 5. GitHub Actions

1. `.github/workflows/ci.yml` (PR + push): `uv sync --extra ml --extra db --extra dev` →
   `ruff` → `mypy` → `pytest` (tests needing models/DB/GPU skipped via marker when assets absent).
2. `.github/workflows/deploy.yml` (`workflow_dispatch` only; inputs: ref, `restore_db: auto|skip`):
   - build `runtime-cpu` → push GHCR tags `sha-<short>` + `latest` (buildx cache);
   - SSH to VPS: `cd /opt/vine && git fetch && git checkout <ref> && scripts/deploy/fetch_assets.sh &&
     scripts/deploy/restore_db_volume.sh && VINE_TAG=sha-<short> docker compose -f docker-compose.vps.yml up -d`
     → health check; on failure re-up previous tag (stored in `deploy/state/current_tag`).
   - Secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` (deploy-only key). GHCR package public, or
     a read-only token on the VPS.
3. Model / catalog update flow: `export_catalog.sh` → `publish_assets.sh` → commit `assets.lock` →
   Deploy button.

## 6. Docs

- `manuals/deploy_vps.md` (RU): bootstrap, update, rollback, assets publishing, profiles.
- `manuals/configuration_guide.md`: profiles section; `README.md` + `manuals/index.md` links;
  `.env.example`: document `APP_ENV`.

## 7. Order of work

| Step | Scope | Depends on |
|---|---|---|
| 1 | Profiles + concurrency gate + tests (§1) | — |
| 2 | Dockerfile CPU target, compose.vps (+ pin db tag in dev compose), `.env.vps.example` (§2) | 1 |
| 3 | Assets scripts + first release (§3) | 2 (pinned db tag) |
| 4 | Bootstrap script, dry run on a clean VM/container (§4) | 2, 3 |
| 5 | CI + deploy workflows (§5) | 2, D3, D4, VPS secrets |
| 6 | Manuals (§6) | 1–5 |

Risks: RAM headroom (app ~1.2 GB + db ~0.3 GB + page cache; swap as guard); server CPU slower than
dev Ryzen (check with bench script; VNNI CPUs speed int8 up); LLM OCR latency/cost now on the
request path for low-margin queries.
