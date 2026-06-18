import os
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI

from agents.bible_scholar import OLLAMA_BASE_URL, OLLAMA_MODELS

load_dotenv()

Testament = Literal["New Testament", "Old Testament"]
DEFAULT_CROSS_REF_MODEL = "gpt-4o-mini"


def _build_prompt(reference: str, testament: Testament | None) -> str:
    testament_phrase = f" {testament}" if testament else ""
    return (
        f"For the Bible verse {reference} give me three Bible{testament_phrase} "
        "verse cross references. Do not display the bible cross references but "
        "instead return a comma delimited list of three bible verse cross references"
    )


def _create_client(model: str | None) -> tuple[OpenAI, str]:
    if model in OLLAMA_MODELS:
        return OpenAI(api_key="ollama", base_url=OLLAMA_BASE_URL), OLLAMA_MODELS[model]

    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not set")
    return OpenAI(), DEFAULT_CROSS_REF_MODEL


def get_cross_references(
    reference: str,
    testament: Testament | None = None,
    model: str | None = None,
) -> str:
    """Return three Bible cross references for the given verse.

    Args:
        reference: A passage reference such as "John 3:16".
        testament: Optional filter for "New Testament" or "Old Testament" cross references.
        model: Optional UI model selection. Ollama models use local Ollama; others use gpt-4o-mini.

    Returns:
        A comma-delimited list of three cross-reference verses.
    """
    reference = reference.strip()
    if not reference:
        raise ValueError("Bible verse reference is required")

    client, model_name = _create_client(model)
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": _build_prompt(reference, testament)}],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response")

    return content.strip()
