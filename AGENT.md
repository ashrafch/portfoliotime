# AGENT.md — PortfolioTime

## Identità del progetto

PortfolioTime è una piattaforma ibrida AI + dati finanziari verificati.
Permette di simulare le performance reali di un portafoglio su periodi storici precisi.
Architettura: RAG-First, AI-Second. Il motore calcola i numeri. L'AI interpreta, mai inventa.

---

## Stack — riferimento rapido

```
Backend     FastAPI + Python 3.12 · Celery + Redis · SQLAlchemy · Pandas/NumPy
Database    PostgreSQL + TimescaleDB (time-series) · Redis (cache/queue)
AI          Claude claude-sonnet-4-6 · LlamaIndex (RAG) · Qdrant (vector DB)
Frontend    Next.js 15 App Router · TailwindCSS · shadcn/ui · TradingView Lightweight
Infra       Docker Compose (dev) · Railway (staging) · Monorepo Turborepo
```

---

## Struttura directory

```
portfoliotime/
├── apps/
│   ├── web/                   # Next.js 15 — frontend + PWA
│   │   ├── app/               # App Router pages
│   │   ├── components/        # UI components (shadcn base)
│   │   └── lib/               # Client utilities, API hooks
│   └── api/                   # FastAPI backend
│       ├── routers/           # endpoint modules
│       ├── engine/            # motore calcolo finanziario
│       │   ├── metrics.py     # CAGR, Sharpe, Drawdown, VaR...
│       │   └── simulator.py   # orchestratore simulazione
│       ├── rag/               # pipeline RAG
│       │   ├── ingestion.py   # build-time: chunking + embedding
│       │   └── retrieval.py   # runtime: query Qdrant
│       ├── data/              # connettori fonti dati esterne
│       │   ├── yfinance.py
│       │   ├── coingecko.py
│       │   └── fred.py
│       └── models/            # SQLAlchemy models
├── packages/
│   ├── types/                 # TypeScript types condivisi web/mobile
│   └── shared/                # logica condivisa (validazione, costanti)
├── knowledge-base/            # documenti RAG — MAI modificare senza aggiornare ingestion
│   ├── scenarios/             # un .md per scenario storico
│   ├── formule/               # una .md per metrica finanziaria
│   └── glossario/
├── infra/
│   └── docker-compose.yml
└── AGENT.md                   # questo file
```

---

## Regole architetturali — non derogare mai

**R1 — Separazione dati/AI**
Il motore finanziario (`engine/`) calcola SEMPRE i numeri da DB.
Il LLM riceve SOLO l'output del motore. Non genera mai valori numerici autonomamente.
Se vedi codice che chiede al LLM di calcolare rendimenti o metriche: è un bug architetturale.

**R2 — Fonte tracciata**
Ogni valore numerico esposto all'utente deve avere la sua sorgente (`source: "yahoo_finance" | "coingecko" | "fred"`).
Propagare il campo `source` dagli strati dati fino alla risposta API.

**R3 — RAG build-time**
L'ingestion (`rag/ingestion.py`) è un job offline, non real-time.
Non chiamare mai l'embedding model durante una request HTTP.
Qdrant viene interrogato a runtime, mai scritto.

**R4 — Mobile-first CSS**
Tutto il CSS in `web/` parte da breakpoint mobile (`sm:`, `md:`, `lg:`).
La PWA deve funzionare su schermo 375px senza scroll orizzontale.

**R5 — Async ovunque**
Tutte le route FastAPI sono `async def`.
Le simulazioni pesanti vanno su Celery, non inline nella request.
Pattern: POST /simulate → ritorna job_id → GET /simulate/{job_id}/result.

---

## Comportamento atteso in questa codebase

**Quando scrivi codice:**
- Usa i tipi esistenti in `packages/types/` prima di crearne nuovi
- Le metriche finanziarie vanno in `engine/metrics.py`, non sparse nei router
- I connettori dati esterni hanno sempre retry logic e timeout esplicito (default: 10s)
- Non usare `any` in TypeScript — se il tipo non esiste, crealo in `packages/types/`

**Quando modifichi il knowledge-base:**
- Ogni modifica a `knowledge-base/` richiede di ri-eseguire `python api/rag/ingestion.py`
- I file .md seguono lo schema: H1 titolo, H2 sezioni (Contesto / Timeline / Impatto / Lezione)
- Il chunking avviene su separatori H2 — non usare H3 come struttura primaria

**Quando aggiungi uno scenario storico:**
1. Crea `knowledge-base/scenarios/YYYY-nome-scenario.md`
2. Aggiungi la entry in `packages/shared/scenarios.ts` (id, label, dateFrom, dateTo)
3. Ri-esegui ingestion
4. Aggiungi test in `api/tests/test_simulator.py` per il nuovo periodo

---

## Comandi operativi

```bash
# Dev locale completo
docker compose up -d          # PG + TimescaleDB + Redis + Qdrant
cd apps/api && uvicorn main:app --reload
cd apps/web && pnpm dev

# Ingestion RAG (dopo modifiche a knowledge-base/)
cd apps/api && python rag/ingestion.py

# Test
cd apps/api && pytest tests/ -v
cd apps/web && pnpm test

# Type check
pnpm turbo typecheck
```

