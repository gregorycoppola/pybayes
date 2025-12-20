"""
Unit tests using FastAPI TestClient (no separate server needed).
"""

import pytest
from fastapi.testclient import TestClient
from world.server.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestKBUnit:
    def test_create_kb(self, client):
        dsl = """
entity socrates : person
man(theme: socrates)
"""
        r = client.post("/api/kbs", json={"name": "unit_test_kb", "dsl": dsl})
        assert r.status_code == 200
        assert r.json()["entity_count"] == 1


class TestFullPipelineUnit:
    def test_end_to_end(self, client):
        # Create KB
        dsl = """
entity socrates : person
man(theme: socrates)
rule [x:person]: man(theme: x) -> mortal(theme: x)
"""
        r = client.post("/api/kbs", json={"name": "e2e_kb", "dsl": dsl})
        kb_id = r.json()["id"]
        
        # Create doc
        r = client.post("/api/docs", json={"text": "Socrates is a man"})
        doc_id = r.json()["id"]
        
        # Create run
        r = client.post("/api/runs", json={"doc_id": doc_id, "kb_id": kb_id})
        run_id = r.json()["id"]
        
        # Process
        r = client.post(f"/api/runs/{run_id}/process")
        results = r.json()["results"]
        
        # All layers should succeed
        for layer_id, result in results.items():
            assert result["success"], f"{layer_id} failed: {result['message']}"