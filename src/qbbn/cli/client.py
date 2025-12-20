"""
HTTP client for QBBN API.
"""

import httpx

BASE_URL = "http://localhost:8000/api"


# === Docs ===

def create_doc(text: str) -> dict:
    r = httpx.post(f"{BASE_URL}/docs", json={"text": text, "run_base": False}, timeout=60)
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


# === Runs ===

def create_run(doc_id: str, kb_path: str = "kb", parent_run_id: str = None) -> dict:
    payload = {"doc_id": doc_id, "kb_path": kb_path}
    if parent_run_id:
        payload["parent_run_id"] = parent_run_id
    r = httpx.post(f"{BASE_URL}/runs", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def get_run(run_id: str) -> dict:
    r = httpx.get(f"{BASE_URL}/runs/{run_id}")
    r.raise_for_status()
    return r.json()


def list_runs(doc_id: str) -> list[dict]:
    r = httpx.get(f"{BASE_URL}/docs/{doc_id}/runs")
    r.raise_for_status()
    return r.json()["runs"]


def process_run(run_id: str, layers: list[str] = None) -> dict:
    payload = {}
    if layers:
        payload["layers"] = layers
    r = httpx.post(f"{BASE_URL}/runs/{run_id}/process", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def get_run_layer_dsl(run_id: str, layer_id: str) -> dict:
    r = httpx.get(f"{BASE_URL}/runs/{run_id}/layers/{layer_id}/dsl")
    r.raise_for_status()
    return r.json()


def list_layers() -> list[dict]:
    r = httpx.get(f"{BASE_URL}/layers")
    r.raise_for_status()
    return r.json()["layers"]