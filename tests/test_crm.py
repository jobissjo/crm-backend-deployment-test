import uuid

import httpx
import pytest
from sqlalchemy import delete

from app.db import engine, session_factory
from app.main import app
from app.models import User


@pytest.mark.asyncio
async def test_crm_ownership_and_relationships():
    emails = [f"{uuid.uuid4()}@example.com" for _ in range(2)]
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            headers = []
            for email in emails:
                response = await client.post("/api/v1/auth/register", json={"email": email, "name": "Tester", "password": "test-password-123"})
                assert response.status_code == 201, response.text
                assert "password_hash" not in response.json()
                response = await client.post("/api/v1/auth/login", json={"email": email, "password": "test-password-123"})
                assert response.status_code == 200
                headers.append({"Authorization": f"Bearer {response.json()['access_token']}"})
            assert (await client.get("/api/v1/companies")).status_code == 401
            response = await client.post("/api/v1/companies", headers=headers[0], json={"name": "Acme"})
            assert response.status_code == 201, response.text
            company_id = response.json()["id"]
            assert (await client.get(f"/api/v1/companies/{company_id}", headers=headers[1])).status_code == 404
            assert (await client.get("/api/v1/companies", headers=headers[1])).json() == []
            assert (await client.post("/api/v1/contacts", headers=headers[1], json={"name": "Other", "company_id": company_id})).status_code == 404
            response = await client.post("/api/v1/contacts", headers=headers[0], json={"name": "Alice", "company_id": company_id})
            assert response.status_code == 201
            contact_id = response.json()["id"]
            assert (await client.post("/api/v1/deals", headers=headers[0], json={"title": "Invalid", "value": "-1"})).status_code == 422
            response = await client.post("/api/v1/deals", headers=headers[0], json={"title": "Contract", "value": "123.45", "contact_id": contact_id})
            assert response.status_code == 201
            deal_id = response.json()["id"]
            response = await client.post("/api/v1/tasks", headers=headers[0], json={"title": "Call", "deal_id": deal_id, "due_at": "2026-12-01T10:00:00+05:30"})
            assert response.status_code == 201
            task_id = response.json()["id"]
            assert (await client.put(f"/api/v1/tasks/{task_id}", headers=headers[0], json={"title": "Call", "status": "done"})).json()["status"] == "done"
            response = await client.get("/api/v1/dashboard", headers=headers[0])
            assert response.json()["counts"]["deals"] == 1
            assert response.json()["pipeline"][0]["value"] == "123.45"
            assert (await client.delete(f"/api/v1/companies/{company_id}", headers=headers[0])).status_code == 204
            assert (await client.get(f"/api/v1/contacts/{contact_id}", headers=headers[0])).json()["company_id"] is None
    finally:
        async with session_factory() as session:
            await session.execute(delete(User).where(User.email.in_(emails)))
            await session.commit()
        await engine.dispose()
