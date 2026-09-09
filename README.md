# AITU Gaming Hub — Modular Monolith

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-2CA5E0.svg)](https://docs.aiogram.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%20Async-D71F00.svg)](https://docs.sqlalchemy.org/)
[![Redis](https://img.shields.io/badge/Redis-aioredis-DC382D.svg)](https://redis.io/)

High-performance, modular Telegram platform for the **Astana IT University Esports Club**. Runs as an asynchronous **Modular Monolith** inside a single Python process.

---

## 🏛️ Architectural Foundations

### 1. Application Core & Plugin Architecture
- **Application Core (`core/`)**: Lightweight runtime owning the Telegram Bot, Dispatcher, Lifespan context, and Ingress routing. Avoids premature DI containers.
- **Narrow Plugin Manager (`core/plugin_manager.py`)**: Responsible strictly for 3 things: registering plugins, executing `await plugin.setup(core)` on startup, and `await plugin.teardown()` on shutdown.
- **Strict Isolation**: Plugins communicate **exclusively** through an In-Memory Domain Event Bus. Cross-plugin module imports are prohibited.

### 2. Strictly Domain Events (`core/event_bus.py`)
- The event bus is reserved exclusively for past-tense business events between domains (e.g. `UserVerifiedEvent`, `TicketCreatedEvent`, `TicketRepliedEvent`).
- UI lifecycle events (`ButtonClicked`, `ScreenRendered`) remain localized in handlers.
- Circuit breaker boundaries: an unhandled exception in one event subscriber is logged and isolated, never crashing the event loop or stopping other subscribers.

### 3. Anchor Wizard UI Engine (`core/navigation/`)
- **Single-Message Navigation**: The user interacts with the bot inside a single persistent visual message. Chat history spam is eliminated.
- **Redis Session & History**:
  - `anchor:user:{user_id}:message_id`: ID of the visual anchor.
  - `anchor:user:{user_id}:stack`: Redis-backed LIFO stack for deterministic "Back" navigation.
  - `lock:user:{user_id}`: Distributed lock (`timeout=2.0s`) on incoming callbacks to prevent race conditions and duplicate clicks.
- **Declarative Screen DTO**:
  ```python
  @dataclass(frozen=True)
  class Screen:
      text: str
      reply_markup: InlineKeyboardMarkup | None = None
      parse_mode: str = "HTML"
  ```
- **Silent Recovery**: Silently ignores Telegram's `"message is not modified"` errors and automatically recreates deleted anchor messages without breaking the user session.

### 4. Garbage Collector Middleware (`core/middlewares/garbage_collector.py`)
- When a student enters text (e.g. Student ID, Barcode, Minecraft nickname, or support question):
  1. Global middleware intercepts and executes `bot.delete_message(chat.id, message.message_id)`.
  2. The text is passed to the active FSM state handler.
  3. The persistent anchor message updates in-place.

### 5. Deadline Time Budgeting for External Protocols (`plugins/minecraft/rcon_client.py`)
- Minecraft RCON socket operations enforce a strict total deadline (e.g. `3.0s`).
- Retry attempts are strictly bound by the remaining time budget:
  ```python
  deadline = monotonic() + total_timeout
  for attempt in range(attempts):
      remaining = deadline - monotonic()
      if remaining <= 0:
          break
      # Each attempt is strictly limited to remaining budget
      return await asyncio.wait_for(send_rcon_command(..., remaining), timeout=remaining)
  ```
- If the Minecraft server is offline or lagging, the bot fails fast with a user-friendly error screen instead of stalling the event loop.

### 6. Kubernetes-Ready Probes
- **`/healthz` (Liveness)**: Fast 200 OK check confirming the Python asyncio loop is responsive.
- **`/ready` (Readiness)**: Probes PostgreSQL (`SELECT 1`) and Redis (`PING`). Returns 200 OK or 503 Service Unavailable if dependencies are down.

---

## 📁 Project Structure

```
aitu-gaming-hub/
├── alembic/                # Async database migrations
├── common/                 # Shared domain models, DTOs, and configuration
│   ├── config.py           # Pydantic BaseSettings
│   ├── enums.py            # UserRole, TicketStatus
│   ├── dtos/               # Screen DTO & Domain Events
│   ├── database/           # Async SQLAlchemy engine & sessionmaker
│   └── models/             # User, MinecraftWhitelist, HelpdeskTicket
├── core/                   # Application Core Runtime
│   ├── context.py          # CoreContext injected into plugins
│   ├── protocols.py        # PluginProtocol, EventBusProtocol, NavigatorProtocol
│   ├── event_bus.py        # In-memory typed domain event bus
│   ├── plugin_manager.py   # Narrow plugin lifecycle manager
│   ├── navigation/         # Anchor Wizard UI engine & Redis LIFO stack
│   ├── middlewares/        # Garbage Collector, User Lock, DB Session
│   └── lifespan.py         # FastAPI lifespan, /healthz, /ready, and webhook
├── plugins/                # Isolated Domain Modules
│   ├── auth/               # Student ID & Barcode verification wizard
│   ├── minecraft/          # Time-budgeted RCON client, server status, whitelist
│   └── helpdesk/           # Support ticketing & admin channel reply bridge
├── tests/                  # Pytest test suite (100% passing)
├── main.py                 # Application entry point
├── pyproject.toml          # Project configuration & pytest settings
└── requirements.txt        # Production dependencies
```

---

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Clone and enter directory
cd aitu-gaming-hub

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

### 3. Database Migrations
```bash
alembic upgrade head
```

### 4. Running the Platform
```bash
# Start FastAPI and Aiogram in a single process
python main.py
```

### 5. Running Tests
```bash
pytest -v
```
