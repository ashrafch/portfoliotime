# AVVIO_LOCALE.md — Guida avvio locale su Windows

Guida passo-passo per avviare PortfolioTime in locale su Windows 10/11.

---

## 1. Prerequisiti

Installa questi strumenti **nell'ordine indicato**:

| Tool | Versione | Download |
|------|----------|----------|
| Docker Desktop | 4.x+ | https://www.docker.com/products/docker-desktop/ |
| Python | 3.12.x | https://www.python.org/downloads/ |
| Node.js | 20 LTS | https://nodejs.org/ |
| pnpm | 9.x | `npm install -g pnpm` (dopo Node.js) |
| Git | 2.x+ | https://git-scm.com/download/win |

> **Docker Desktop su Windows:** alla prima installazione, abilitare WSL2 quando richiesto. Riavviare il PC dopo l'installazione.

---

## 2. Configurazione variabili d'ambiente

```powershell
# Nella cartella portfoliotime/
Copy-Item .env.example .env
```

Apri `.env` con un editor e compila:

| Variabile | Come ottenerla |
|-----------|----------------|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ → API Keys → Create key |
| `FRED_API_KEY` | https://fred.stlouisfed.org/docs/api/api_key.html → Request API key (gratis) |
| `COINGECKO_API_KEY` | Lascia vuoto per il piano free. Demo key: https://www.coingecko.com/en/api |
| `JWT_SECRET` | Esegui in terminale: `python -c "import secrets; print(secrets.token_hex(32))"` |

Le altre variabili (DATABASE_URL, REDIS_URL, QDRANT_URL) vanno bene così per il locale.

---

## 3. Avvio infrastruttura con Docker

```powershell
# Dalla cartella portfoliotime/
docker compose up -d
```

Questo avvia:
- **PostgreSQL 16 + TimescaleDB** su `localhost:5432`
- **Redis 7** su `localhost:6379`
- **Qdrant** su `localhost:6333`

Verifica che i servizi siano up:

```powershell
docker compose ps
```

Attendi che tutti e tre mostrino `healthy` nella colonna STATUS (può richiedere 30-60 secondi al primo avvio).

---

## 4. Setup ambiente Python

```powershell
# Entra nella cartella API
cd apps\api

# Crea il virtual environment
python -m venv .venv

# Attiva il virtualenv (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Se ottieni errore "execution policy":
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Poi riprova il comando Activate.ps1

# Installa le dipendenze
pip install -r requirements.txt
```

---

## 5. Crea le tabelle database

```powershell
# Con il virtualenv attivo, dalla cartella apps/api/
alembic upgrade head
```

Se Alembic non è ancora configurato (prima esecuzione assoluta), crea la struttura:

```powershell
alembic init alembic
# Poi modifica alembic/env.py per usare DATABASE_URL da config.py
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

---

## 6. Prima ingestion RAG (knowledge-base)

```powershell
# Con virtualenv attivo, dalla cartella apps/api/
python rag/ingestion.py
```

Questo legge tutti i file in `knowledge-base/` e li indicizza in Qdrant.
Tempo stimato: 30-120 secondi (dipende dalla connessione per scaricare il modello di embedding).

Ri-esegui ogni volta che modifichi file in `knowledge-base/`.

---

## 7. Avvio API (hot reload)

```powershell
# Con virtualenv attivo, dalla cartella apps/api/
uvicorn main:app --reload --port 8000
```

Verifica: apri http://localhost:8000/docs — dovresti vedere la documentazione Swagger interattiva.

---

## 8. Avvio Frontend

In un **nuovo terminale PowerShell**:

```powershell
cd apps\web
pnpm install
pnpm dev
```

Il frontend si avvia su http://localhost:3000.

---

## 9. URL servizi locali

| Servizio | URL | Note |
|----------|-----|------|
| **Web App** | http://localhost:3000 | Next.js dev server |
| **API (Swagger)** | http://localhost:8000/docs | Documentazione interattiva |
| **API (ReDoc)** | http://localhost:8000/redoc | Documentazione alternativa |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | Visualizza collezioni vettoriali |
| **Redis** | localhost:6379 | Usa Redis Desktop Manager o `redis-cli` |
| **PostgreSQL** | localhost:5432 | User: portfoliotime / Pass: portfoliotime |

---

## 10. Troubleshooting — 5 errori comuni su Windows

### Errore 1: `uvicorn: command not found` o simile

**Causa:** Il virtualenv non è attivato.

**Soluzione:**
```powershell
# Verifica di essere nella cartella apps/api/
# Il prompt deve mostrare (.venv) davanti
.\.venv\Scripts\Activate.ps1
```

### Errore 2: `docker compose up` fallisce con "WSL2 not enabled"

**Causa:** Docker Desktop richiede WSL2 su Windows.

**Soluzione:**
```powershell
# In PowerShell come amministratore:
wsl --install
# Riavvia il PC, poi apri Docker Desktop e completa la configurazione
```

### Errore 3: Path separators — `ModuleNotFoundError` su import locali

**Causa:** Windows usa backslash `\`, ma Python/uvicorn si aspettano forward slash in certi contesti.

**Soluzione:** Usa sempre `cd apps\api` (backslash) in PowerShell, ma nei file Python usa `Path(__file__).parent` invece di stringhe hardcoded.

### Errore 4: `alembic upgrade head` fallisce con "connection refused"

**Causa:** PostgreSQL non è ancora partito (healthcheck non passato).

**Soluzione:**
```powershell
docker compose ps     # verifica che postgres sia "healthy"
docker compose logs postgres   # leggi i log se non diventa healthy
```

### Errore 5: `pnpm dev` fallisce con "next: command not found"

**Causa:** Le dipendenze Node non sono installate.

**Soluzione:**
```powershell
cd apps\web
pnpm install    # installa node_modules
pnpm dev        # poi avvia
```
