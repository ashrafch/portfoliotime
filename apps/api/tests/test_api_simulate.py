"""Test API simulazioni: esecuzione, storico, proprietà (ownership)."""

import pytest
from tests.conftest import SIM_BODY


class TestSimulate:
    async def test_create_simulation(self, client, user_headers):
        r = await client.post("/simulate", headers=user_headers, json=SIM_BODY)
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "completed"
        assert set(data["result"]["allocazione"].keys()) == {
            "azioni", "bitcoin", "oro", "materie_prime", "obbligazioni"}
        assert "equity_curve" in data["result"]
        assert data["narrative"]

    async def test_simulation_requires_auth(self, client):
        r = await client.post("/simulate", json=SIM_BODY)
        assert r.status_code == 401

    async def test_list_my_simulations(self, client, user_headers):
        await client.post("/simulate", headers=user_headers, json=SIM_BODY)
        r = await client.get("/simulate", headers=user_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

    async def test_get_own_simulation(self, client, user_headers):
        created = (await client.post("/simulate", headers=user_headers, json=SIM_BODY)).json()
        r = await client.get(f"/simulate/{created['id']}", headers=user_headers)
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]

    async def test_cannot_access_others_simulation(self, client, user_headers, admin_headers):
        # creata dall'utente
        created = (await client.post("/simulate", headers=user_headers, json=SIM_BODY)).json()
        # un secondo utente normale non può vederla
        await client.post("/auth/register", json={
            "email": "altro@example.com", "password": "Password123"})
        other_token = (await client.post("/auth/login", json={
            "email": "altro@example.com", "password": "Password123"})).json()["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        r = await client.get(f"/simulate/{created['id']}", headers=other_headers)
        assert r.status_code == 403

        # ma il super_admin sì
        r_admin = await client.get(f"/simulate/{created['id']}", headers=admin_headers)
        assert r_admin.status_code == 200

    async def test_admin_sees_all_simulations(self, client, user_headers, admin_headers):
        await client.post("/simulate", headers=user_headers, json=SIM_BODY)
        r = await client.get("/admin/simulations", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1
        assert r.json()[0]["user_email"] == "user@portfoliotime.com"

    async def test_invalid_date_rejected(self, client, user_headers):
        bad = {**SIM_BODY, "date_from": "non-una-data"}
        r = await client.post("/simulate", headers=user_headers, json=bad)
        assert r.status_code == 422
