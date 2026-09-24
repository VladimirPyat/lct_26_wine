"""Factory: load task YAML + prompt, resolve API key from env."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

from llm.client import LLMClient
from llm.engine import LLMEngine, Modality, OutputKind

_LLM_ROOT = Path(__file__).resolve().parent
_DEFAULT_RETRIES = 3


def create_llm_engine(task_name: str) -> LLMEngine:
    """Загрузить ``src/llm/tasks/{task_name}.yaml`` и prompt; ключ API из env.

    Missing/empty ``provider.api_key_env`` value → ``ValueError`` (fail fast).
    """
    task_path = _LLM_ROOT / "tasks" / f"{task_name}.yaml"
    if not task_path.is_file():
        msg = f"LLM task config not found: {task_path}"
        raise FileNotFoundError(msg)

    raw = yaml.safe_load(task_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"LLM task config must be a mapping: {task_path}"
        raise TypeError(msg)

    provider = raw.get("provider")
    if not isinstance(provider, dict):
        msg = f"LLM task {task_name!r}: missing provider block"
        raise ValueError(msg)

    api_key_env = provider.get("api_key_env")
    if not isinstance(api_key_env, str) or not api_key_env.strip():
        msg = f"LLM task {task_name!r}: provider.api_key_env is required"
        raise ValueError(msg)
    api_key = os.environ.get(api_key_env, "")
    if not api_key.strip():
        msg = (
            f"Environment variable {api_key_env!r} is missing or empty "
            f"(required by LLM task {task_name!r})"
        )
        raise ValueError(msg)

    base_url = _require_str(provider, "base_url", task_name)
    model = _require_str(provider, "model", task_name)
    provider_name = _require_str(provider, "name", task_name)

    prompt_rel = raw.get("prompt_path")
    if not isinstance(prompt_rel, str) or not prompt_rel.strip():
        msg = f"LLM task {task_name!r}: prompt_path is required"
        raise ValueError(msg)
    prompt_path = _LLM_ROOT / prompt_rel
    if not prompt_path.is_file():
        msg = f"LLM prompt not found for task {task_name!r}: {prompt_path}"
        raise FileNotFoundError(msg)
    prompt = prompt_path.read_text(encoding="utf-8")

    modality_raw = raw.get("modality")
    if modality_raw not in ("vision", "text"):
        msg = f"LLM task {task_name!r}: modality must be 'vision' or 'text'"
        raise ValueError(msg)
    modality = cast(Modality, modality_raw)

    output = raw.get("output")
    if not isinstance(output, dict):
        msg = f"LLM task {task_name!r}: missing output block"
        raise ValueError(msg)
    output_kind_raw = output.get("kind")
    if output_kind_raw != "text_lines":
        msg = (
            f"LLM task {task_name!r}: unsupported output.kind {output_kind_raw!r} "
            "(2A supports text_lines only)"
        )
        raise ValueError(msg)
    output_kind = cast(OutputKind, output_kind_raw)

    retries = raw.get("retries", _DEFAULT_RETRIES)
    if not isinstance(retries, int) or retries < 1:
        msg = f"LLM task {task_name!r}: retries must be int >= 1, got {retries!r}"
        raise ValueError(msg)

    temperature = raw.get("temperature", 0.0)
    if not isinstance(temperature, (int, float)):
        msg = f"LLM task {task_name!r}: temperature must be a number"
        raise ValueError(msg)

    client = LLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        retries=retries,
        task_name=task_name,
        provider_name=provider_name,
        temperature=float(temperature),
    )
    return LLMEngine(
        client=client,
        prompt=prompt,
        modality=modality,
        output_kind=output_kind,
        task_name=task_name,
    )


def _require_str(block: dict[str, Any], key: str, task_name: str) -> str:
    value = block.get(key)
    if not isinstance(value, str) or not value.strip():
        msg = f"LLM task {task_name!r}: provider.{key} is required"
        raise ValueError(msg)
    return value
