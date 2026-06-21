# PortfolioTime

Piattaforma ibrida **AI + dati finanziari verificati** per simulare le performance reali di un portafoglio su periodi storici precisi.

> **Architettura:** RAG-First, AI-Second. Il motore calcola i numeri. L'AI interpreta, mai inventa.

---

## Cos'è PortfolioTime

PortfolioTime risponde a una domanda semplice: *"Come sarebbe andato il mio portafoglio nel 2008?"*

L'utente configura il proprio profilo (età, tolleranza al rischio), seleziona uno scenario storico (es. Grande Recessione 2007-2009) e il sistema:

1. Calcola le allocazioni del **Chameleon Portfolio** (formule proprietarie del cliente, vedi [`docs/formule-cliente.md`](docs/formule-cliente.md))
2. Scarica i prezzi reali da Yahoo Finance, CoinGecko e FRED
3. Calcola CAGR, Max Drawdown, Sharpe Ratio, Volatilità annualizzata
4. Genera una narrativa contestuale via Claude (mai i numeri — solo l'interpretazione)

---

## Architettura ad alto livello

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser / PWA  ←→  Next.js 15 (apps/web)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST
┌────────────────────────────▼────────────────────────────────────┐
│  FastAPI (apps/api)                                             │
│  ├── engine/metrics.py   ← formule Chameleon + metriche std    │
│  ├── engine/simulator.py ← orchestratore simulazione           │
│  ├── data/               ← connettori Yahoo/CoinGecko/FRED     │
│  ├── rag/retrieval.py    ← interroga Qdrant                    │
│  └── workers/celery_app  ← simulazioni async > 2s              │
└────────┬─────────────────────────────────────┬──────────────────┘
         │                                     │
┌────────▼─────────┐  ┌──────────┐  ┌─────────▼─────────────────┐
│ PostgreSQL 16    │  │  Redis 7 │  │  Qdrant (vector store)    │
│ + TimescaleDB    │  │  (cache) │  │  knowledge-base embeddings│
└──────────────────┘  └──────────┘  └───────────────────────────┘
```

---

## Prerequisiti

| Tool | Versione minima | Note |
|------|-----------------|------|
| Docker Desktop | 4.x | Con WSL2 abilitato su Windows |
| Python | 3.12 | Via pyenv o python.org |
| Node.js | 20 LTS | |
| pnpm | 9.x | `npm install -g pnpm` |

---

## Quick Start (5 comandi)

```bash
# 1. Copia le variabili d'ambiente e compila le chiavi API
cp .env.example .env

# 2. Avvia database, cache e vector store
docker compose up -d

# 3. Installa dipendenze Python e crea le tabelle
cd apps/api && python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt && alembic upgrade head

# 4. Avvia l'API (hot reload)
uvicorn main:app --reload --port 8000

# 5. In un altro terminale — avvia il frontend
cd apps/web && pnpm install && pnpm dev
```

→ Guida completa passo-passo: [AVVIO_LOCALE.md](AVVIO_LOCALE.md)

---

## Riferimento core: formule del cliente

Il file [`docs/formule-cliente.md`](docs/formule-cliente.md) è la **fonte di verità** per il motore di calcolo. Contiene:

- Le 6 formule del **Chameleon Portfolio** estratte dal PDF originale
- Il grafo di dipendenza tra le formule
- I parametri di input con le fonti dati
- Le assunzioni e i delta rispetto ai modelli standard

**R7 (invariante architetturale):** Le formule del PDF cliente non si modificano senza aggiornare `docs/formule-cliente.md`.

---

## Struttura directory

```
portfoliotime/
├── AGENT.md                    ← contesto architetturale per AI assistants
├── README.md                   ← questo file
├── AVVIO_LOCALE.md             ← guida dettagliata avvio locale
├── docker-compose.yml          ← PostgreSQL + TimescaleDB + Redis + Qdrant
├── turbo.json                  ← Turborepo monorepo config
├── package.json                ← root workspace pnpm
├── .env.example                ← template variabili (committato)
├── .env                        ← valori reali (gitignored)
│
├── docs/
│   ├── formule-cliente.md      ← ★ analisi formule PDF — leggere prima di toccare engine/
│   └── formule-cliente-original.pdf
│
├── apps/
│   ├── api/                    ← FastAPI backend
│   │   ├── engine/             ← ★ motore finanziario (formule Chameleon + std)
│   │   ├── routers/            ← endpoint REST
│   │   ├── rag/                ← pipeline RAG (ingestion build-time, retrieval runtime)
│   │   ├── data/               ← connettori Yahoo/CoinGecko/FRED
│   │   ├── models/             ← SQLAlchemy ORM
│   │   ├── workers/            ← Celery async tasks
│   │   └── tests/              ← pytest unit tests
│   └── web/                    ← Next.js 15 frontend
│       └── app/                ← App Router pages
│
├── packages/
│   ├── types/                  ← TypeScript shared types
│   └── shared/                 ← scenarios.ts — lista scenari storici
│
└── knowledge-base/             ← documenti RAG (modificare → ri-eseguire ingestion)
    ├── scenarios/              ← 10 scenari storici con dati reali
    ├── formule/                ← documentazione metriche finanziarie
    └── glossario/
```

---

## Prossimi step di sviluppo

Vedi [AGENT.md](AGENT.md) per le priorità correnti. In breve:

1. Completare `apps/api/engine/metrics.py` con i test di verifica (`pytest tests/ -v`)
2. Implementare `/simulate` endpoint end-to-end
3. Collegare il frontend alla prima chiamata API reale
