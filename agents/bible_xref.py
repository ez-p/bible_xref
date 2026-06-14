import os
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

Testament = Literal["New Testament", "Old Testament"]
MODEL = "gpt-4o-mini"


def _build_prompt(reference: str, testament: Testament | None) -> str:
    testament_phrase = f" {testament}" if testament else ""
    return (
        f"For the Bible verse {reference} give me three Bible{testament_phrase} "
        "verse cross references. Do not display the bible cross references but "
        "instead return a comma delimited list of three bible verse cross references"
    )


def get_cross_references(reference: str, testament: Testament | None = None) -> str:
    """Return three Bible cross references for the given verse.

    Args:
        reference: A passage reference such as "John 3:16".
        testament: Optional filter for "New Testament" or "Old Testament" cross references.

    Returns:
        A comma-delimited list of three cross-reference verses.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not set")

    reference = reference.strip()
    if not reference:
        raise ValueError("Bible verse reference is required")

    client = OpenAI()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": _build_prompt(reference, testament)}],
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response")

    return content.strip()
