// Lightbox for [data-lightbox] links: wheel / buttons / pinch zoom, drag to pan. Links work without JS.

const MIN_SCALE = 1;
const MAX_SCALE = 5;
const STEP = 0.5;

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function button(label, text) {
  const el = document.createElement("button");
  el.type = "button";
  el.className = "lightbox__btn";
  el.setAttribute("aria-label", label);
  el.textContent = text;
  return el;
}

function openLightbox(src, alt, opener) {
  const overlay = document.createElement("div");
  overlay.className = "lightbox";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-label", alt || "Просмотр изображения");

  const stage = document.createElement("div");
  stage.className = "lightbox__stage";
  const img = document.createElement("img");
  img.className = "lightbox__img";
  img.alt = alt || "";
  img.src = src;
  stage.append(img);

  const controls = document.createElement("div");
  controls.className = "lightbox__controls";
  const zoomOut = button("Уменьшить", "−");
  const zoomIn = button("Увеличить", "+");
  const close = button("Закрыть", "×");
  controls.append(zoomOut, zoomIn, close);
  overlay.append(stage, controls);

  let scale = 1;
  let x = 0;
  let y = 0;
  const pointers = new Map();
  let pinchStart = 0;
  let pinchScale = 1;

  const apply = () => {
    if (scale === 1) {
      x = 0;
      y = 0;
    }
    img.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
    img.style.cursor = scale > 1 ? "grab" : "zoom-in";
  };
  const zoomTo = (value) => {
    scale = clamp(value, MIN_SCALE, MAX_SCALE);
    apply();
  };

  const onKey = (event) => {
    if (event.key === "Escape") {
      doClose();
    } else if (event.key === "+" || event.key === "=") {
      zoomTo(scale + STEP);
    } else if (event.key === "-") {
      zoomTo(scale - STEP);
    }
  };
  const doClose = () => {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
    document.body.style.overflow = "";
    if (opener) {
      opener.focus();
    }
  };

  zoomIn.addEventListener("click", () => zoomTo(scale + STEP));
  zoomOut.addEventListener("click", () => zoomTo(scale - STEP));
  close.addEventListener("click", doClose);
  stage.addEventListener("click", (event) => {
    if (event.target === stage) {
      doClose();
    }
  });
  img.addEventListener("dblclick", () => zoomTo(scale > 1 ? 1 : 2));
  img.addEventListener("error", () => {
    const message = document.createElement("p");
    message.className = "lightbox__error";
    message.textContent = "Не удалось загрузить изображение.";
    img.replaceWith(message);
  });
  stage.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      zoomTo(scale + (event.deltaY < 0 ? STEP : -STEP));
    },
    { passive: false },
  );

  img.addEventListener("pointerdown", (event) => {
    img.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinchStart = Math.hypot(a.x - b.x, a.y - b.y);
      pinchScale = scale;
    }
  });
  img.addEventListener("pointermove", (event) => {
    const prev = pointers.get(event.pointerId);
    if (!prev) {
      return;
    }
    const current = { x: event.clientX, y: event.clientY };
    pointers.set(event.pointerId, current);
    if (pointers.size === 2 && pinchStart > 0) {
      const [a, b] = [...pointers.values()];
      zoomTo(pinchScale * (Math.hypot(a.x - b.x, a.y - b.y) / pinchStart));
    } else if (pointers.size === 1 && scale > 1) {
      x += current.x - prev.x;
      y += current.y - prev.y;
      apply();
    }
  });
  const release = (event) => {
    pointers.delete(event.pointerId);
    if (pointers.size < 2) {
      pinchStart = 0;
    }
  };
  img.addEventListener("pointerup", release);
  img.addEventListener("pointercancel", release);

  document.addEventListener("keydown", onKey);
  document.body.append(overlay);
  document.body.style.overflow = "hidden";
  close.focus();
}

document.querySelectorAll("a[data-lightbox]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    openLightbox(link.href, link.dataset.lightboxAlt || "", link);
  });
});
