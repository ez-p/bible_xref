import os
from typing import Any

import requests
from dotenv import load_dotenv

ESV_PASSAGE_URL = "https://api.esv.org/v3/passage/html/"

load_dotenv()


def get_passage(reference: str) -> dict[str, Any]:
    """Fetch a Bible passage from the ESV API.

    Args:
        reference: A passage reference such as "John 3:16".

    Returns:
        The ESV API JSON response, including query metadata and HTML passages.
    """
    token = os.environ.get("ESV_API_TOKEN")
    if not token:
        raise ValueError("ESV_API_TOKEN is not set")

    # curl -H 'Authorization: Token YOUR_API_KEY' 'https://api.esv.org/v3/passage/html/?q=John+11:35'
    response = requests.get(
        ESV_PASSAGE_URL,
        params={"q": reference.strip()},
        headers={"Authorization": f"Token {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_passage_markup(passage: dict[str, Any]) -> str:
    """Extract the HTML markup from an ESV API passage response."""
    return "\n".join(passage.get("passages", []))
