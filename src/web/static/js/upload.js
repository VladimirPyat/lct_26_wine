// Upload enhancement: auto-submit on file choice, drag&drop, inline errors. Server validates again.

const form = document.querySelector("[data-upload]");

function el(selector) {
  return form ? form.querySelector(selector) : null;
}

export function showUploadError(message) {
  const box = el("[data-upload-error]");
  if (!box) {
    return;
  }
  box.textContent = message;
  box.hidden = !message;
}

function setBusy(busy) {
  const status = el("[data-upload-status]");
  const input = el("[data-upload-input]");
  if (status) {
    status.hidden = !busy;
  }
  if (input) {
    input.disabled = busy;
  }
  document.querySelectorAll("[data-camera-snap]").forEach((button) => {
    button.disabled = busy || button.dataset.ready !== "1";
  });
}

function validateFile(file) {
  if (!form) {
    return "";
  }
  const maxBytes = Number(form.dataset.maxBytes || 0);
  const types = (form.dataset.types || "").split(",").filter(Boolean);
  if (file.size === 0) {
    return "Файл пустой. Выберите фото бутылки.";
  }
  if (maxBytes && file.size > maxBytes) {
    return `Файл слишком большой. Максимальный размер — ${form.dataset.maxMb} МБ.`;
  }
  if (file.type && types.length && !types.includes(file.type)) {
    return "Неподдерживаемый формат. Выберите фото в формате JPEG, PNG или WebP.";
  }
  return "";
}

async function extractServerError(response) {
  const fallback = `Не удалось распознать фото (ошибка ${response.status}). Попробуйте ещё раз.`;
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("text/html")) {
    return fallback;
  }
  const html = await response.text();
  const doc = new DOMParser().parseFromString(html, "text/html");
  const box = doc.querySelector("[data-upload-error]");
  const text = box ? box.textContent.trim() : "";
  return text || fallback;
}

export async function postImage(file, filename) {
  const problem = validateFile(file);
  if (problem) {
    showUploadError(problem);
    return;
  }
  const action = form ? form.action : "/search";
  const body = new FormData();
  body.append("image", file, filename);
  showUploadError("");
  setBusy(true);
  let response;
  try {
    response = await fetch(action, { method: "POST", body, credentials: "same-origin" });
  } catch (error) {
    setBusy(false);
    showUploadError("Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.");
    console.error("upload failed", error);
    return;
  }
  if (response.ok && new URL(response.url).pathname.startsWith("/result/")) {
    window.location.assign(response.url);
    return;
  }
  let message;
  try {
    message = await extractServerError(response);
  } catch (error) {
    console.error("cannot read error response", error);
    message = `Не удалось распознать фото (ошибка ${response.status}). Попробуйте ещё раз.`;
  }
  setBusy(false);
  showUploadError(message);
}

function initUpload() {
  if (!form || !window.fetch || !window.FormData) {
    return;
  }
  const input = el("[data-upload-input]");
  const zone = el("[data-dropzone]");
  if (!input) {
    return;
  }
  // The file input stays `required` for the no-JS path; JS submits via fetch instead.
  input.addEventListener("change", () => {
    const file = input.files && input.files[0];
    if (file) {
      postImage(file, file.name);
    }
  });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const file = input.files && input.files[0];
    if (file) {
      postImage(file, file.name);
    } else {
      showUploadError("Выберите фото бутылки.");
    }
  });
  if (!zone) {
    return;
  }
  ["dragenter", "dragover"].forEach((type) => {
    zone.addEventListener(type, (event) => {
      event.preventDefault();
      zone.classList.add("dropzone--over");
    });
  });
  ["dragleave", "dragend"].forEach((type) => {
    zone.addEventListener(type, () => zone.classList.remove("dropzone--over"));
  });
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("dropzone--over");
    const file = event.dataTransfer && event.dataTransfer.files[0];
    if (file) {
      postImage(file, file.name);
    }
  });
}

initUpload();
