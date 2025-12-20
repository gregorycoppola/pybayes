"""
Integration tests for QBBN API.
Requires server running: uv run uvicorn world.server.main:app --port 8000
"""

import pytest
import httpx

BASE_URL = "http://localhost:8000/api"


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=120)


class TestKB:
    def test_create_and_get_kb(self, client):
        dsl = """
entity socrates : person
entity plato : person
man(theme: socrates)
rule [x:person]: man(theme: x) -> mortal(theme: x)
"""
        # Create
        r = client.post("/kbs", json={"name": "test_kb", "dsl": dsl})
        assert r.status_code == 200
        data = r.json()
        kb_id = data["id"]
        assert data["entity_count"] == 2
        assert data["fact_count"] == 1
        assert data["rule_count"] == 1
        
        # Get
        r = client.get(f"/kbs/{kb_id}")
        assert r.status_code == 200
        kb = r.json()
        assert kb["name"] == "test_kb"
        assert "socrates" in kb["entities"]
        
        # Get DSL
        r = client.get(f"/kbs/{kb_id}/dsl")
        assert r.status_code == 200
        assert "entity socrates" in r.json()["dsl"]
        
        # List
        r = client.get("/kbs")
        assert r.status_code == 200
        assert any(k["id"] == kb_id for k in r.json()["kbs"])
    
    def test_kb_not_found(self, client):
        r = client.get("/kbs/nonexistent123")
        assert r.status_code == 404


class TestDocs:
    def test_create_and_get_doc(self, client):
        # Create
        r = client.post("/docs", json={"text": "Socrates is wise"})
        assert r.status_code == 200
        doc_id = r.json()["id"]
        
        # Get
        r = client.get(f"/docs/{doc_id}")
        assert r.status_code == 200
        doc = r.json()
        assert doc["text"] == "Socrates is wise"
        
        # List
        r = client.get("/docs")
        assert r.status_code == 200
        assert any(d["id"] == doc_id for d in r.json()["docs"])
    
    def test_doc_not_found(self, client):
        r = client.get("/docs/nonexistent123")
        assert r.status_code == 404


class TestRuns:
    @pytest.fixture
    def kb_id(self, client):
        dsl = """
entity socrates : person
man(theme: socrates)
rule [x:person]: man(theme: x) -> mortal(theme: x)
"""
        r = client.post("/kbs", json={"name": "run_test_kb", "dsl": dsl})
        return r.json()["id"]
    
    @pytest.fixture
    def doc_id(self, client):
        r = client.post("/docs", json={"text": "Socrates is a man"})
        return r.json()["id"]
    
    def test_create_run(self, client, doc_id, kb_id):
        r = client.post("/runs", json={"doc_id": doc_id, "kb_id": kb_id})
        assert r.status_code == 200
        run = r.json()
        assert run["doc_id"] == doc_id
        assert run["kb_id"] == kb_id
    
    def test_process_run(self, client, doc_id, kb_id):
        # Create run
        r = client.post("/runs", json={"doc_id": doc_id, "kb_id": kb_id})
        run_id = r.json()["id"]
        
        # Process
        r = client.post(f"/runs/{run_id}/process")
        assert r.status_code == 200
        results = r.json()["results"]
        
        # Check all layers succeeded
        assert results["base"]["success"]
        assert results["clauses"]["success"]
        assert results["args"]["success"]
        assert results["coref"]["success"]
        assert results["entities"]["success"]
        assert results["link"]["success"]
        assert results["logic"]["success"]
        assert results["ground"]["success"]
    
    def test_get_run_layer_dsl(self, client, doc_id, kb_id):
        # Create and process
        r = client.post("/runs", json={"doc_id": doc_id, "kb_id": kb_id})
        run_id = r.json()["id"]
        client.post(f"/runs/{run_id}/process")
        
        # Get base layer DSL
        r = client.get(f"/runs/{run_id}/layers/base/dsl")
        assert r.status_code == 200
        dsl = r.json()["dsl"]
        assert "Socrates" in dsl
        assert "sentence 0" in dsl
    
    def test_run_not_found(self, client):
        r = client.get("/runs/nonexistent123")
        assert r.status_code == 404
    
    def test_run_with_invalid_doc(self, client, kb_id):
        r = client.post("/runs", json={"doc_id": "nonexistent", "kb_id": kb_id})
        assert r.status_code == 404
    
    def test_run_with_invalid_kb(self, client, doc_id):
        r = client.post("/runs", json={"doc_id": doc_id, "kb_id": "nonexistent"})
        assert r.status_code == 404


