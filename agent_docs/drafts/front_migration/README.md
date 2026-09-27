# Front migration demo

This folder contains a copy of the current frontend version for UI review without the real backend.

## What it includes

- Mobile scanner / wine recognition flow
- Catalog list and product detail pages
- Add-product form mock
- Search-by-photo page with mocked OCR/search results
- Twin/duplicate cluster view
- Detection/segmentation test panel
- Studio-style dewarping workflow page

## What the mock server provides

The mock API is intentionally minimal and returns static JSON + SVG placeholder content so the frontend is visible and interactive without a real inference service.

## Required API endpoints

- `GET /api/ready` or `GET /api/health/ready`
- `GET /api/samples`
- `POST /api/process_sample`
- `POST /api/process_upload`
- `GET /api/wine/{slug}`
- `GET /api/image/{slug}`
- `GET /api/detect/files`
- `GET /api/detect/image/{filename}`
- `POST /api/detect/predict`
- `GET /api/v1/search`
- `POST /api/v1/search`
- `POST /api/v1/search-from-crop`
- `GET /api/twins/clusters`
- `GET /api/health/ping`

## Run locally

```bash
cd /work/lct2026prod/front_migration
python3 mock_server.py
```

Then open:

- `http://localhost:8001/` for the main scanner UI
- `http://localhost:8001/studio/` for the studio UI

All pages use the copied static assets from `web/`, so the styling is visible without any backend dependency.
