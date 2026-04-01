"""
tests/test_api.py
Integration tests cho tất cả HTTP endpoints.
Dùng client + db_session fixtures từ conftest.py.
"""
import uuid
from unittest.mock import patch

import pytest


# ── Helper ────────────────────────────────────────────────────────────────────

def _create_asset(client, name="example.com", type_="domain", status="active"):
    r = client.post("/assets/batch", json={
        "assets": [{"name": name, "type": type_, "status": status}]
    })
    assert r.status_code == 201, r.text
    return r.json()["ids"][0]


# ═══════════════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealth:

    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["database"]["connected"] is True

    def test_health_db_unreachable(self, client):
        from sqlalchemy.exc import OperationalError
        with patch("app.api.health.db_module.engine") as mock_engine:
            mock_engine.pool.status.side_effect = Exception("pool error")
            r = client.get("/health")
        assert r.status_code in (200, 503)


# ═══════════════════════════════════════════════════════════════════════════════
# POST /assets/batch
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchCreate:

    def test_create_single(self, client):
        r = client.post("/assets/batch", json={
            "assets": [{"name": "test.com", "type": "domain", "status": "active"}]
        })
        assert r.status_code == 201
        assert r.json()["created_count"] == 1
        assert len(r.json()["ids"]) == 1

    def test_create_multiple(self, client):
        r = client.post("/assets/batch", json={"assets": [
            {"name": "a.com", "type": "domain",  "status": "active"},
            {"name": "1.1.1.1", "type": "ip",    "status": "active"},
            {"name": "nginx", "type": "service",  "status": "inactive"},
        ]})
        assert r.status_code == 201
        assert r.json()["created_count"] == 3

    def test_create_all_types(self, client):
        for t in ("domain", "ip", "service"):
            r = client.post("/assets/batch", json={
                "assets": [{"name": f"{t}.test", "type": t, "status": "active"}]
            })
            assert r.status_code == 201, f"Failed for {t}: {r.text}"

    def test_invalid_type_422(self, client):
        r = client.post("/assets/batch", json={"assets": [{"name": "x", "type": "INVALID", "status": "active"}]})
        assert r.status_code == 422

    def test_invalid_status_422(self, client):
        r = client.post("/assets/batch", json={"assets": [{"name": "x", "type": "domain", "status": "deleted"}]})
        assert r.status_code == 422

    def test_empty_list_422(self, client):
        assert client.post("/assets/batch", json={"assets": []}).status_code == 422

    def test_missing_name_422(self, client):
        assert client.post("/assets/batch", json={"assets": [{"type": "domain", "status": "active"}]}).status_code == 422

    def test_response_has_valid_uuid(self, client):
        r = client.post("/assets/batch", json={"assets": [{"name": "u.com", "type": "domain", "status": "active"}]})
        uuid.UUID(r.json()["ids"][0])


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /assets/batch
# ═══════════════════════════════════════════════════════════════════════════════

