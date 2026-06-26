"""Test API autenticazione e RBAC."""

import pytest


class TestAuth:
    async def test_login_admin_ok(self, client):
        r = await client.post("/auth/login", json={
            "email": "admin@portfoliotime.com", "password": "Admin123!"})
        assert r.status_code == 200
        data = r.json()
        assert data["user"]["role"] == "super_admin"
        assert len(data["access_token"]) > 20

    async def test_login_wrong_password(self, client):
        r = await client.post("/auth/login", json={
            "email": "admin@portfoliotime.com", "password": "sbagliata"})
        assert r.status_code == 401

    async def test_login_unknown_email(self, client):
        r = await client.post("/auth/login", json={
            "email": "nessuno@example.com", "password": "x"})
        assert r.status_code == 401

    async def test_register_new_user(self, client):
        r = await client.post("/auth/register", json={
            "email": "nuovo@example.com", "password": "Password123", "full_name": "Nuovo"})
        assert r.status_code == 201
        data = r.json()
        assert data["user"]["email"] == "nuovo@example.com"
        assert data["user"]["role"] == "user"

    async def test_register_duplicate(self, client):
        r = await client.post("/auth/register", json={
            "email": "user@portfoliotime.com", "password": "Password123"})
        assert r.status_code == 409

    async def test_register_short_password(self, client):
        r = await client.post("/auth/register", json={
            "email": "x@example.com", "password": "corta"})
        assert r.status_code == 422

    async def test_me_with_token(self, client, user_headers):
        r = await client.get("/auth/me", headers=user_headers)
        assert r.status_code == 200
        assert r.json()["email"] == "user@portfoliotime.com"

    async def test_me_without_token(self, client):
        r = await client.get("/auth/me")
        assert r.status_code == 401


class TestRBAC:
    async def test_user_cannot_access_admin_stats(self, client, user_headers):
        r = await client.get("/admin/stats", headers=user_headers)
        assert r.status_code == 403

    async def test_admin_can_access_stats(self, client, admin_headers):
        r = await client.get("/admin/stats", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["total_users"] >= 2

    async def test_admin_can_list_users(self, client, admin_headers):
        r = await client.get("/admin/users", headers=admin_headers)
        assert r.status_code == 200
        emails = {u["email"] for u in r.json()}
        assert "admin@portfoliotime.com" in emails

    async def test_admin_cannot_delete_self(self, client, admin_headers):
        me = (await client.get("/auth/me", headers=admin_headers)).json()
        r = await client.delete(f"/admin/users/{me['id']}", headers=admin_headers)
        assert r.status_code == 400

    async def test_deactivated_user_cannot_login(self, client, admin_headers):
        # crea, disattiva, poi prova login
        reg = await client.post("/auth/register", json={
            "email": "temp@example.com", "password": "Password123"})
        uid = reg.json()["user"]["id"]
        await client.patch(f"/admin/users/{uid}", headers=admin_headers, json={"is_active": False})
        r = await client.post("/auth/login", json={
            "email": "temp@example.com", "password": "Password123"})
        assert r.status_code == 403