---

## Variabili d'ambiente richieste

```
# API
DATABASE_URL          postgresql://...
REDIS_URL             redis://localhost:6379
QDRANT_URL            http://localhost:6333
ANTHROPIC_API_KEY     sk-ant-...
FRED_API_KEY          (gratuito su fred.stlouisfed.org)
COINGECKO_API_KEY     (opzionale, aumenta rate limit)

# Web
NEXT_PUBLIC_API_URL   http://localhost:8000
```

---

## Metriche finanziarie implementate

| Metrica | File | Fase |
|---|---|---|
| CAGR | engine/metrics.py | MVP |
| Max Drawdown | engine/metrics.py | MVP |
| Sharpe Ratio | engine/metrics.py | MVP |
| Volatilità annualizzata | engine/metrics.py | MVP |
| Rendimento reale (vs FRED CPI) | engine/metrics.py | MVP |
| Sortino Ratio | engine/metrics.py | Fase 2 |
| VaR (95%) | engine/metrics.py | Fase 2 |
| Beta vs benchmark | engine/metrics.py | Fase 2 |
| Correlation Matrix | engine/metrics.py | Fase 2 |

---

## Limiti e vincoli noti

- Dati crypto disponibili da CoinGecko: **dal 1 gennaio 2013** in poi. Non simulare crypto prima di questa data.
- yfinance può avere rate limiting: usare la cache TimescaleDB, non chiamare l'API ad ogni request.
- Claude claude-sonnet-4-6 max_tokens per narrativa contestuale: **1500 token** — la risposta deve essere concisa.
- Simulazioni su periodi > 10 anni con > 20 asset vanno obbligatoriamente su Celery (tempo calcolo > 2s).

---

## Anti-pattern — non fare mai

```python
# ❌ MAI — LLM che genera numeri
response = claude.ask("Quanto avrebbe reso un portafoglio 60/40 nel 2008?")

# ✅ CORRETTO — motore calcola, LLM interpreta
metrics = engine.simulate(portfolio, "2007-01-01", "2009-12-31")
context = rag.retrieve("grande recessione 2008 impatto mercati")
narrative = claude.interpret(metrics=metrics, context=context)
```

```typescript
// ❌ MAI — dati finanziari hardcoded nel frontend
const sp500Return2008 = -0.37

// ✅ CORRETTO — sempre da API
const { data } = await api.get('/benchmarks/sp500?from=2008&to=2009')
```

---

## Priorità di sviluppo corrente

Controllare `TODO.md` per lo stato aggiornato. In assenza di indicazioni specifiche:
1. Stabilità del motore finanziario (`engine/`) — zero errori sui calcoli
2. Copertura test metriche > 90%
3. Performance API: /simulate deve rispondere < 500ms per periodi < 5 anni
4. Poi: feature frontend

---

## Git — workflow e convenzioni di commit

### Setup iniziale (già eseguito)

```bash
git init
git remote add origin https://github.com/<username>/portfoliotime.git
```

### Convenzione commit message

Usare il formato Conventional Commits:

```
<tipo>(<scope>): <descrizione breve in italiano>

[corpo opzionale]
[footer opzionale]
```

**Tipi:**
| Tipo | Quando usarlo |
|------|---------------|
| `feat` | Nuova funzionalità |
| `fix` | Bug fix |
| `docs` | Solo documentazione |
| `refactor` | Refactoring senza nuove feature |
| `test` | Aggiunta/modifica test |
| `chore` | Build, config, dipendenze |
| `perf` | Miglioramento performance |

**Scope (opzionale):** `engine`, `api`, `web`, `rag`, `docker`, `kb` (knowledge-base)

**Esempi:**
```bash
feat(engine): implementa formule Chameleon Portfolio dal PDF cliente
fix(engine): corregge edge case divisione per zero in calc_cagr
docs(kb): aggiunge scenario COVID crash con dati storici reali
test(engine): aggiunge test unitari per tutte le formule PDF cliente
chore(docker): aggiunge healthcheck a tutti i servizi compose
```

### Workflow standard

```bash
# 1. Controlla stato locale
git status
git diff

# 2. Aggiungi file specifici (MAI git add -A — rischio di committare .env)
git add apps/api/engine/metrics.py
git add apps/api/tests/test_metrics.py

# 3. Commit con messaggio descrittivo
git commit -m "feat(engine): implementa calc_sharpe_ratio con edge case handling"

# 4. Push sul branch corrente
git push origin main
```

### Regola critica: .env non va mai su git

Il file `.env` è nel `.gitignore`. Solo `.env.example` (con valori placeholder) va committato.
Verificare sempre con `git status` prima di committare.

### Branch strategy (per future PR)

```
main          ← produzione / staging
develop       ← integrazione feature
feature/xxx   ← sviluppo singola feature
hotfix/xxx    ← fix urgenti su main
```

Per il progetto in fase MVP: lavorare su `main` direttamente. Introdurre i branch quando si aggiungono collaboratori.

### Pubblicare su GitHub

```bash
# Crea repo su GitHub (via browser o CLI)
gh repo create portfoliotime --private --source=. --remote=origin

# Push iniziale
git push -u origin main

# Per push successivi
git push
```