class TestBatchDelete:

    def test_delete_existing(self, client):
        asset_id = _create_asset(client)
        r = client.delete(f"/assets/batch?ids={asset_id}")
        assert r.status_code == 200
        assert r.json()["deleted"] == 1

    def test_delete_nonexistent(self, client):
        ghost = str(uuid.uuid4())
        r = client.delete(f"/assets/batch?ids={ghost}")
        assert r.json()["not_found"] == 1

    def test_delete_invalid_uuid_400(self, client):
        r = client.delete("/assets/batch?ids=not-a-uuid")
        assert r.status_code == 400

    def test_delete_multiple(self, client):
        ids = [_create_asset(client, name=f"del{i}.com") for i in range(3)]
        r = client.delete(f"/assets/batch?ids={','.join(ids)}")
        assert r.json()["deleted"] == 3

    def test_delete_idempotent(self, client):
        asset_id = _create_asset(client)
        client.delete(f"/assets/batch?ids={asset_id}")
        r = client.delete(f"/assets/batch?ids={asset_id}")
        assert r.json()["deleted"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# GET /assets
# ═══════════════════════════════════════════════════════════════════════════════

class TestListAssets:

    def test_empty_returns_empty(self, client):
        r = client.get("/assets")
        assert r.json()["data"] == []
        assert r.json()["pagination"]["total"] == 0

    def test_pagination(self, client):
        for i in range(5):
            _create_asset(client, name=f"p{i}.com")
        r = client.get("/assets?page=1&limit=3")
        assert len(r.json()["data"]) == 3
        assert r.json()["pagination"]["total"] == 5
        assert r.json()["pagination"]["total_pages"] == 2

    def test_filter_by_type(self, client):
        _create_asset(client, name="dom.com", type_="domain")
        _create_asset(client, name="1.2.3.4", type_="ip")
        data = client.get("/assets?type=domain").json()["data"]
        assert all(a["type"] == "domain" for a in data)

    def test_filter_by_status(self, client):
        _create_asset(client, name="a.com", status="active")
        _create_asset(client, name="b.com", status="inactive")
        data = client.get("/assets?status=inactive").json()["data"]
        assert all(a["status"] == "inactive" for a in data)

    def test_invalid_type_422(self, client):
        assert client.get("/assets?type=INVALID").status_code == 422

    def test_newest_first(self, client):
        for i in range(3):
            _create_asset(client, name=f"sort{i}.com")
        names = [a["name"] for a in client.get("/assets").json()["data"]]
        assert names[0] == "sort2.com"


# ═══════════════════════════════════════════════════════════════════════════════
# GET /assets/search
# ═══════════════════════════════════════════════════════════════════════════════

class TestSearch:

    def test_partial_match(self, client):
        _create_asset(client, name="example.com")
        _create_asset(client, name="test.example.org")
        _create_asset(client, name="unrelated.io")
        names = [a["name"] for a in client.get("/assets/search?q=example").json()]
        assert "example.com" in names
        assert "unrelated.io" not in names

    def test_case_insensitive(self, client):
        _create_asset(client, name="CaseSensitive.com")
        assert len(client.get("/assets/search?q=casesensitive").json()) == 1

    def test_no_results(self, client):
        assert client.get("/assets/search?q=zzznomatch").json() == []

    def test_missing_q_422(self, client):
        assert client.get("/assets/search").status_code == 422

    def test_empty_q_422(self, client):
        assert client.get("/assets/search?q=").status_code == 422


# ═══════════════════════════════════════════════════════════════════════════════
# GET /assets/stats + /assets/count
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatsCount:

    def test_stats_empty(self, client):
        body = client.get("/assets/stats").json()
        assert body["total"] == 0
        assert body["by_type"] == {"domain": 0, "ip": 0, "service": 0}

    def test_stats_counts(self, client):
        _create_asset(client, name="a.com", type_="domain")
        _create_asset(client, name="1.1.1.1", type_="ip")
        body = client.get("/assets/stats").json()
        assert body["by_type"]["domain"] == 1
        assert body["by_type"]["ip"] == 1

    def test_count(self, client):
        for i in range(3):
            _create_asset(client, name=f"c{i}.com")
        assert client.get("/assets/count").json()["count"] == 3

    def test_count_filter(self, client):
        _create_asset(client, name="a.com", type_="domain")
        _create_asset(client, name="b.io",  type_="ip")
        assert client.get("/assets/count?type=domain").json()["count"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# Scan Jobs
# ═══════════════════════════════════════════════════════════════════════════════

class TestScanJobs:

    def test_enqueue_returns_202(self, client):
        asset_id = _create_asset(client, name="scan.com")
        with patch("app.api.scan_router._run_async_in_background"):
            r = client.post(f"/assets/{asset_id}/scan")
        assert r.status_code == 202
        assert r.json()["status"] == "pending"
        assert "job_id" in r.json()

    def test_enqueue_nonexistent_404(self, client):
        assert client.post(f"/assets/{uuid.uuid4()}/scan").status_code == 404

    def test_duplicate_409(self, client):
        asset_id = _create_asset(client)
        with patch("app.api.scan_router._run_async_in_background"):
            client.post(f"/assets/{asset_id}/scan")
            r = client.post(f"/assets/{asset_id}/scan")
        assert r.status_code == 409

    def test_get_job(self, client):
        asset_id = _create_asset(client)
        with patch("app.api.scan_router._run_async_in_background"):
            job_id = client.post(f"/assets/{asset_id}/scan").json()["job_id"]
        r = client.get(f"/scan/jobs/{job_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_get_job_schema(self, client):
        asset_id = _create_asset(client)
        with patch("app.api.scan_router._run_async_in_background"):
            job_id = client.post(f"/assets/{asset_id}/scan").json()["job_id"]
        body = client.get(f"/scan/jobs/{job_id}").json()
        for field in ("job_id", "asset_id", "status", "result", "error", "created_at"):
            assert field in body

    def test_get_nonexistent_404(self, client):
        assert client.get(f"/scan/jobs/{uuid.uuid4()}").status_code == 404

    def test_list_jobs(self, client):
        asset_id = _create_asset(client)
        with patch("app.api.scan_router._run_async_in_background"):
            client.post(f"/assets/{asset_id}/scan")
        assert len(client.get("/scan/jobs").json()) >= 1

    def test_delete_job(self, client):
        asset_id = _create_asset(client)
        with patch("app.api.scan_router._run_async_in_background"):
            job_id = client.post(f"/assets/{asset_id}/scan").json()["job_id"]
        assert client.delete(f"/scan/jobs/{job_id}").status_code == 204
        assert client.get(f"/scan/jobs/{job_id}").status_code == 404

    def test_delete_nonexistent_404(self, client):
        assert client.delete(f"/scan/jobs/{uuid.uuid4()}").status_code == 404