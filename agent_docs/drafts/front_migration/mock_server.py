from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
WEB_DIR = ROOT / "web"

app = FastAPI(title="Front Migration Mock", version="0.1.0")


def svg_placeholder(title: str, subtitle: str = "mock", *, width: int = 800, height: int = 600, color: str = "#0f172a", accent: str = "#65d7a4") -> bytes:
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_sub = subtitle.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <defs>
        <linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="{color}"/>
          <stop offset="100%" stop-color="#111827"/>
        </linearGradient>
      </defs>
      <rect width="100%" height="100%" fill="url(#g)"/>
      <rect x="48" y="48" width="{width - 96}" height="{height - 96}" rx="24" fill="rgba(255,255,255,0.05)" stroke="{accent}" stroke-width="2"/>
      <circle cx="{width * 0.75}" cy="{height * 0.28}" r="110" fill="{accent}" opacity="0.12"/>
      <rect x="90" y="160" width="220" height="280" rx="20" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.2)"/>
      <rect x="310" y="140" width="260" height="76" rx="12" fill="{accent}" opacity="0.25"/>
      <rect x="310" y="240" width="260" height="18" rx="9" fill="rgba(255,255,255,0.18)"/>
      <rect x="310" y="278" width="190" height="18" rx="9" fill="rgba(255,255,255,0.12)"/>
      <rect x="310" y="316" width="230" height="18" rx="9" fill="rgba(255,255,255,0.12)"/>
      <rect x="310" y="354" width="170" height="18" rx="9" fill="rgba(255,255,255,0.12)"/>
      <text x="90" y="520" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#f8fafc">{safe_title}</text>
      <text x="90" y="558" font-family="Arial, sans-serif" font-size="18" fill="rgba(255,255,255,0.7)">{safe_sub}</text>
    </svg>
    """
    return svg.strip().encode("utf-8")


PRODUCTS = [
    {
        "slug": "chateau-montrose-2021",
        "title": "Chateau Montrose 2021",
        "winery": "Maison Vignes",
        "color": "Красное",
        "category": "Сухое",
        "region": "Бордо",
        "grape": "Каберне Совиньон",
        "description": "Насыщенное красное вино с ягодными нотами, бархатистой текстурой и длинным финалом.",
    },
    {
        "slug": "vinea-alturas-blanc",
        "title": "Vinea Alturas Blanc",
        "winery": "Alturas Winery",
        "color": "Белое",
        "category": "Сухое",
        "region": "Долина",
        "grape": "Совиньон Блан",
        "description": "Свежий белый сорт с цитрусовым ароматом и ровной кислотностью.",
    },
    {
        "slug": "domaine-lune-rose",
        "title": "Domaine Lune Rosé",
        "winery": "Domaine Lune",
        "color": "Розовое",
        "category": "Сухое",
        "region": "Прованс",
        "grape": "Гренаш",
        "description": "Лёгкий розовый стиль с фруктовыми оттенками клубники и граната.",
    },
]


def mock_search_result() -> dict[str, Any]:
    top = PRODUCTS[0]
    return {
        "winner": {
            "product_id": top["slug"],
            "title": top["title"],
            "manufacturer": top["winery"],
            "description": top["description"],
            "image_url": "/api/image/chateau-montrose-2021",
            "dino_similarity": 0.933,
            "sift_score": 0.88,
            "inliers": 134,
            "inlier_ratio": 0.78,
        },
        "query_crop": "/api/detect/image/mock_query.png",
        "results": [
            {
                "product_id": p["slug"],
                "title": p["title"],
                "manufacturer": p["winery"],
                "image_url": f"/api/image/{p['slug']}",
                "dino_similarity": round(0.92 - idx * 0.03, 3),
                "sift_score": round(0.8 - idx * 0.07, 3),
                "inliers": 120 - idx * 10,
            }
            for idx, p in enumerate(PRODUCTS)
        ],
        "timings": {"total_ms": 1820, "embedding_ms": 420, "pgvector_ms": 90, "sift_ms": 240},
    }


@app.get("/")
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/index.html")


@app.get("/api/health/ping")
@app.get("/api/ready")
@app.get("/api/health/ready")
async def ready() -> dict[str, Any]:
    return {"ready": True, "database": True, "models": True, "gpu_name": "Mock GPU (demo)"}


@app.get("/api/samples")
async def samples() -> dict[str, Any]:
    return {
        "samples": [
            {"filename": "sample_wine_01.jpg", "title": "Sample 01", "cam_url": "/api/detect/image/sample_wine_01.jpg", "has_catalog": True},
            {"filename": "sample_wine_02.jpg", "title": "Sample 02", "cam_url": "/api/detect/image/sample_wine_02.jpg", "has_catalog": False},
            {"filename": "sample_wine_03.jpg", "title": "Sample 03", "cam_url": "/api/detect/image/sample_wine_03.jpg", "has_catalog": True},
        ]
    }


@app.post("/api/process_sample")
async def process_sample(payload: dict[str, Any]) -> dict[str, Any]:
    filename = payload.get("sample_filename", "sample.jpg")
    return {
        "filename": filename,
        "artifacts": {
            "original": f"/api/detect/image/{filename}",
            "dewarped": f"/api/detect/image/{filename}",
            "annotated": f"/api/detect/image/{filename}",
        },
        "comparison": {"raw": {"num_words": 24}, "dewarped": {"num_words": 46}, "gain": 22},
        "word_comparison": {"raw_words": 24, "dewarped_words": 46, "gain": 22},
    }


@app.post("/api/process_upload")
async def process_upload(file: UploadFile | None = File(None)) -> dict[str, Any]:
    filename = file.filename if file else "uploaded.jpg"
    return {
        "filename": filename,
        "artifacts": {
            "original": "/api/detect/image/uploaded.jpg",
            "dewarped": "/api/detect/image/uploaded.jpg",
            "annotated": "/api/detect/image/uploaded.jpg",
        },
        "comparison": {"raw": {"num_words": 18}, "dewarped": {"num_words": 37}, "gain": 19},
        "word_comparison": {"raw_words": 18, "dewarped_words": 37, "gain": 19},
    }


@app.get("/api/wine/{slug}")
async def wine_details(slug: str) -> dict[str, Any]:
    product = next((item for item in PRODUCTS if item["slug"] == slug), PRODUCTS[0])
    return {
        "slug": product["slug"],
        "name": product["title"],
        "winery": product["winery"],
        "color": product["color"],
        "category": product["category"],
        "region": product["region"],
        "grape": product["grape"],
        "description": product["description"],
        "image": f"/api/image/{product['slug']}",
    }


@app.get("/api/image/{slug}")
async def image(slug: str) -> Response:
    title = slug.replace("-", " ").title()
    payload = svg_placeholder(title, "mock product", width=900, height=1200, color="#1f2937", accent="#65d7a4")
    return Response(content=payload, media_type="image/svg+xml")


@app.get("/api/detect/files")
async def detect_files(q: str = "") -> list[str]:
    files = [f"wine-{i}.jpg" for i in range(1, 5)]
    query = (q or "").strip().lower()
    if query:
        files = [item for item in files if query in item.lower()]
    return files


@app.get("/api/detect/image/{filename}")
async def detect_image(filename: str) -> Response:
    title = filename.replace("_", " ").replace("-", " ")
    payload = svg_placeholder(title, "YOLO mock preview", width=1200, height=900, color="#111827", accent="#f59e0b")
    return Response(content=payload, media_type="image/svg+xml")


@app.post("/api/detect/predict")
async def predict_image(file: UploadFile | None = File(None), conf: float = Form(0.25)) -> dict[str, Any]:
    filename = file.filename if file else "mock.jpg"
    return {
        "filename": filename,
        "image_url": f"/api/detect/image/{filename}",
        "width": 1200,
        "height": 900,
        "mode": "RGB",
        "infer_ms": 180,
        "threshold": conf,
        "detections": [
            {"xtl": 150.0, "ytl": 200.0, "xbr": 760.0, "ybr": 760.0, "width": 610.0, "height": 560.0, "confidence": 0.92, "class_id": 0},
            {"xtl": 100.0, "ytl": 420.0, "xbr": 620.0, "ybr": 820.0, "width": 520.0, "height": 400.0, "confidence": 0.81, "class_id": 0},
        ],
        "segmentations": [{"points": [[180, 210], [720, 220], [760, 760], [180, 780]], "confidence": 0.88}],
    }


@app.get("/api/v1/search")
async def search_v1() -> JSONResponse:
    return JSONResponse(mock_search_result())


@app.post("/api/v1/search")
async def search_v1_post(file: UploadFile | None = File(None), k: int = Form(5)) -> JSONResponse:
    return JSONResponse(mock_search_result())


@app.post("/api/v1/search-from-crop")
async def search_from_crop(file: UploadFile | None = File(None), k: int = Form(5), augment: bool = Form(False)) -> JSONResponse:
    return JSONResponse(mock_search_result())


@app.get("/api/search")
async def search_legacy() -> JSONResponse:
    return JSONResponse(mock_search_result())


@app.get("/api/twins/clusters")
async def twin_clusters() -> dict[str, Any]:
    return {
        "total_clusters": 2,
        "total_products": 6,
        "clusters": [
            {
                "cluster_id": "cluster_1",
                "manufacturer": "Maison Vignes",
                "size": 3,
                "max_similarity": 0.97,
                "products": [
                    {"product_id": PRODUCTS[0]["slug"], "title": PRODUCTS[0]["title"], "manufacturer": PRODUCTS[0]["winery"], "crop_url": f"/api/image/{PRODUCTS[0]['slug']}", "slug": PRODUCTS[0]["slug"]},
                    {"product_id": PRODUCTS[1]["slug"], "title": PRODUCTS[1]["title"], "manufacturer": PRODUCTS[1]["winery"], "crop_url": f"/api/image/{PRODUCTS[1]['slug']}", "slug": PRODUCTS[1]["slug"]},
                    {"product_id": PRODUCTS[2]["slug"], "title": PRODUCTS[2]["title"], "manufacturer": PRODUCTS[2]["winery"], "crop_url": f"/api/image/{PRODUCTS[2]['slug']}", "slug": PRODUCTS[2]["slug"]},
                ],
            }
        ],
    }


app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("mock_server:app", host="0.0.0.0", port=8001, reload=False)
