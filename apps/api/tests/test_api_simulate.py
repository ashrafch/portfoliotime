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

    async def test_result_includes_advanced_metrics(self, client, user_headers):
        r = await client.post("/simulate", headers=user_headers, json=SIM_BODY)
        res = r.json()["result"]
        for key in ["sortino_ratio", "calmar_ratio", "var_95", "cvar_95", "beta",
                    "max_underwater_days", "money"]:
            assert key in res
        # money: lump sum → final_value coerente col total_return
        m = res["money"]
        assert m["total_invested"] == pytest.approx(10000.0, abs=0.01)
        assert m["is_dca"] is False

    async def test_dca_money_weighted_differs(self, client, user_headers):
        body = {**SIM_BODY, "initial_capital": 10000, "contribution": 200,
                "contribution_frequency": "monthly"}
        res = (await client.post("/simulate", headers=user_headers, json=body)).json()["result"]
        m = res["money"]
        assert m["is_dca"] is True
        assert m["contributions_count"] > 0
        # totale versato = iniziale + n*contributo
        assert m["total_invested"] == pytest.approx(10000 + m["contributions_count"] * 200, abs=0.01)

    async def test_invalid_frequency_rejected(self, client, user_headers):
        bad = {**SIM_BODY, "contribution_frequency": "settimanale"}
        r = await client.post("/simulate", headers=user_headers, json=bad)
        assert r.status_code == 422

    async def test_montecarlo_endpoint(self, client, user_headers):
        created = (await client.post("/simulate", headers=user_headers, json=SIM_BODY)).json()
        r = await client.get(f"/simulate/{created['id']}/montecarlo?n_sims=200", headers=user_headers)
        assert r.status_code == 200
        d = r.json()
        assert d["n_simulations"] == 200
        assert {"p5", "p50", "p95"} <= set(d["final_return"].keys())
        assert 0.0 <= d["prob_loss"] <= 1.0
        assert "disclaimer" in d

    async def test_export_csv(self, client, user_headers):
        created = (await client.post("/simulate", headers=user_headers, json=SIM_BODY)).json()
        r = await client.get(f"/simulate/{created['id']}/export.csv", headers=user_headers)
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        assert "total_return" in r.text

    async def test_montecarlo_ownership(self, client, user_headers):
        created = (await client.post("/simulate", headers=user_headers, json=SIM_BODY)).json()
        await client.post("/auth/register", json={"email": "mc@example.com", "password": "Password123"})
        other = (await client.post("/auth/login", json={
            "email": "mc@example.com", "password": "Password123"})).json()["access_token"]
        r = await client.get(f"/simulate/{created['id']}/montecarlo",
                             headers={"Authorization": f"Bearer {other}"})
        assert r.status_code == 403


class TestEvents:
    async def test_events_in_range(self, client):
        r = await client.get("/scenarios/events?date_from=2007-10-09&date_to=2009-03-09")
        assert r.status_code == 200
        events = r.json()
        labels = [e["label"] for e in events]
        assert any("Lehman" in l for l in labels)
        # tutti dentro il range
        assert all("2007-10-09" <= e["date"] <= "2009-03-09" for e in events)

    async def test_events_empty_range(self, client):
        r = await client.get("/scenarios/events?date_from=1990-01-01&date_to=1991-01-01")
        assert r.status_code == 200
        assert r.json() == []
