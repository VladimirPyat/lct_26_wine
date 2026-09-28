"""PROD-API-FIX1 C — цепочка выбора OCR-движка (без GPU / LLM / сети)."""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from api import runtime as runtime_mod
from core.config import load_app_settings, load_ocr_rerank_settings
from core.ocr.base import IOCREngine
from core.ocr.factory import create_ocr_engine
from core.ocr.mock import MockOCREngine
from core.ocr.selection import OcrSelection, select_ocr_engine
from core.retrieve.dino_encoder import DinoOnnxEncoder
from llm.adapters.ocr import LLMOCREngine

FAKE_SECRET = "sk-fix1-fake-secret-value-0123456789"
CUDA_EP = "CUDAExecutionProvider"
CPU_EP = "CPUExecutionProvider"


class _FakeEngine(IOCREngine):
    def recognize(self, image_path: str) -> list[str]:
        return ["fake"]


class _Probe:
    """LLM-проба: считает вызовы, возвращает движок или бросает ошибку."""

    def __init__(self, result: IOCREngine | Exception | None = None) -> None:
        self.calls = 0
        self._result = result if result is not None else _FakeEngine()

    def __call__(self) -> IOCREngine:
        self.calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


_MISSING_KEY = ValueError(
    "Environment variable 'QWEN_API_KEY' is missing or empty "
    "(required by LLM task 'ocr_label')"
)


# --- pure selection --------------------------------------------------------


def test_phocr_with_cuda_selects_phocr_without_probe() -> None:
    """[TEST-ID] FIX1-C1 phocr + CUDA → phocr, cuda_available, проба LLM не вызвана."""
    probe = _Probe()
    sel = select_ocr_engine("phocr", cuda_available=True, llm_probe=probe)
    assert sel == OcrSelection("phocr", "cuda_available", None)
    assert probe.calls == 0


def test_phocr_without_cuda_falls_back_to_llm() -> None:
    """[TEST-ID] FIX1-C2 phocr без CUDA + проба OK → llm, no_cuda."""
    engine = _FakeEngine()
    probe = _Probe(engine)
    sel = select_ocr_engine("phocr", cuda_available=False, llm_probe=probe)
    assert sel.effective == "llm"
    assert sel.reason == "no_cuda"
    assert sel.engine is engine
    assert probe.calls == 1


def test_phocr_without_cuda_llm_unavailable_none() -> None:
    """[TEST-ID] FIX1-C3 phocr без CUDA + нет ключа → none, llm_unavailable, engine
    None.
    """
    probe = _Probe(_MISSING_KEY)
    sel = select_ocr_engine("phocr", cuda_available=False, llm_probe=probe)
    assert sel.effective == "none"
    assert sel.reason.startswith("llm_unavailable")
    assert "QWEN_API_KEY" in sel.reason
    assert sel.engine is None
    assert probe.calls == 1


@pytest.mark.parametrize("cuda", [True, False])
def test_llm_configured_probes_regardless_of_cuda(cuda: bool) -> None:
    """[TEST-ID] FIX1-C4 llm → проба вызывается при любом CUDA; ошибка → none."""
    probe = _Probe()
    sel = select_ocr_engine("llm", cuda_available=cuda, llm_probe=probe)
    assert (sel.effective, sel.reason) == ("llm", "configured_llm")
    assert probe.calls == 1

    failing = _Probe(RuntimeError("client init failed"))
    sel = select_ocr_engine("llm", cuda_available=cuda, llm_probe=failing)
    assert sel.effective == "none"
    assert sel.reason.startswith("llm_unavailable")
    assert sel.engine is None
    assert failing.calls == 1


@pytest.mark.parametrize("cuda", [True, False])
def test_mock_configured(cuda: bool) -> None:
    """[TEST-ID] FIX1-C5 mock → mock, проба не вызвана."""
    probe = _Probe()
    sel = select_ocr_engine("mock", cuda_available=cuda, llm_probe=probe)
    assert (sel.effective, sel.reason) == ("mock", "configured_mock")
    assert isinstance(sel.engine, MockOCREngine)
    assert probe.calls == 0


def test_unknown_engine_raises() -> None:
    """[TEST-ID] FIX1-C5b неизвестный engine → ValueError (без тихого выбора)."""
    with pytest.raises(ValueError, match="Unknown ocr.engine"):
        select_ocr_engine("tesseract", cuda_available=True, llm_probe=_Probe())


