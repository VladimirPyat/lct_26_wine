"""Stage 2A — LLMOCREngine adapter + OCR factory engine swap."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from core.ocr.base import IOCREngine, OCRUnavailableError
from core.ocr.factory import create_ocr_engine
from core.ocr.mock import MockOCREngine
from llm.adapters.ocr import LLMOCREngine
from llm.client import LLMClient
from llm.engine import LLMEngine


def _tiny_jpeg(path: Path) -> Path:
    # Minimal JPEG (1x1) — enough for file-exists + data-url path.
    path.write_bytes(
        bytes.fromhex(
            "ffd8ffe000104a46494600010100000100010000ffdb004300"
            "080606070605080707070909080a0c140c0c0b0b0c1912130f"
            "141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c3031"
            "34343f38302c3c39333734ffdb0043010909090c0b0c180d0d"
            "1832211c213232323232323232323232323232323232323232"
            "32323232323232323232323232323232323232323232323232"
            "323232ffc00011080001000103011100021101031101ffc400"
            "14000100000000000000000000000000000008ffc400141001"
            "00000000000000000000000000000000ffda000c0301000210"
            "030000003f00bf80ffd9"
        )
    )
    return path


class _StubLLMEngine:
    """Minimal stand-in for LLMEngine.complete → list[str]."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.calls: list[str | None] = []

    def complete(self, *, image_path: str | None = None) -> list[str]:
        self.calls.append(image_path)
        return list(self._lines)


class _FakePHOCREngine(IOCREngine):
    """Local stand-in so factory phocr path needs no ONNX."""

    def __init__(self, **_kwargs: Any) -> None:
        pass

    def recognize(self, image_path: str) -> list[str]:
        return ["phocr-mock-line"]


def test_llm_ocr_adapter_returns_stripped_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[TEST-ID] 2A-05 OCR adapter recognize → list[str] non-empty stripped lines."""
    image = _tiny_jpeg(tmp_path / "label.jpg")

    raw = "  Brand X  \n\n  2019  \n  \n"
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=raw))]

    client = LLMClient(
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
        retries=3,
        task_name="ocr_label",
        provider_name="qwen",
    )
    create = MagicMock(return_value=response)
    monkeypatch.setattr(client._client.chat.completions, "create", create)

    engine = LLMEngine(
        client=client,
        prompt="extract label text",
        modality="vision",
        output_kind="text_lines",
        task_name="ocr_label",
    )
    adapter = LLMOCREngine(task_name="ocr_label", engine=engine)

    lines = adapter.recognize(str(image))

    assert lines == ["Brand X", "2019"]
    assert create.call_count == 1
    assert isinstance(adapter, IOCREngine)


def test_ocr_factory_swap_phocr_mock_vs_llm_mock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """[TEST-ID] 2A-06 create_ocr_engine phocr|llm|mock all satisfy IOCREngine."""
    image = _tiny_jpeg(tmp_path / "label.jpg")

    monkeypatch.setattr("core.ocr.phocr.PHOCREngine", _FakePHOCREngine)
    stub = _StubLLMEngine(["llm-mock-line"])
    monkeypatch.setattr(
        "llm.adapters.ocr.create_llm_engine",
        lambda task_name: stub,
    )

    phocr_eng = create_ocr_engine(
        "phocr",
        use_cuda=False,
        lang="en",
        limit_side_len=960,
        ort_threads=1,
    )
    llm_eng = create_ocr_engine("llm", llm_task="ocr_label")
    mock_eng = create_ocr_engine("mock")

    assert isinstance(phocr_eng, IOCREngine)
    assert isinstance(llm_eng, IOCREngine)
    assert isinstance(mock_eng, MockOCREngine)
    assert isinstance(mock_eng, IOCREngine)

    assert phocr_eng.recognize(str(image)) == ["phocr-mock-line"]
    assert llm_eng.recognize(str(image)) == ["llm-mock-line"]
    assert mock_eng.recognize(str(image)) == []
    assert stub.calls == [str(image)]


# --- PROD-API-FIX1: per-request LLM failure → OCRUnavailableError ----------


class _RaisingLLMEngine:
    def __init__(self, error: Exception) -> None:
        self._error = error
        self.calls = 0

    def complete(self, *, image_path: str | None = None) -> list[str]:
        self.calls += 1
        raise self._error


def _openai_error() -> Exception:
    import httpx
    from openai import APIConnectionError

    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    return APIConnectionError(request=request)


@pytest.mark.parametrize(
    "make_error",
    [
        _openai_error,
        lambda: RuntimeError("LLM returned empty content"),
    ],
    ids=["openai_error", "runtime_error"],
)
def test_llm_ocr_failure_raises_ocr_unavailable(tmp_path: Path, make_error) -> None:
    """[TEST-ID] FIX1-O1 сбой complete (OpenAIError / RuntimeError) →
    OCRUnavailableError с __cause__.
    """
    image = _tiny_jpeg(tmp_path / "label.jpg")
    error = make_error()
    stub = _RaisingLLMEngine(error)
    adapter = LLMOCREngine(task_name="ocr_label", engine=stub)  # type: ignore[arg-type]
    with pytest.raises(OCRUnavailableError) as info:
        adapter.recognize(str(image))
    assert info.value.__cause__ is error
    assert stub.calls == 1


def test_llm_ocr_missing_image_still_file_not_found(tmp_path: Path) -> None:
    """[TEST-ID] FIX1-O2 отсутствующий кроп → FileNotFoundError (не
    OCRUnavailableError).
    """
    stub = _RaisingLLMEngine(RuntimeError("must not be called"))
    adapter = LLMOCREngine(task_name="ocr_label", engine=stub)  # type: ignore[arg-type]
    with pytest.raises(FileNotFoundError):
        adapter.recognize(str(tmp_path / "missing.jpg"))
    assert stub.calls == 0


def test_llm_ocr_unexpected_error_not_wrapped(tmp_path: Path) -> None:
    """[TEST-ID] FIX1-O3 прочие ошибки (не OpenAI / RuntimeError) не маскируются."""
    image = _tiny_jpeg(tmp_path / "label.jpg")
    adapter = LLMOCREngine(
        task_name="ocr_label", engine=_RaisingLLMEngine(TypeError("bug"))  # type: ignore[arg-type]
    )
    with pytest.raises(TypeError):
        adapter.recognize(str(image))
