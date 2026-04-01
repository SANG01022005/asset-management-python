"""
tests/test_tags_export.py
Tests cho Tags API và Export API.
"""
import csv
import io
import json
import uuid
import pytest
from app.domain.models import Asset, ScanJob


def _create_asset(client, name="test.com", type_="domain", status="active"):
    r = client.post("/assets/batch", json={"assets": [{"name": name, "type": type_, "status": status}]})
    return r.json()["ids"][0]


def _create_tag(client, name="tag1", color="#aabbcc"):
    return client.post("/tags", json={"name": name, "color": color}).json()["id"]


# ═══════════════════════════════════════════════════════════════════
# Tags CRUD
# ═══════════════════════════════════════════════════════════════════

class TestTagsCRUD:

    def test_create_tag(self, client):
        r = client.post("/tags", json={"name": "production", "color": "#22d3a0"})
        assert r.status_code == 201
        assert r.json()["name"]        == "production"
        assert r.json()["asset_count"] == 0

    def test_create_duplicate_409(self, client):
        client.post("/tags", json={"name": "dup", "color": "#111111"})
        r = client.post("/tags", json={"name": "dup", "color": "#222222"})
        assert r.status_code == 409

    def test_create_invalid_color_422(self, client):
        assert client.post("/tags", json={"name": "bad", "color": "red"}).status_code == 422

    def test_list_tags_sorted(self, client):
        for name in ["zebra", "alpha", "middle"]:
            client.post("/tags", json={"name": name, "color": "#aabbcc"})
        names = [t["name"] for t in client.get("/tags").json()]
        assert names == sorted(names)

    def test_delete_tag(self, client):
        tag_id = _create_tag(client, "to-delete")
        assert client.delete(f"/tags/{tag_id}").status_code == 204
        assert not any(t["id"] == tag_id for t in client.get("/tags").json())

    def test_delete_nonexistent_404(self, client):
        assert client.delete(f"/tags/{uuid.uuid4()}").status_code == 404


class TestAssetTags:

    def test_assign_tags(self, client):
        asset_id = _create_asset(client)
        tag_id   = _create_tag(client)
        r = client.post(f"/assets/{asset_id}/tags", json={"tag_ids": [tag_id]})
        assert r.status_code == 200
        assert "tag1" in r.json()["added"]

    def test_list_asset_tags(self, client):
        asset_id = _create_asset(client)
        tag_id   = _create_tag(client)
        client.post(f"/assets/{asset_id}/tags", json={"tag_ids": [tag_id]})
        tags = client.get(f"/assets/{asset_id}/tags").json()
        assert len(tags) == 1

    def test_list_nonexistent_asset_404(self, client):
        assert client.get(f"/assets/{uuid.uuid4()}/tags").status_code == 404

    def test_remove_tag(self, client):
        asset_id = _create_asset(client)
        tag_id   = _create_tag(client)
        client.post(f"/assets/{asset_id}/tags", json={"tag_ids": [tag_id]})
        assert client.delete(f"/assets/{asset_id}/tags/{tag_id}").status_code == 204
        assert client.get(f"/assets/{asset_id}/tags").json() == []

    def test_assign_nonexistent_tag(self, client):
        asset_id = _create_asset(client)
        ghost_id = str(uuid.uuid4())
        r = client.post(f"/assets/{asset_id}/tags", json={"tag_ids": [ghost_id]})
        assert ghost_id in r.json()["not_found"]

    def test_duplicate_assign_idempotent(self, client):
        asset_id = _create_asset(client)
        tag_id   = _create_tag(client)
        client.post(f"/assets/{asset_id}/tags", json={"tag_ids": [tag_id]})
        client.post(f"/assets/{asset_id}/tags", json={"tag_ids": [tag_id]})
        assert len(client.get(f"/assets/{asset_id}/tags").json()) == 1

    def test_asset_count_updates(self, client):
        asset_id = _create_asset(client)
        tag_id   = _create_tag(client)
        client.post(f"/assets/{asset_id}/tags", json={"tag_ids": [tag_id]})
        assert client.get("/tags").json()[0]["asset_count"] == 1


# ═══════════════════════════════════════════════════════════════════
# Export API
# ═══════════════════════════════════════════════════════════════════

class TestExportAssets:

    def test_returns_csv(self, client):
        _create_asset(client)
        r = client.get("/export/assets")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

    def test_has_header_row(self, client):
        r = client.get("/export/assets")
        first_line = r.text.strip().split("\n")[0]
        assert "id" in first_line and "name" in first_line

    def test_contains_data(self, client):
        _create_asset(client, name="google.com")
        assert "google.com" in client.get("/export/assets").text

    def test_filter_by_type(self, client):
        _create_asset(client, name="dom.com", type_="domain")
        _create_asset(client, name="1.2.3.4", type_="ip")
        r = client.get("/export/assets?type=domain")
        assert "dom.com" in r.text
        assert "1.2.3.4" not in r.text

    def test_empty_db(self, client):
        r = client.get("/export/assets")
        lines = [l for l in r.text.strip().split("\n") if l]
        assert len(lines) == 1  # chỉ header

    def test_filename_has_timestamp(self, client):
        r = client.get("/export/assets")
        assert "assets_" in r.headers["content-disposition"]


class TestExportScanResults:

    def test_returns_csv(self, client):
        r = client.get("/export/scan-results")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

    def test_only_completed(self, client, db_session):
        asset_id = _create_asset(client)
        pending   = ScanJob(id=uuid.uuid4(), asset_id=uuid.UUID(asset_id), status="pending")
        completed = ScanJob(id=uuid.uuid4(), asset_id=uuid.UUID(asset_id), status="completed",
                            result=json.dumps({"asset_type": "domain", "ip_scan": {"status": "ok"}}))
        db_session.add_all([pending, completed])
        db_session.commit()
        r      = client.get("/export/scan-results")
        reader = csv.DictReader(io.StringIO(r.text))
        rows   = list(reader)
        assert len(rows) == 1
        assert rows[0]["status"] == "completed"


class TestExportReport:

    def test_returns_json(self, client):
        body = client.get("/export/report").json()
        for key in ("generated_at", "assets", "scans", "tags", "never_scanned"):
            assert key in body

    def test_empty_db(self, client):
        body = client.get("/export/report").json()
        assert body["assets"]["total"] == 0
        assert body["never_scanned"]   == []

    def test_asset_counts(self, client):
        _create_asset(client, name="a.com",   type_="domain")
        _create_asset(client, name="1.1.1.1", type_="ip")
        body = client.get("/export/report").json()
        assert body["assets"]["total"]             == 2
        assert body["assets"]["by_type"]["domain"] == 1

    def test_never_scanned(self, client):
        _create_asset(client, name="never.com")
        assert "never.com" in client.get("/export/report").json()["never_scanned"]

    def test_tag_summary(self, client):
        _create_tag(client, "mytag")
        body = client.get("/export/report").json()
        assert body["tags"]["total"] == 1
        assert body["tags"]["summary"][0]["name"] == "mytag"