class TestPipeline:
    """End-to-end pipeline tests with different inputs."""
    
    @pytest.fixture
    def kb_id(self, client):
        dsl = """
entity socrates : person
entity plato : person
man(theme: socrates)
man(theme: plato)
philosopher(theme: socrates)
rule [x:person]: man(theme: x) -> mortal(theme: x)
rule [x:person]: philosopher(theme: x) -> wise(theme: x)
"""
        r = client.post("/kbs", json={"name": "pipeline_test_kb", "dsl": dsl})
        return r.json()["id"]
    
    def test_simple_assertion(self, client, kb_id):
        """Test: Socrates is a man"""
        r = client.post("/docs", json={"text": "Socrates is a man"})
        doc_id = r.json()["id"]
        
        r = client.post("/runs", json={"doc_id": doc_id, "kb_id": kb_id})
        run_id = r.json()["id"]
        
        r = client.post(f"/runs/{run_id}/process")
        results = r.json()["results"]
        
        assert results["link"]["success"]
        assert "1 linked" in results["link"]["message"]
        
        assert results["ground"]["success"]
    
    def test_unknown_entity(self, client, kb_id):
        """Test: Aristotle is wise (not in KB)"""
        r = client.post("/docs", json={"text": "Aristotle is wise"})
        doc_id = r.json()["id"]
        
        r = client.post("/runs", json={"doc_id": doc_id, "kb_id": kb_id})
        run_id = r.json()["id"]
        
        r = client.post(f"/runs/{run_id}/process")
        results = r.json()["results"]
        
        # Should have 0 linked, 1 new
        assert results["link"]["success"]
        assert "0 linked" in results["link"]["message"] or "1 new" in results["link"]["message"]
    
    def test_multi_sentence(self, client, kb_id):
        """Test: Socrates is a man. Plato is a philosopher."""
        r = client.post("/docs", json={"text": "Socrates is a man. Plato is a philosopher."})
        doc_id = r.json()["id"]
        
        r = client.post("/runs", json={"doc_id": doc_id, "kb_id": kb_id})
        run_id = r.json()["id"]
        
        r = client.post(f"/runs/{run_id}/process")
        results = r.json()["results"]
        
        # Check base has 2 sentences
        r = client.get(f"/runs/{run_id}/layers/base/dsl")
        dsl = r.json()["dsl"]
        assert "sentence 0" in dsl
        assert "sentence 1" in dsl
    
    def test_conditional_rule(self, client, kb_id):
        """Test: If someone is a man then they are mortal"""
        r = client.post("/docs", json={"text": "If someone is a man then they are mortal"})
        doc_id = r.json()["id"]
        
        r = client.post("/runs", json={"doc_id": doc_id, "kb_id": kb_id})
        run_id = r.json()["id"]
        
        r = client.post(f"/runs/{run_id}/process")
        results = r.json()["results"]
        
        # Should have clauses with antecedent/consequent
        r = client.get(f"/runs/{run_id}/layers/clauses/dsl")
        dsl = r.json()["dsl"]
        assert "antecedent" in dsl or "consequent" in dsl
        
        # Should have coreference
        r = client.get(f"/runs/{run_id}/layers/coref/dsl")
        dsl = r.json()["dsl"]
        # "someone" and "they" should be linked


class TestLayers:
    def test_list_layers(self, client):
        r = client.get("/layers")
        assert r.status_code == 200
        layers = r.json()["layers"]
        
        layer_ids = [l["id"] for l in layers]
        assert "base" in layer_ids
        assert "clauses" in layer_ids
        assert "args" in layer_ids
        assert "coref" in layer_ids
        assert "entities" in layer_ids
        assert "link" in layer_ids
        assert "logic" in layer_ids
        assert "ground" in layer_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])