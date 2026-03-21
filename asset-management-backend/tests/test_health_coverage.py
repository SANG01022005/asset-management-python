# asset-management-backend/tests/test_health_coverage.py
"""
Tests for health endpoint to increase coverage
"""
import pytest
from fastapi import HTTPException


class TestHealthCoverage:
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"]["connected"] is True
    
    def test_health_endpoint_with_db_error(self, client, db_session):
        """Test health endpoint when database is unavailable - FIXED"""
        from app.infrastructure.database import get_db
        from sqlalchemy.exc import OperationalError
        
        # Override get_db to raise exception
        def mock_get_db_error():
            raise OperationalError("Connection failed", None, None)
        
        client.app.dependency_overrides[get_db] = mock_get_db_error
        
        response = client.get("/health")
        # Should return 503 Service Unavailable
        assert response.status_code == 503
        
        data = response.json()
        assert "detail" in data
        assert "Database unreachable" in data["detail"]["message"]
        
        # Clean up
        client.app.dependency_overrides.clear()