"""Test API: stress test, goal planning, allocazione consigliata."""

import pytest


class TestStressTest:
    async def test_stress_test_struttura(self, client, user_headers):
        body = {"holdings": {"azioni": 6000, "obbligazioni": 3000, "oro": 1000}}
        r = await client.post("/portfolio/stress-test", headers=user_headers, json=body)
        assert r.status_code == 200
        d = r.json()
        assert d["total_value"] == pytest.approx(10000, abs=0.01)
        assert len(d["scenarios"]) >= 3
        for s in d["scenarios"]:
            assert "total_return" in s and "max_drawdown" in s and "final_value" in s

    async def test_stress_test_vuoto_422(self, client, user_headers):
        r = await client.post("/portfolio/stress-test", headers=user_headers, json={"holdings": {}})
        assert r.status_code == 422

    async def test_stress_test_requires_auth(self, client):
        r = await client.post("/portfolio/stress-test", json={"holdings": {"azioni": 100}})
        assert r.status_code == 401


class TestGoalPlan:
    async def test_goal_plan_struttura(self, client, user_headers):
        body = {"target": 50000, "horizon_years": 10, "initial_capital": 10000,
                "monthly_contribution": 200, "risk_profile": "bilanciato"}
        r = await client.post("/portfolio/goal-plan", headers=user_headers, json=body)
        assert r.status_code == 200
        d = r.json()
        assert 0.0 <= d["projection"]["probability_success"] <= 1.0
        assert d["allocation"] is not None
        assert d["reference_period"]["from"] and d["reference_period"]["to"]
        # required può essere 0 o un numero positivo
        assert d["required_monthly_contribution"] is None or d["required_monthly_contribution"] >= 0

    async def test_goal_plan_default_risk_da_profilo(self, client, user_headers):
        body = {"target": 30000, "horizon_years": 8, "initial_capital": 5000}
        r = await client.post("/portfolio/goal-plan", headers=user_headers, json=body)
        assert r.status_code == 200
        assert r.json()["risk_profile"] in ("conservativo", "bilanciato", "aggressivo")


class TestRecommended:
    async def test_recommended_struttura(self, client, user_headers):
        r = await client.get("/portfolio/recommended", headers=user_headers)
        assert r.status_code == 200
        d = r.json()
        assert set(d["allocazione"].keys()) == {"azioni", "bitcoin", "oro", "materie_prime", "obbligazioni"}
        assert d["source"] in ("fred", "profilo")
        # prima chiamata: nessuno snapshot precedente → nessun cambiamento
        assert d["changes"] == []

    async def test_recommended_rileva_cambiamento(self, client, user_headers):
        # prima chiamata: salva snapshot
        await client.get("/portfolio/recommended", headers=user_headers)
        # cambia un'assunzione macro del profilo → l'allocazione cambia
        await client.put("/me/profile", headers=user_headers, json={"default_tasso_fed": 0.5})
        r = await client.get("/portfolio/recommended", headers=user_headers)
        d = r.json()
        assert len(d["changes"]) > 0
        assert all({"asset", "da", "a"} <= set(c.keys()) for c in d["changes"])

    async def test_recommended_requires_auth(self, client):
        r = await client.get("/portfolio/recommended")
        assert r.status_code == 401


class TestAdvice:
    async def test_advice_struttura(self, client, user_headers):
        body = {"initial_capital": 10000, "monthly_contribution": 300,
                "horizon_years": 15, "target": 100000, "risk_profile": "bilanciato"}
        r = await client.post("/portfolio/advice", headers=user_headers, json=body)
        assert r.status_code == 200
        d = r.json()
        assert d["allocation"] is not None
        assert d["breakdown"] and all("amount_now" in b and "instrument" in b for b in d["breakdown"])
        # la somma degli importi ~ capitale iniziale
        tot = sum(b["amount_now"] for b in d["breakdown"])
        assert tot == pytest.approx(10000, abs=1.0)
        assert 0.0 <= d["projection"]["probability_success"] <= 1.0
        assert d["explanations"]["mix"] and d["explanations"]["probability"]
        assert "consulenza" in d["disclaimer"].lower()

    async def test_advice_senza_target(self, client, user_headers):
        body = {"initial_capital": 5000, "monthly_contribution": 100, "horizon_years": 10}
        r = await client.post("/portfolio/advice", headers=user_headers, json=body)
        assert r.status_code == 200
        d = r.json()
        assert d["required_monthly_contribution"] is None  # nessun target → nessun calcolo
        assert d["projection"]["final_value"]["p50"] is not None

    async def test_advice_basis_chameleon(self, client, user_headers):
        body = {"initial_capital": 10000, "monthly_contribution": 0,
                "horizon_years": 10, "basis": "chameleon"}
        r = await client.post("/portfolio/advice", headers=user_headers, json=body)
        assert r.status_code == 200
        assert r.json()["basis"] == "chameleon"

    async def test_advice_requires_auth(self, client):
        r = await client.post("/portfolio/advice", json={"horizon_years": 10})
        assert r.status_code == 401

    async def test_advice_ripartizione_anche_su_mensile(self, client, user_headers):
        # capitale iniziale 0, solo versamento mensile → la ripartizione deve esserci comunque
        body = {"initial_capital": 0, "monthly_contribution": 500, "horizon_years": 10,
                "risk_profile": "bilanciato"}
        d = (await client.post("/portfolio/advice", headers=user_headers, json=body)).json()
        assert all(b["amount_initial"] == 0 for b in d["breakdown"])
        assert sum(b["amount_monthly"] for b in d["breakdown"]) == pytest.approx(500, abs=1.0)
        assert d["composition"]["initial"] == 0
        assert d["composition"]["monthly_total"] > 0

    async def test_allocation_presets(self, client, user_headers):
        r = await client.get("/portfolio/allocation-presets", headers=user_headers)
        assert r.status_code == 200
        d = r.json()
        assert set(d["strategic"].keys()) >= {"azioni", "obbligazioni"}
        assert d["recommended"] is not None
        assert d["recommended_source"] in ("fred", "profilo")


class TestNotifications:
    async def test_no_changes_initially(self, client, user_headers):
        r = await client.get("/me/notifications", headers=user_headers)
        assert r.status_code == 200
        assert r.json()["has_changes"] is False

    async def test_detects_change_after_profile_update(self, client, user_headers):
        # segna come visto
        await client.get("/portfolio/recommended", headers=user_headers)
        # cambia assunzione macro → l'allocazione cambia
        await client.put("/me/profile", headers=user_headers, json={"default_tasso_fed": 0.5})
        r = await client.get("/me/notifications", headers=user_headers)
        d = r.json()
        assert d["has_changes"] is True
        assert len(d["changes"]) > 0
