# PortfolioTime — Guida per lo sviluppatore

Riferimento tecnico completo del progetto: architettura, moduli, API, scelte
metodologiche e procedure operative. Pensata per chi mantiene ed estende il codice.

---

## 1. Panoramica

PortfolioTime è una piattaforma **AI + dati finanziari verificati** che simula la
performance di un portafoglio su periodi storici reali.

Principio architetturale di fondo: **il motore calcola i numeri, l'AI li interpreta**.
L'LLM non genera mai valori numerici (vedi regola R1).

### Stack

| Livello | Tecnologia |
|---|---|
| Backend | FastAPI · Python 3.12 · SQLAlchemy 2 (async) · Pandas/NumPy |
| Database | PostgreSQL 16 + TimescaleDB · Redis (cache/broker) · Qdrant (vector) |
| Migrazioni | Alembic (sync, psycopg2) |
| AI | Claude (`claude-sonnet-4-6`) opzionale · LlamaIndex/Qdrant per il RAG |
| Frontend | Next.js 15 (App Router) · React 19 · TailwindCSS · TypeScript |
| Infra | Docker Compose · monorepo pnpm + Turborepo |

### Avvio

```bash
docker compose up -d        # tutto: db, redis, qdrant, api, web
```

- Web: <http://localhost:3000> · API/Swagger: <http://localhost:8000/docs>
- Le migrazioni e il seed degli utenti girano **automaticamente** all'avvio dell'API.
- Hot reload attivo: il codice è montato come volume (modifica → ricarica).

---

## 2. Struttura del repository

```
portfoliotime/
├── apps/
│   ├── api/                      # backend FastAPI
│   │   ├── main.py               # app + lifespan (migrazioni + seed) + CORS + router
│   │   ├── config.py             # Settings (pydantic-settings, da .env)
│   │   ├── database.py           # engine async, get_db, Base
│   │   ├── security.py           # bcrypt, JWT, dependency get_current_user / require_super_admin
│   │   ├── seed.py               # crea admin + utente demo (idempotente)
│   │   ├── migrations.py         # runner Alembic all'avvio (stamp/upgrade)
│   │   ├── alembic/              # env.py (sync) + versions/0001_initial_schema.py
│   │   ├── engine/
│   │   │   ├── metrics.py        # formule Chameleon + metriche (base e avanzate)
│   │   │   ├── simulator.py      # orchestratore: allocazione → metriche → money/DCA
│   │   │   ├── montecarlo.py     # proiezione bootstrap
│   │   │   └── narrative.py      # interpretazione (Claude o template)
│   │   ├── data/
│   │   │   ├── yfinance_client.py   # download prezzi (azioni/ETF + BTC)
│   │   │   ├── price_repository.py  # cache TimescaleDB + fallback
│   │   │   ├── fred_client.py       # tassi/inflazione (FRED, opzionale)
│   │   │   └── coingecko_client.py  # alternativa BTC (non usata di default)
│   │   ├── routers/             # auth, me, admin, simulate, scenarios, portfolio, macro
│   │   ├── models/              # user, profile, portfolio (SimulationRecord), price_cache
│   │   └── tests/              # 87 test (engine, metriche avanzate, API)
│   └── web/                      # frontend Next.js
│       ├── app/
│       │   ├── (auth)/           # login, register (pubbliche)
│       │   └── (app)/            # dashboard, simulate, results, compare, profile, admin (protette)
│       ├── components/          # Navbar, EquityChart, CompareChart, MonteCarloChart, InfoTip
│       └── lib/                 # api.ts, auth.tsx (context), types.ts, format.ts
├── packages/                     # types/ e shared/ (scenari) condivisi
├── knowledge-base/               # scenari, formule, glossario (per il RAG)
└── docs/                         # formule-cliente.md, GUIDA-UTENTE.md, questa guida
```

---

## 3. Regole architetturali (invarianti)

| ID | Regola |
|----|--------|
| R1 | Il motore calcola SEMPRE i numeri. L'LLM riceve solo l'output, non genera valori. |
| R2 | Ogni valore numerico porta la sua `source` (`yahoo_finance` \| `cache` \| `fred` \| `calculated`). |
| R3 | L'ingestion RAG è build-time. Mai chiamare l'embedding model in una request HTTP. |
| R4 | CSS mobile-first; la PWA funziona a 375px senza scroll orizzontale. |
| R5 | Tutte le route FastAPI sono `async def`. |
| R6 | Dati crypto solo dal 2013-01-01 — validati lato API. |
| R7 | Le formule del PDF cliente sono la fonte di verità: non modificarle senza aggiornare `docs/formule-cliente.md`. |

