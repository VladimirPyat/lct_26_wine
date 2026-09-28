// Demo «shops nearby» map (FIX-WEB-02): 3×3 OSM tiles around the user (or central Moscow),
// random shops with random prices. No backend; tile host approved for this demo only.

const TILE_HOST = "https://tile.openstreetmap.org";
const TILE_SIZE = 256;
const ZOOM = 15;
const GRID = 3;
const FALLBACK_CENTER = { lat: 55.7558, lon: 37.6173 };
const GEO_TIMEOUT_MS = 3000;
const SHOPS_MIN = 6;
const SHOPS_MAX = 8;
const PRICE_MIN = 900;
const PRICE_MAX = 1200;
const PRICE_STEP = 10;
const MARKER_MARGIN_X = 48;
const MARKER_MARGIN_Y = 28;
const MARKER_GAP = 56;

function randInt(min, max) {
  return min + Math.floor(Math.random() * (max - min + 1));
}

function formatPrice(value) {
  return `${String(value).replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0")}\u00a0₽`;
}

function worldPixel(lat, lon, zoom) {
  const size = TILE_SIZE * 2 ** zoom;
  const latRad = (lat * Math.PI) / 180;
  const x = ((lon + 180) / 360) * size;
  const y = ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * size;
  return { x, y };
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

function locate() {
  return new Promise((resolve) => {
    if (!("geolocation" in navigator)) {
      resolve({ ...FALLBACK_CENTER, own: false });
      return;
    }
    let done = false;
    const finish = (value) => {
      if (!done) {
        done = true;
        resolve(value);
      }
    };
    window.setTimeout(() => finish({ ...FALLBACK_CENTER, own: false }), GEO_TIMEOUT_MS + 500);
    navigator.geolocation.getCurrentPosition(
      (pos) => finish({ lat: pos.coords.latitude, lon: pos.coords.longitude, own: true }),
      () => finish({ ...FALLBACK_CENTER, own: false }),
      { timeout: GEO_TIMEOUT_MS, maximumAge: 600000, enableHighAccuracy: false },
    );
  });
}

function buildTiles(center) {
  const pixel = worldPixel(center.lat, center.lon, ZOOM);
  const tilesPerSide = 2 ** ZOOM;
  const originX = Math.floor(pixel.x / TILE_SIZE) - 1;
  const originY = Math.floor(pixel.y / TILE_SIZE) - 1;
  const layer = el("div", "shops-map__tiles");
  layer.style.width = `${GRID * TILE_SIZE}px`;
  layer.style.height = `${GRID * TILE_SIZE}px`;
  const offsetX = pixel.x - originX * TILE_SIZE;
  const offsetY = pixel.y - originY * TILE_SIZE;
  layer.style.transform = `translate(${-offsetX}px, ${-offsetY}px)`;
  for (let row = 0; row < GRID; row += 1) {
    for (let col = 0; col < GRID; col += 1) {
      const y = originY + row;
      if (y < 0 || y >= tilesPerSide) {
        continue;
      }
      const x = (((originX + col) % tilesPerSide) + tilesPerSide) % tilesPerSide;
      const img = el("img", "shops-map__tile");
      img.alt = "";
      img.width = TILE_SIZE;
      img.height = TILE_SIZE;
      img.decoding = "async";
      img.draggable = false;
      img.style.left = `${col * TILE_SIZE}px`;
      img.style.top = `${row * TILE_SIZE}px`;
      img.addEventListener("error", () => img.classList.add("is-failed"), { once: true });
      img.src = `${TILE_HOST}/${ZOOM}/${x}/${y}.png`;
      layer.append(img);
    }
  }
  return layer;
}

function randomShops(width, height) {
  const count = randInt(SHOPS_MIN, SHOPS_MAX);
  const steps = (PRICE_MAX - PRICE_MIN) / PRICE_STEP;
  const cx = width / 2;
  const cy = height / 2;
  const points = [];
  for (let i = 0; i < count; i += 1) {
    let best = null;
    let bestDist = -1;
    for (let attempt = 0; attempt < 40; attempt += 1) {
      const x = randInt(MARKER_MARGIN_X, Math.max(MARKER_MARGIN_X, width - MARKER_MARGIN_X));
      const y = randInt(MARKER_MARGIN_Y, Math.max(MARKER_MARGIN_Y, height - MARKER_MARGIN_Y));
      const others = [...points, { x: cx, y: cy }];
      const dist = Math.min(...others.map((p) => Math.hypot(p.x - x, p.y - y)));
      if (dist > bestDist) {
        best = { x, y };
        bestDist = dist;
      }
      if (dist >= MARKER_GAP) {
        break;
      }
    }
    points.push(best);
  }
  return points.map((point, index) => ({
    ...point,
    name: `Магазин ${index + 1}`,
    price: PRICE_MIN + randInt(0, steps) * PRICE_STEP,
  }));
}

function initShopsMap(root) {
  const openBtn = root.querySelector("[data-shops-open]");
  const dialog = root.querySelector("[data-shops-dialog]");
  const map = root.querySelector("[data-shops-map]");
  const status = root.querySelector("[data-shops-status]");
  const minLine = root.querySelector("[data-shops-min]");
  const list = root.querySelector("[data-shops-list]");
  const refreshBtn = root.querySelector("[data-shops-refresh]");
  if (!openBtn || !dialog || !map || !status || !minLine || !list) {
    return;
  }

  const tilesBox = el("div", "shops-map__tiles-box");
  const markers = el("div", "shops-map__markers");
  const you = el("span", "shops-map__you");
  you.title = "Центр карты";
  map.replaceChildren(tilesBox, markers, you);

  let center = null;

  const renderShops = () => {
    const shops = randomShops(map.clientWidth || 320, map.clientHeight || 320);
    const cheapest = shops.reduce((a, b) => (b.price < a.price ? b : a));
    markers.replaceChildren(
      ...shops.map((shop) => {
        const marker = el("span", shop === cheapest ? "shops-marker is-min" : "shops-marker");
        marker.style.left = `${shop.x}px`;
        marker.style.top = `${shop.y}px`;
        marker.title = shop.name;
        marker.append(
          el("span", "shops-marker__price", formatPrice(shop.price)),
          el("span", "shops-marker__name", shop.name),
        );
        return marker;
      }),
    );
    minLine.textContent = `Дешевле всего: ${formatPrice(cheapest.price)} — ${cheapest.name}`;
    const sorted = [...shops].sort((a, b) => a.price - b.price);
    list.replaceChildren(
      ...sorted.map((shop) => {
        const item = el("li", shop === cheapest ? "shops-list__item is-min" : "shops-list__item");
        item.append(
          el("span", "shops-list__name", shop.name),
          el("span", "shops-list__price", formatPrice(shop.price)),
        );
        return item;
      }),
    );
  };

  const render = async () => {
    if (!center) {
      status.textContent = "Определяем местоположение…";
      center = await locate();
      tilesBox.replaceChildren(buildTiles(center));
    }
    status.textContent = center.own
      ? "Центр карты — ваше местоположение."
      : "Геолокация недоступна — показан центр Москвы.";
    renderShops();
    if (refreshBtn) {
      refreshBtn.hidden = false;
    }
  };

  openBtn.addEventListener("click", () => {
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) {
        dialog.showModal();
      }
    } else {
      dialog.setAttribute("open", "");
    }
    render();
  });
  if (refreshBtn) {
    refreshBtn.addEventListener("click", renderShops);
  }
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) {
      return;
    }
    const rect = dialog.getBoundingClientRect();
    const inside =
      event.clientX >= rect.left &&
      event.clientX <= rect.right &&
      event.clientY >= rect.top &&
      event.clientY <= rect.bottom;
    if (!inside) {
      dialog.close();
    }
  });
  dialog.addEventListener("close", () => openBtn.focus());
}

document.querySelectorAll("[data-shops]").forEach(initShopsMap);
