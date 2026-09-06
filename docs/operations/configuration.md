# Configuration Reference

The Vexa backend loads configuration via `pydantic-settings` from environment variables prefixed with `VEXA_` or from a local `.env` file. Settings class: [`backend/app/config.py`](file:///Users/shankar/.ao/data/worktrees/vexa/vexa-7/backend/app/config.py).

---

## Complete Settings Catalog

| Variable | Python Type | Default Value | Description |
| :--- | :---: | :---: | :--- |
| **`VEXA_APP_NAME`** | `str` | `"ClosePilot Backend"` | Application display name in OpenAPI documentation. |
| **`VEXA_ENVIRONMENT`** | `str` | `"development"` | Environment runtime mode (`development`, `test`, `production`). |
| **`VEXA_DEBUG`** | `bool` | `False` | Enables verbose FastAPI debug output. |
| **`VEXA_API_PREFIX`** | `str` | `"/api"` | Global URL route prefix. |
| **`VEXA_DB_URL`** | `str` | `"postgresql+asyncpg://localhost:5432/vexa"` | SQLAlchemy async PostgreSQL database URI. |
| **`VEXA_DB_ECHO`** | `bool` | `False` | Prints raw SQL queries to console. |
| **`VEXA_DB_POOL_SIZE`** | `int` | `10` | SQLAlchemy connection pool base size. |
| **`VEXA_DB_MAX_OVERFLOW`**| `int` | `20` | SQLAlchemy connection pool overflow limit. |
| **`VEXA_AUTH_ENABLED`** | `bool` | `False` | Enforces JWT authorization headers. |
| **`VEXA_DEFAULT_TENANT_COMPANY_ID`** | `int \| None` | `None` | Default company ID when auth is disabled. |
| **`VEXA_SEED_DATA_DIR`** | `str` | `"app/data"` | Location of synthetic JSON definitions. |
| **`VEXA_SEED_DETERMINISTIC`**| `bool` | `True` | Guarantees identical IDs and amounts across seeds. |
| **`VEXA_SEED_RANDOM_SEED`**| `int` | `42` | Random seed number for synthetic generator. |
| **`VEXA_LLM_PROVIDER`** | `str` | `"deterministic"` | Reasoning engine: `deterministic`, `openai`, `anthropic`, `gemini`. |
| **`VEXA_LLM_MODEL`** | `str` | `"gpt-4o"` | Model identifier for external calls. |
| **`VEXA_LLM_API_KEY`** | `str \| None`| `None` | External model vendor API key. |
| **`VEXA_LLM_BASE_URL`** | `str \| None`| `None` | Base URL for custom/proxy LLM gateways. |
| **`VEXA_LLM_TIMEOUT_SECONDS`**| `float` | `30.0` | Timeout for external model HTTP requests. |
| **`VEXA_INVESTIGATION_MAX_STEPS`** | `int` | `15` | Circuit breaker step limit per investigation. |
| **`VEXA_INVESTIGATION_MAX_SECONDS`**| `float` | `30.0` | Circuit breaker wall-clock limit per investigation. |
