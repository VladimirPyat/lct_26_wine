// Shared UI helpers: js class, toast, image fallback, «Скоро» stubs, catalog filters panel.

document.documentElement.classList.remove("no-js");
document.documentElement.classList.add("js");

let toastTimer = 0;

export function showToast(message) {
  const toast = document.querySelector("[data-toast]");
  if (!toast) {
    return;
  }
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toast.hidden = true;
  }, 2500);
}

function initImageFallback() {
  const placeholder = document.body.dataset.placeholderSrc;
  if (!placeholder) {
    return;
  }
  const swap = (img) => {
    if (img.dataset.fallbackApplied) {
      return;
    }
    img.dataset.fallbackApplied = "1";
    img.src = placeholder;
  };
  document.querySelectorAll("img[data-fallback]").forEach((img) => {
    if (img.complete && img.naturalWidth === 0) {
      swap(img);
    } else {
      img.addEventListener("error", () => swap(img), { once: true });
    }
  });
}

function initSoonButtons() {
  document.querySelectorAll("[data-soon]").forEach((button) => {
    button.addEventListener("click", () => showToast("Скоро"));
  });
}

function initFiltersPanel() {
  const panel = document.querySelector("[data-filters-panel]");
  const openBtn = document.querySelector("[data-filters-open]");
  if (!panel || !openBtn) {
    return;
  }
  const backdrop = document.querySelector("[data-filters-backdrop]");
  const closeBtn = panel.querySelector("[data-filters-close]");

  const setOpen = (open) => {
    panel.classList.toggle("is-open", open);
    openBtn.setAttribute("aria-expanded", String(open));
    if (backdrop) {
      backdrop.hidden = !open;
    }
    if (open) {
      const first = panel.querySelector("select, button, a");
      if (first) {
        first.focus();
      }
    } else {
      openBtn.focus();
    }
  };

  openBtn.addEventListener("click", () => setOpen(true));
  if (closeBtn) {
    closeBtn.addEventListener("click", () => setOpen(false));
  }
  if (backdrop) {
    backdrop.addEventListener("click", () => setOpen(false));
  }
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && panel.classList.contains("is-open")) {
      setOpen(false);
    }
  });
}

initImageFallback();
initSoonButtons();
initFiltersPanel();