def test_real_probe_missing_key_reason_names_variable_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[TEST-ID] FIX1-C3b реальная LLM-фабрика без ключа → none, причина называет только
    имя.
    """
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    sel = select_ocr_engine(
        "phocr",
        cuda_available=False,
        llm_probe=lambda: create_ocr_engine("llm", llm_task="ocr_label"),
    )
    assert sel.effective == "none"
    assert sel.reason.startswith("llm_unavailable: ValueError:")
    assert "QWEN_API_KEY" in sel.reason


def test_secret_never_in_reason_or_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """[TEST-ID] FIX1-C3c значение ключа не попадает в reason / лог ни при успехе, ни
    при ошибке.
    """
    monkeypatch.setenv("QWEN_API_KEY", FAKE_SECRET)
    caplog.set_level(logging.DEBUG)

    ok = select_ocr_engine(
        "phocr",
        cuda_available=False,
        llm_probe=lambda: create_ocr_engine("llm", llm_task="ocr_label"),
    )
    assert ok.effective == "llm"
    assert isinstance(ok.engine, LLMOCREngine)
    assert FAKE_SECRET not in ok.reason

    # Key is present, but a later init step fails (task YAML missing).
    bad = select_ocr_engine(
        "llm",
        cuda_available=True,
        llm_probe=lambda: create_ocr_engine("llm", llm_task="no_such_task_fix1"),
    )
    assert bad.effective == "none"
    assert bad.reason.startswith("llm_unavailable")
    assert FAKE_SECRET not in bad.reason
    assert all(FAKE_SECRET not in r.getMessage() for r in caplog.records)
    assert FAKE_SECRET not in caplog.text


# --- CUDA detection --------------------------------------------------------


def _app_settings(device: str):  # noqa: ANN202
    base = load_app_settings()
    return base.model_copy(
        update={"compute": base.compute.model_copy(update={"device": device})}
    )


def _encoder(providers: list[str]) -> SimpleNamespace:
    return SimpleNamespace(active_providers=list(providers))


def test_cuda_available_device_cpu_false() -> None:
    """[TEST-ID] FIX1-C6 compute.device=cpu → False даже при CUDA-сессии."""
    assert (
        runtime_mod.cuda_available(_app_settings("cpu"), _encoder([CUDA_EP, CPU_EP]))
        is False
    )


def test_cuda_available_session_cpu_only_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """[TEST-ID] FIX1-C6b cuda + сессия только на CPU EP → False (ort провайдеры не
    сигнал).
    """
    import onnxruntime as ort

    monkeypatch.setattr(ort, "get_available_providers", lambda: [CUDA_EP, CPU_EP])
    assert (
        runtime_mod.cuda_available(_app_settings("cuda"), _encoder([CPU_EP])) is False
    )
    assert (
        runtime_mod.cuda_available(_app_settings("CUDA"), _encoder([CPU_EP])) is False
    )


def test_cuda_available_session_on_cuda_true() -> None:
    """[TEST-ID] FIX1-C6c cuda + сессия с CUDAExecutionProvider → True."""
    assert (
        runtime_mod.cuda_available(_app_settings("cuda"), _encoder([CUDA_EP, CPU_EP]))
        is True
    )


def test_encoder_active_providers_uses_existing_session() -> None:
    """[TEST-ID] FIX1-C6d active_providers энкодера читает уже созданную сессию."""
    calls: list[str] = []

    class _Session:
        def get_providers(self) -> list[str]:
            calls.append("get_providers")
            return [CUDA_EP, CPU_EP]

    encoder = DinoOnnxEncoder.__new__(DinoOnnxEncoder)
    encoder._session = _Session()  # type: ignore[attr-defined]
    providers = encoder.active_providers
    assert providers == [CUDA_EP, CPU_EP]
    assert calls == ["get_providers"]
    providers.append("X")  # returns a copy
    assert encoder.active_providers == [CUDA_EP, CPU_EP]


# --- runtime wiring (build_eval_runtime with fakes) ------------------------


class _Factory:
    """Подмена create_ocr_engine в api.runtime: пишет аргументы вызовов."""

    def __init__(self, llm_result: IOCREngine | Exception | None = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._llm = llm_result if llm_result is not None else _FakeEngine()

    def __call__(self, engine: str, **kwargs: Any) -> IOCREngine:
        self.calls.append((engine, kwargs))
        if engine == "llm":
            if isinstance(self._llm, Exception):
                raise self._llm
            return self._llm
        return _FakeEngine()


def _build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    device: str,
    providers: list[str],
    engine: str = "phocr",
    factory: _Factory | None = None,
) -> tuple[runtime_mod.EvalRuntime, _Factory]:
    app = _app_settings(device)
    rerank = load_ocr_rerank_settings()
    rerank = rerank.model_copy(
        update={"ocr": rerank.ocr.model_copy(update={"engine": engine})}
    )
    fac = factory if factory is not None else _Factory()
    monkeypatch.setattr(runtime_mod, "load_app_settings", lambda: app)
    monkeypatch.setattr(runtime_mod, "load_ocr_rerank_settings", lambda: rerank)
    monkeypatch.setattr(runtime_mod, "create_label_cropper", lambda _s: object())
    monkeypatch.setattr(
        runtime_mod, "create_dino_encoder", lambda _d, _c: _encoder(providers)
    )
    monkeypatch.setattr(runtime_mod, "create_db_engine", lambda: object())
    monkeypatch.setattr(runtime_mod, "create_session_factory", lambda _e: object())
    monkeypatch.setattr(runtime_mod, "create_ocr_engine", fac)
    return runtime_mod.build_eval_runtime(tmp_path), fac


def test_runtime_gpu_path_phocr_lazy_same_args(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """[TEST-ID] FIX1-C7 phocr + CUDA: create_ocr_engine("phocr", use_cuda=True, …) один
    раз, лениво.
    """
    rt, fac = _build(monkeypatch, tmp_path, device="cuda", providers=[CUDA_EP, CPU_EP])
    assert (rt.ocr_effective, rt.ocr_reason) == ("phocr", "cuda_available")
    assert fac.calls == []  # lazy: nothing built at startup

    first = rt.get_ocr()
    second = rt.get_ocr()
    assert first is not None and first is second
    ocr = rt.ocr_rerank.ocr
    assert fac.calls == [
        (
            "phocr",
            {
                "llm_task": ocr.llm_task,
                "use_cuda": True,
                "lang": ocr.lang,
                "limit_side_len": ocr.limit_side_len,
                "ort_threads": rt.app_settings.compute.ort_threads,
            },
        )
    ]


def test_runtime_no_cuda_uses_llm_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """[TEST-ID] FIX1-C7b phocr без CUDA → llm-движок из пробы, PHOCR не строится."""
    engine = _FakeEngine()
    rt, fac = _build(
        monkeypatch,
        tmp_path,
        device="cuda",
        providers=[CPU_EP],
        factory=_Factory(engine),
    )
    assert (rt.ocr_effective, rt.ocr_reason) == ("llm", "no_cuda")
    assert rt.get_ocr() is engine
    assert [name for name, _ in fac.calls] == ["llm"]
    assert fac.calls[0][1] == {"llm_task": rt.ocr_rerank.ocr.llm_task}


def test_runtime_none_get_ocr_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """[TEST-ID] FIX1-C7c phocr, device=cpu, LLM недоступен → none; get_ocr() → None."""
    rt, fac = _build(
        monkeypatch,
        tmp_path,
        device="cpu",
        providers=[CPU_EP],
        factory=_Factory(_MISSING_KEY),
    )
    assert rt.ocr_effective == "none"
    assert rt.ocr_reason.startswith("llm_unavailable")
    assert rt.get_ocr() is None
    assert rt.get_ocr() is None
    assert [name for name, _ in fac.calls] == ["llm"]  # no PHOCR, no retry


def test_runtime_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """[TEST-ID] FIX1-C7d mock → MockOCREngine, фабрика не вызывается."""
    rt, fac = _build(
        monkeypatch, tmp_path, device="cuda", providers=[CUDA_EP], engine="mock"
    )
    assert rt.ocr_effective == "mock"
    assert isinstance(rt.get_ocr(), MockOCREngine)
    assert fac.calls == []


@pytest.mark.parametrize(
    ("device", "providers", "factory_result", "effective", "reason_prefix"),
    [
        ("cuda", [CUDA_EP, CPU_EP], None, "phocr", "cuda_available"),
        ("cuda", [CPU_EP], None, "llm", "no_cuda"),
        ("cpu", [CPU_EP], _MISSING_KEY, "none", "llm_unavailable"),
    ],
)
def test_runtime_startup_log_line(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    device: str,
    providers: list[str],
    factory_result: Exception | None,
    effective: str,
    reason_prefix: str,
) -> None:
    """[TEST-ID] FIX1-C8 одна INFO-строка «OCR engine: configured=… effective=…
    reason=…».
    """
    monkeypatch.setenv("QWEN_API_KEY", FAKE_SECRET)
    with caplog.at_level(logging.INFO, logger="api.runtime"):
        rt, _ = _build(
            monkeypatch,
            tmp_path,
            device=device,
            providers=providers,
            factory=_Factory(factory_result),
        )
    lines = [
        r
        for r in caplog.records
        if r.name == "api.runtime" and r.getMessage().startswith("OCR engine:")
    ]
    assert len(lines) == 1
    record = lines[0]
    assert record.levelno == logging.INFO
    msg = record.getMessage()
    assert msg.startswith(f"OCR engine: configured=phocr effective={effective} reason=")
    assert msg.split("reason=", 1)[1].startswith(reason_prefix)
    assert rt.ocr_effective == effective
    assert FAKE_SECRET not in caplog.text
