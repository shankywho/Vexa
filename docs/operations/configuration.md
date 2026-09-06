# Configuration Reference

The Vexa backend loads configuration via `pydantic-settings` from environment variables prefixed with `VEXA_` or from a local `.env` file. Settings class: [`backend/app/config.py`](../../backend/app/config.py).

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
| **`VEXA_GROQ_API_KEY`** | `str \| None`| `None` | API key for Groq LLM provider (`GROQ_API_KEY` alias). |
| **`VEXA_GROQ_MODEL`** | `str` | `"qwen/qwen3.8-27b"` | Model identifier for Groq (`qwen/qwen3.8-27b`, `openai/gpt-oss-120b`). |
| **`VEXA_GROQ_BASE_URL`** | `str` | `"https://api.groq.com/openai/v1"` | Base URL for Groq API. |
| **`VEXA_MISTRAL_API_KEY`**| `str \| None`| `None` | API key for Mistral AI provider (`MISTRAL_API_KEY` alias). |
| **`VEXA_MISTRAL_MODEL`** | `str` | `"codestral-latest"` | Model identifier for Mistral (`codestral-latest` 22B, `ministral-14b-latest`). |
| **`VEXA_MISTRAL_BASE_URL`**| `str` | `"https://api.mistral.ai/v1"` | Base URL for Mistral API. |
| **`VEXA_GEMINI_API_KEY`** | `str \| None`| `None` | API key for Google Gemini provider (`GEMINI_API_KEY` alias). |
| **`VEXA_GEMINI_MODEL`** | `str` | `"gemini-3.5-flash-lite"` | Model identifier for Gemini (`gemini-3.5-flash-lite`, `gemini-3.6-flash`). |
| **`VEXA_GEMINI_BASE_URL`** | `str` | `"https://generativelanguage.googleapis.com/v1beta/models"` | Base URL for Gemini API. |
| **`VEXA_AGENT_PROVIDER_ROUTING`** | `dict` | *Default Routing Map* | Routing map assigning primary and fallback providers per agent. |
| **`VEXA_LLM_PROVIDER`** | `str` | `"deterministic"` | Legacy fallback engine: `deterministic`, `custom`, `openai`. |
| **`VEXA_LLM_MODEL`** | `str` | `"gpt-4o"` | Model identifier for legacy fallback calls. |
| **`VEXA_LLM_API_KEY`** | `str \| None`| `None` | External model vendor API key for legacy fallback. |
| **`VEXA_LLM_BASE_URL`** | `str \| None`| `None` | Base URL for custom/proxy LLM gateways. |
| **`VEXA_LLM_TIMEOUT_SECONDS`**| `float` | `30.0` | Timeout for external model HTTP requests. |
| **`VEXA_INVESTIGATION_MAX_STEPS`** | `int` | `15` | Circuit breaker step limit per investigation. |
| **`VEXA_INVESTIGATION_MAX_SECONDS`**| `float` | `30.0` | Circuit breaker wall-clock limit per investigation. |

---

## Agent Routing Defaults & Independence Guarantee

By default, ClosePilot enforces segregation of duties between reasoning and verification:
```python
DEFAULT_AGENT_PROVIDER_ROUTING = {
    "investigation_agent": {"primary": "mistral", "fallback": "groq"},
    "verification_agent": {"primary": "groq", "fallback": "gemini"},
    "close_controller": {"primary": "gemini", "fallback": "mistral"},
    "reconciliation_agent": {"primary": "groq", "fallback": "mistral"},
    "financial_analyst": {"primary": "groq", "fallback": "mistral"},
    "action_agent": {"primary": "groq", "fallback": "deterministic"},
}
```

* **Startup Check:** If `investigation_agent` and `verification_agent` share a primary provider in production, `ConfigurationError` is raised.
* **Runtime Guard:** If runtime fallback causes both agents to invoke the same provider, `independence_compromised=True` is recorded with a `-0.1000` calibrated confidence penalty and high-visibility audit alert.