---

## 4. Autenticazione e ruoli (RBAC)

- **Hashing**: `bcrypt` diretto (`security.py`), troncamento a 72 byte.
- **Token**: JWT (python-jose) con `sub`, `email`, `role`, `exp`.
- **Dependency**:
  - `get_current_user` — decodifica il token, carica l'utente, verifica `is_active`.
  - `require_super_admin` — 403 se il ruolo non è `super_admin`.
- **Ruoli**: `super_admin` (tutto + `/admin/*`) e `user` (funzionalità standard).
- **Seed** (`seed.py`, all'avvio): `admin@portfoliotime.com` / `Admin123!` e
  `user@portfoliotime.com` / `User123!`.
- Endpoint: `/auth/login` (JSON, usato dal web), `/auth/token` (OAuth2 form, per
  il bottone *Authorize* di Swagger), `/auth/register`, `/auth/me`.

> Nota: il validatore email rifiuta i TLD riservati (es. `.local`) — usare domini reali.

---

## 5. Dati di mercato e affidabilità

### Cache prezzi (`data/price_repository.py`)
È il cuore dell'affidabilità: yfinance non è più un single point of failure.

`get_prices(db, tickers, date_from, date_to)` per ogni ticker:
1. legge la cache TimescaleDB (`price_cache`);
2. se la copertura del periodo è sufficiente (euristica con tolleranza ai bordi e
   ratio minimo) → usa la cache (`source="cache"`);
3. altrimenti scarica da yfinance, salva (delete+insert idempotente) e restituisce
   (`source="yahoo_finance"`);
4. se il download fallisce ma c'è cache parziale → usa la cache con un **warning**
   (degradazione graziosa); se non c'è nulla → warning esplicito.

Effetto: la **prima** simulazione di un periodo scarica (~6s), le successive sullo
stesso periodo sono servite dal DB (~1s) e resistono ai downtime di yfinance.

### FRED (`data/fred_client.py`, opzionale)
Se `FRED_API_KEY` è configurata:
- `GET /macro/suggest` pre-compila tasso FED, inflazione, tasso nominale dal periodo
  (serie `DFF`, `CPIAUCSL`, `GS10`);
- il rendimento reale viene calcolato dall'**inflazione storica reale** (`source="fred"`),
  altrimenti dal valore inserito dall'utente (`source="calculated"`).

Senza chiave, tutto resta funzionante con fallback.

---

## 6. Motore di calcolo

### Formule Chameleon (`engine/metrics.py`, STRATO 1)
Le 5 funzioni proprietarie dal PDF cliente (`chameleon_azioni`, `_bitcoin`, `_oro`,
`_materie_prime`, `_portafoglio`) + override QE. Sono la fonte di verità (R7) e
documentate in `docs/formule-cliente.md`.

### Metriche (STRATO 2 e 2b)
| Funzione | Cosa misura |
|---|---|
| `calc_cagr` | rendimento medio annuo composto |
| `calc_max_drawdown` | perdita massima picco→minimo |
| `calc_sharpe_ratio` | rendimento per unità di rischio totale |
| `calc_annualized_volatility` | deviazione standard annualizzata |
| `calc_real_return` | rendimento al netto inflazione (Fisher) |
| `calc_sortino_ratio` | Sharpe ma con sola downside deviation |
| `calc_calmar_ratio` | CAGR / |max drawdown| |
| `calc_historical_var` | VaR storico giornaliero 95% (quantile empirico) |
| `calc_historical_cvar` | Expected Shortfall (media della coda) |
| `calc_beta` | Cov(p,b)/Var(b) vs benchmark |
| `calc_underwater_recovery` | max giorni sotto il massimo + flag recuperato |

Tutte tipizzate, con gestione edge case (serie vuote, divisioni per zero, NaN) e
**test con valori calcolati a mano** (`tests/test_advanced_metrics.py`).

### Orchestratore (`engine/simulator.py`)
`run_simulation(sim_input, prices, allocation_override=None)`:
1. calcola l'allocazione (Chameleon o `custom` se `allocation_override`);
2. costruisce la serie del portafoglio pesata (ribilanciamento giornaliero);
3. calcola tutte le metriche + curva equity (downsampled, base 100) + beta vs benchmark;
4. calcola la **proiezione in denaro** (`_money_projection`).

`compute_portfolio_returns(...)` espone i rendimenti giornalieri (usato da Monte Carlo).

### Importi e DCA — nota metodologica importante
`_money_projection` distingue **due rendimenti diversi**, senza confonderli:
- **time-weighted** (`total_return`, CAGR…) = performance della *strategia*;
- **money-weighted** (`money.money_return = valore_finale / totale_versato − 1`) =
  risultato dei *tuoi soldi* con il piano di accumulo. Ogni versamento cresce dalla
  propria data: i versamenti recenti rendono meno (corretto e atteso).

### Monte Carlo (`engine/montecarlo.py`)
`bootstrap_projection(returns, n_sims)`: ricampiona i rendimenti giornalieri con
reimmissione (i.i.d.), calcola percentili del rendimento finale (p5…p95),
probabilità di perdita e bande temporali per il fan chart.

> **Limite dichiarato** (anche in UI): bootstrap i.i.d. ignora autocorrelazione e
> volatility clustering, e campiona dallo *stesso* periodo. È una proiezione, non una
> previsione. Evoluzione naturale: *block bootstrap*.

### Narrativa (`engine/narrative.py`)
`build_narrative(sim_input, result, profile)`: se `ANTHROPIC_API_KEY` è presente usa
Claude passando **solo numeri già calcolati** (R1); altrimenti genera un testo
deterministico dai numeri. In entrambi i casi è personalizzata sul profilo di rischio.

---

## 7. Persistenza e modelli

| Modello | Tabella | Note |
|---|---|---|
| `User` | `users` | ruolo, `is_active`, hash password |
| `InvestorProfile` | `investor_profiles` | 1:1 con utente, default per le simulazioni |
| `SimulationRecord` | `simulation_records` | input + `result` (JSON) + narrativa, per-utente |
| `PriceCache` | `price_cache` | cache prezzi con `source`, unique (ticker, date) |

I NaN vengono convertiti in `null` prima del salvataggio JSON (`_clean_nan`).

### Migrazioni (Alembic)
- Sorgente di verità dello schema. Runner all'avvio (`migrations.py`) in un thread:
  - DB vuoto → `upgrade head`;
  - DB legacy (creato da vecchio `create_all`, senza `alembic_version`) → `stamp head`
    (adozione **senza perdita dati**) poi `upgrade head`;
  - DB già migrato → `upgrade head`.
- Creare una nuova migrazione (da `apps/api`, con DB raggiungibile):
  ```bash
  alembic revision --autogenerate -m "descrizione"
  alembic upgrade head
  ```

---

## 8. API — riferimento rapido

| Metodo | Endpoint | Auth | Descrizione |
|---|---|---|---|
| POST | `/auth/register` | — | registra un utente (ruolo `user`) |
| POST | `/auth/login` | — | login JSON → token + utente |
| POST | `/auth/token` | — | login OAuth2 form (Swagger) |
| GET | `/auth/me` | sì | profilo dell'utente autenticato |
| GET/PUT | `/me/profile` | sì | profilo investitore (auto-creato) |
| GET | `/me/analytics` | sì | aggregati sullo storico personale |
| POST | `/portfolio/allocation` | sì | anteprima allocazione (no dati di mercato) |
| GET | `/scenarios` | — | elenco scenari storici |
| GET | `/scenarios/events` | — | eventi macro reali nel range `date_from..date_to` |
| POST | `/simulate` | sì | esegue + salva una simulazione |
| GET | `/simulate` | sì | storico dell'utente |
| GET | `/simulate/{id}` | sì* | dettaglio (proprietario o super_admin) |
| GET | `/simulate/{id}/montecarlo` | sì* | proiezione bootstrap |
| GET | `/simulate/{id}/export.csv` | sì* | export CSV (download) |
| GET | `/macro/suggest` | sì | parametri macro reali da FRED |
| GET | `/admin/stats` | admin | statistiche piattaforma |
| GET | `/admin/users` | admin | elenco utenti + conteggi |
| PATCH | `/admin/users/{id}` | admin | cambia ruolo / attivazione |
| DELETE | `/admin/users/{id}` | admin | elimina utente + sue simulazioni |
| GET | `/admin/simulations` | admin | tutte le simulazioni (cross-user) |

`*` = proprietario della risorsa oppure super_admin.

---

## 9. Frontend

- **Auth**: `lib/auth.tsx` (React context + token in localStorage) avvolge l'app;
  `lib/api.ts` è il client centralizzato che inserisce l'header `Authorization`.
- **Route protette**: gruppo `app/(app)/` con layout client che redirige a `/login`
  se non autenticati e mostra la `Navbar` (link *Admin* solo per super_admin).
- **Pagine**: `dashboard` (storico + analytics + modalità confronto), `simulate`
  (form con scenari rapidi, regime macro / FRED autofill, allocazione Chameleon o
  custom, capitale + DCA), `results/[jobId]` (semaforo, denaro, spiegazioni, grafico
  con eventi, metriche con tooltip, Monte Carlo on-demand, export), `compare`
  (due simulazioni affiancate), `profile`, `admin`.
- **Grafici**: SVG self-contained, nessuna libreria esterna
  (`EquityChart`, `CompareChart`, `MonteCarloChart`).
- **Export PDF**: `window.print()` + stili `@media print` in `globals.css`
  (`.no-print` nasconde la chrome, `.print-light` forza tema chiaro leggibile).
- **Tooltip glossario**: `InfoTip` con definizioni in una frase (oggetto `GLOSSARY`).

---

## 10. Test

`cd apps/api && pytest -q` → **87 test**:
- `test_metrics.py` — formule Chameleon + metriche base (valori a mano);
- `test_advanced_metrics.py` — Sortino, Calmar, VaR, CVaR, Beta, recovery;
- `test_simulator.py` — pipeline su prezzi sintetici;
- `test_api_auth.py` — login, register, RBAC, utente disattivato;
- `test_api_simulate.py` — simulazione, ownership, DCA, Monte Carlo, export, eventi.

Infrastruttura test: SQLite in-memory + override di `get_db` + mock del repository
prezzi (nessuna rete). Config in `pytest.ini` (`asyncio_mode=auto`).
Typecheck frontend: `docker compose exec web pnpm typecheck`.

---

## 11. Procedure comuni (how-to)

**Aggiungere una metrica**: implementala in `engine/metrics.py` (con docstring +
edge case), aggiungi il test in `test_advanced_metrics.py`, includila in
`SimulationResult` (simulator) e nel `result_dict` del router `simulate`, poi
esponila nel frontend (`types.ts` + pagina results + voce in `GLOSSARY`).

**Aggiungere uno scenario storico**: crea `knowledge-base/scenarios/AAAA-nome.md`,
aggiungi la entry in `routers/scenarios.py` (e `packages/shared/scenarios.ts`),
ri-esegui l'ingestion RAG se usata.

**Aggiungere un evento sul grafico**: una riga in `MARKET_EVENTS`
(`routers/scenarios.py`) — solo date storiche reali.

**Cambiare lo schema DB**: modifica i model, genera la migrazione con Alembic, fai
`upgrade head` (in dev avviene da solo al riavvio dell'API).

**Variabili d'ambiente** (`.env`): `DATABASE_URL`, `REDIS_URL`, `QDRANT_URL`,
`JWT_SECRET`, `ANTHROPIC_API_KEY` (opz.), `FRED_API_KEY` (opz.), `COINGECKO_API_KEY` (opz.).

---

## 12. Trasparenza metodologica (cosa NON facciamo passare per vero)

- **Valuta**: importi mostrati nella valuta del profilo ma rendimenti su asset USD;
  l'effetto cambio EUR/USD **non** è modellato → disclaimer esplicito in UI.
- **DCA**: rendimento della strategia ≠ rendimento sul capitale versato → due numeri distinti.
- **Monte Carlo**: proiezione statistica, non previsione → assunzioni dichiarate.
- **Source tracking**: ogni numero porta la fonte (R2), inclusi cache vs download.
- **Warning, non silenzi**: dati mancanti vengono segnalati, non nascosti.

---

## 13. Roadmap consigliata (prossimi passi)

1. **Block bootstrap** per il Monte Carlo (preserva il clustering dei crash).
2. **Costi e ribilanciamento configurabili** (frequenza + costi di transazione).
3. **Più benchmark** (60/40, All-Weather) e correlation matrix.
4. **Effetto cambio** EUR/USD opzionale (serie FX storica) per importi davvero realistici.
5. **Rate limiting + refresh token + reset password** per l'hardening in produzione.
6. **Celery** per simulazioni molto pesanti (pattern già predisposto in `workers/`).
