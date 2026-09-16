"""Thin wrapper around the backend API. The base URL is read from an
environment variable -- never hard-coded, per the assignment's own
explicit "Common Mistakes" warning."""
import os

import requests
from dotenv import load_dotenv

load_dotenv()  # reads frontend/.env -- Streamlit does not do this automatically

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


class ApiError(Exception):
    pass


def ask(question: str) -> dict:
    try:
        resp = requests.post(f"{API_BASE_URL}/query", json={"question": question}, timeout=120)
    except requests.RequestException as e:
        raise ApiError(f"Could not reach the backend at {API_BASE_URL}: {e}") from e

    if resp.status_code != 200:
        raise ApiError(f"Backend returned {resp.status_code}: {resp.text[:300]}")

    return resp.json()


def health() -> dict | None:
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return resp.json() if resp.status_code == 200 else None
    except requests.RequestException:
        return None
