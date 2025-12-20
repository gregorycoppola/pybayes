"""
HTTP client for QBBN API.
"""

import httpx

BASE_URL = "http://localhost:8000/api"


def create_doc(text: str) -> dict:
    r = httpx.post(f"{BASE_URL}/docs", json={"text": text}, timeout=60)
    r.raise_for_status()
    return r.json()


def list_docs() -> list[dict]:
    r = httpx.get(f"{BASE_URL}/docs")
    r.raise_for_status()
    return r.json()["docs"]


def get_doc(doc_id: str) -> dict:
    r = httpx.get(f"{BASE_URL}/docs/{doc_id}")
    r.raise_for_status()
    return r.json()


def run_layer(doc_id: str, layer_id: str, force: bool = False) -> dict:
    r = httpx.post(
        f"{BASE_URL}/docs/{doc_id}/layers/{layer_id}/run",
        json={"force": force},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def run_all_layers(doc_id: str) -> dict:
    r = httpx.post(f"{BASE_URL}/docs/{doc_id}/run", timeout=120)
    r.raise_for_status()
    return r.json()


def get_layer_dsl(doc_id: str, layer_id: str) -> dict:
    r = httpx.get(f"{BASE_URL}/docs/{doc_id}/layers/{layer_id}/dsl")
    r.raise_for_status()
    return r.json()


def set_layer_override(doc_id: str, layer_id: str, dsl: str) -> dict:
    r = httpx.put(
        f"{BASE_URL}/docs/{doc_id}/layers/{layer_id}",
        json={"dsl": dsl},
    )
    r.raise_for_status()
    return r.json()


def clear_layer_override(doc_id: str, layer_id: str) -> dict:
    r = httpx.delete(f"{BASE_URL}/docs/{doc_id}/layers/{layer_id}/override")
    r.raise_for_status()
    return r.json()


def list_layers() -> list[dict]:
    r = httpx.get(f"{BASE_URL}/layers")
    r.raise_for_status()
    return r.json()["layers"]