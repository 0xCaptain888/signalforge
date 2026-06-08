"""DeepSeek client wrapper (OpenAI-compatible API).

Logs every prompt + response to `outputs/llm_logs/` so the report-writing
pipeline is fully auditable: any number that lands in the final markdown
can be traced back to the exact prompt that produced it. This is the
mechanism the hallucination-detector in `report_writer.verify_numbers`
relies on.

Two model entry points:
- `chat`     → `deepseek-chat`     (general writing, default)
- `reason`   → `deepseek-reasoner` (multi-step explanations, lower temp)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from openai import OpenAI

from config.settings import settings


# Lazy client — constructed on first chat/reason call so importing this
# module never requires a DEEPSEEK_API_KEY (lets unit tests import the
# downstream report_writer / synth without credentials).
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.deepseek_api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is empty — set it in .env before "
                "calling chat()/reason()."
            )
        _client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
    return _client


_LOG = Path(settings.outputs_dir) / "llm_logs"
_LOG.mkdir(parents=True, exist_ok=True)


def _log(payload: dict, tag: str) -> None:
    """Persist a single call's full prompt + response to a timestamped JSON."""
    (_LOG / f"{tag}_{int(time.time() * 1000)}.json").write_text(
        json.dumps(payload, indent=2)
    )


def chat(
    system: str,
    user: str,
    model: str = "deepseek-chat",
    temperature: float = 0.5,
    tag: str = "chat",
) -> str:
    """Send a single chat-completion turn; return the assistant text.

    The temperature default of 0.5 is a reasonable middle ground for
    factor narratives — high enough for some variation in phrasing,
    low enough that paraphrasing of the supplied numbers stays faithful.
    """
    resp = _get_client().chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = resp.choices[0].message.content or ""

    _log(
        {
            "model": model,
            "temperature": temperature,
            "system": system,
            "user": user,
            "response": text,
            "usage": (
                resp.usage.model_dump() if getattr(resp, "usage", None) else {}
            ),
        },
        tag=tag,
    )
    return text


def reason(
    system: str,
    user: str,
    temperature: float = 0.3,
    tag: str = "reason",
) -> str:
    """Use the reasoner model for tasks that require step-by-step grounding.

    Lower default temperature reflects the reasoner's intended use: stable,
    chain-of-thought-style explanations rather than creative copy.
    """
    return chat(
        system, user,
        model="deepseek-reasoner",
        temperature=temperature,
        tag=tag,
    )
