// Camera: getUserMedia preview with a visual-only aim overlay; snap sends the FULL frame.

import { postImage, showUploadError } from "./upload.js";

const JPEG_QUALITY = 0.92;

const root = document.querySelector("[data-camera]");
const note = document.querySelector("[data-camera-note]");

function showNote(message) {
  if (!note) {
    return;
  }
  note.textContent = message;
  note.hidden = !message;
}

function cameraSupported() {
  return Boolean(
    window.isSecureContext && navigator.mediaDevices && navigator.mediaDevices.getUserMedia,
  );
}

async function hasVideoInput() {
  if (!navigator.mediaDevices.enumerateDevices) {
    return true;
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices.some((device) => device.kind === "videoinput");
  } catch (error) {
    console.warn("enumerateDevices failed", error);
    return true;
  }
}

async function initCamera() {
  if (!root) {
    return;
  }
  if (!cameraSupported()) {
    showNote(
      window.isSecureContext
        ? "Камера недоступна в этом браузере. Загрузите фото из галереи."
        : "Камера требует HTTPS. Загрузите фото из галереи — это работает всегда.",
    );
    return;
  }
  if (!(await hasVideoInput())) {
    showNote("Камера не найдена. Загрузите фото или перетащите файл.");
    return;
  }

  const video = root.querySelector("[data-camera-video]");
  const startWrap = root.querySelector("[data-camera-start-wrap]");
  const startBtn = root.querySelector("[data-camera-start]");
  const snapBtn = root.querySelector("[data-camera-snap]");
  root.hidden = false;
  let stream = null;

  const stop = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }
  };

  startBtn.addEventListener("click", async () => {
    startBtn.disabled = true;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      startWrap.hidden = true;
      snapBtn.dataset.ready = "1";
      snapBtn.disabled = false;
      showNote("");
    } catch (error) {
      console.error("getUserMedia failed", error);
      startBtn.disabled = false;
      const denied = error && (error.name === "NotAllowedError" || error.name === "SecurityError");
      showNote(
        denied
          ? "Доступ к камере запрещён. Разрешите камеру в настройках браузера или загрузите фото."
          : "Не удалось включить камеру. Загрузите фото из галереи.",
      );
    }
  });

  snapBtn.addEventListener("click", () => {
    if (!stream || !video.videoWidth) {
      showUploadError("Камера ещё не готова. Подождите секунду и попробуйте снова.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          showUploadError("Не удалось сделать снимок. Попробуйте ещё раз или загрузите фото.");
          return;
        }
        postImage(blob, "camera.jpg");
      },
      "image/jpeg",
      JPEG_QUALITY,
    );
  });

  window.addEventListener("pagehide", stop);
}

initCamera();
