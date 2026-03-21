import pytest
from app.domain.models import Asset

def test_list_assets_pagination(client, db_session):
    # Tạo 25 assets trên RAM cực nhanh
    db_session.add_all([Asset(name=f"a-{i}.com", type="domain") for i in range(25)])
    db_session.commit()

    response = client.get("/assets?page=1&limit=10")
    data = response.json()
    assert len(data["data"]) == 10
    assert data["pagination"]["total"] == 25

def test_get_asset_stats(client, db_session):
    db_session.add_all([
        Asset(name="d1", type="domain", status="active"),
        Asset(name="i1", type="ip", status="inactive")
    ])
    db_session.commit()

    response = client.get("/assets/stats")
    assert response.json()["total"] == 2