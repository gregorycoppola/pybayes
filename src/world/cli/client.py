"""
HTTP client for QBBN API.
"""

import httpx

BASE_URL = "http://localhost:8000/api"


# === Docs ===

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


def delete_doc(doc_id: str) -> dict:
    r = httpx.delete(f"{BASE_URL}/docs/{doc_id}")
    r.raise_for_status()
    return r.json()


# === Layers (doc-level) ===

def run_layer(doc_id: str, layer_id: str, force: bool = False) -> dict:
    payload = {"force": force}
    r = httpx.post(f"{BASE_URL}/docs/{doc_id}/layers/{layer_id}/run", json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def get_layer_data(doc_id: str, layer_id: str) -> dict:
    r = httpx.get(f"{BASE_URL}/docs/{doc_id}/layers/{layer_id}")
    r.raise_for_status()
    return r.json()


def get_layer_dsl(doc_id: str, layer_id: str) -> dict:
    r = httpx.get(f"{BASE_URL}/docs/{doc_id}/layers/{layer_id}/dsl")
    r.raise_for_status()
    return r.json()


def set_layer_override(doc_id: str, layer_id: str, dsl: str) -> dict:
    r = httpx.put(f"{BASE_URL}/docs/{doc_id}/layers/{layer_id}", json={"dsl": dsl})
    r.raise_for_status()
    return r.json()


def clear_layer_override(doc_id: str, layer_id: str) -> dict:
    r = httpx.delete(f"{BASE_URL}/docs/{doc_id}/layers/{layer_id}/override")
    r.raise_for_status()
    return r.json()


# === KBs ===

def create_kb(name: str, dsl: str) -> dict:
    r = httpx.post(f"{BASE_URL}/kbs", json={"name": name, "dsl": dsl}, timeout=60)
    r.raise_for_status()
    return r.json()


def list_kbs() -> list[dict]:
    r = httpx.get(f"{BASE_URL}/kbs")
    r.raise_for_status()
    return r.json()["kbs"]


def get_kb(kb_id: str) -> dict:
    r = httpx.get(f"{BASE_URL}/kbs/{kb_id}")
    r.raise_for_status()
    return r.json()


def get_kb_dsl(kb_id: str) -> dict:
    r = httpx.get(f"{BASE_URL}/kbs/{kb_id}/dsl")
    r.raise_for_status()
    return r.json()


# === Runs ===

def create_run(doc_id: str, kb_id: str, parent_run_id: str = None) -> dict:
    payload = {"doc_id": doc_id, "kb_id": kb_id}
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