# DataAgent — Design Document

## 1. Overview

**DataAgent** is a web-based intelligent assistant for data exploration. Users interact with an LLM via a chat interface, browse object storage and database schemas, and inspect the exact prompts and responses sent to the LLM for debugging.

| Layer | Technology |
|-------|-----------|
| Frontend | Vite + React + TypeScript + TailwindCSS + Zustand |
| Backend | Python 3.12 + FastAPI + SQLAlchemy (async) + aiosqlite |
| Database | SQLite (users, conversations, messages, debug logs, workflow executions) |
| LLM | OpenAI-compatible API (openai SDK), configured via `conf.yml` |
| Object Storage | Volcengine TOS (tos SDK) |
| Deployment | Docker Compose (frontend + backend) |

## 2. Core Features

### 2.1 User Authentication
- Login page (username / password).
- JWT-based authentication (stateless, python-jose + bcrypt).
- All API endpoints except `POST /api/auth/login` require `Authorization: Bearer <JWT>`.
- Default seed user must be created at startup using the seed script.

### 2.2 Layout (Three-Column, Collapsible)

| Panel | Position | Content |
|-------|----------|---------|
| Left sidebar | `w-64`, collapsible | Conversation history list, create/delete/switch conversations |
| Center | `flex-1` | Chat area with message bubbles, markdown rendering, streaming, debug button |
| Right resource panel | `w-80`, collapsible | Tabs: Object Storage, Data Sources, Workflow |

### 2.3 Chat Features
- **Streaming:** Assistant responses appear character-by-character via SSE (`text/event-stream`).
- **Markdown:** Completed messages rendered with `react-markdown` + `remark-gfm` (GitHub Flavored Markdown).
- **Context injection:** Selected files (from object storage) and table schemas (from datasources) are injected into the LLM prompt automatically.
- **Debug drawer:** Each assistant message has a "Debug" button showing the full LLM request/response (prompts, parameters, token usage, timing).

### 2.4 Workflow System

Three modes, configurable via `workflow.mode` in `conf.yml` (or `WORKFLOW_MODE` env var):

| Mode | Behavior |
|------|----------|
| `none` (default) | Simple chat: LLM responds directly with streaming, no tools |
| `dynamic` | Agent loop: LLM decides which tools to call via function-calling, up to `max_iterations` (default 10) |
| `yaml` | Predefined workflows: keyword-matched YAML definitions with fixed steps executed in order |

Per-request override available via `workflow_mode` field in `ChatRequest`.

#### Tool Registry

Five built-in tools registered at startup:

| Tool | Description |
|------|-------------|
| `execute_sql` | Execute read-only SELECT queries against configured datasources |
| `list_tables` | List all tables from all datasources |
| `get_table_schema` | Get column definitions (name, type) for a table |
| `read_file` | Read file content from object storage by key |
| `list_files` | List files/directories in object storage at a prefix |

#### YAML Workflow Example

```yaml
name: "explore_table"
description: "Explore a database table by first getting its schema, then running a sample query"
trigger_keywords:
  - "explore table"
  - "show table"
  - "what columns"
  - "describe table"
  - "table structure"

steps:
  - name: "get_schema"
    type: "tool_call"
    tool: "get_table_schema"
    params:
      table_ref: "sample_db.users"

  - name: "list_tables"
    type: "tool_call"
    tool: "list_tables"
    params: {}

final_answer: |
  Here is what I found in the data:
  **Available tables**: {{ steps.list_tables.tables }}
  **Schema for the requested table**:
  {{ steps.get_schema.columns }}
```

Steps support `{{ }}` template expressions resolved against a runtime context that accumulates step results (e.g., `{{ steps.get_schema.columns }}`).

## 3. API Endpoints

All endpoints return JSON except `/api/chat/stream` which returns SSE.

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/login` | Login → JWT + user info | No |
| GET | `/api/auth/me` | Current user profile | Yes |
| GET | `/api/conversations` | List user's conversations | Yes |
| POST | `/api/conversations` | Create a new conversation | Yes |
| GET | `/api/conversations/{id}` | Get conversation with messages | Yes |
| DELETE | `/api/conversations/{id}` | Delete a conversation | Yes |
| POST | `/api/chat/stream` | Streaming chat (SSE) | Yes |
| GET | `/api/storage/list` | List files from object storage | Yes |
| GET | `/api/storage/read` | Read a text file from storage | Yes |
| GET | `/api/datasource/tables` | List tables from datasources | Yes |
| GET | `/api/datasource/table/{table}/columns` | Get columns of a table | Yes |
| GET | `/api/debug/{message_id}` | Get debug info for a message | Yes (ownership) |
| GET | `/api/workflow/executions/{id}` | Get workflow execution with steps | Yes |
| GET | `/api/workflow/conversations/{id}/executions` | List executions for a conversation | Yes |

### 3.1 POST /api/chat/stream — Request Body

```json
{
  "message": "User input text",
  "conversation_id": 123,
  "context": {
    "selected_files": ["path/to/file1.txt"],
    "selected_tables": ["sample_db.users"]
  },
  "workflow_mode": "dynamic"
}
```

`workflow_mode` is optional; when omitted, the config default (`workflow.mode`) is used.

### 3.2 SSE Stream Format

Each event is formatted as `data: <json>\n\n`.

| Event Type | Fields | When |
|-----------|--------|------|
| `chunk` | `content` | Streaming text from LLM |
| `end` | `message_id` | Stream complete, message persisted |
| `error` | `error` | Stream-level error occurred |
| `step_start` | `step_id, step_name, step_type` | Workflow step begins |
| `step_chunk` | `step_id, content` | Streaming content within a step |
| `step_end` | `step_id, output` | Step completed successfully |
| `step_error` | `step_id, error` | Step failed |

### 3.3 GET /api/debug/{message_id} — Response

```json
{
  "debug_id": 42,
  "message_id": 456,
  "request": {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 2048,
    "messages": [
      {"role": "system", "content": "You are a helpful assistant..."},
      {"role": "user", "content": "Expanded prompt with context..."}
    ]
  },
  "response": {
    "content": "Full assistant reply",
    "finish_reason": "stop",
    "usage": {"prompt_tokens": 150, "completion_tokens": 80, "total_tokens": 230}
  },
  "timing": {
    "start_time": "2025-01-15T10:30:00Z",
    "end_time": "2025-01-15T10:30:02.150Z",
    "duration_ms": 2150
  }
}
```

## 4. Backend Architecture

### 4.1 Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, lifespan (DB init, seed user, tool registration)
│   ├── config.py               # Pydantic config models (AppConfig, LLMConfig, WorkflowConfig, etc.)
│   ├── auth.py                 # JWT creation/verification, bcrypt password hashing
│   ├── seed.py                 # Creates initial admin user on startup
│   ├── models/
│   │   └── schemas.py          # All Pydantic request/response schemas
│   ├── db/
│   │   ├── models.py           # ORM: User, Conversation, Message, DebugLog, WorkflowExecution, WorkflowStep
│   │   ├── session.py          # AsyncEngine + session factory
│   │   ├── database.py         # CRUD: users, conversations, messages, debug_logs
│   │   └── workflow_db.py      # CRUD: workflow_executions, workflow_steps
│   ├── router/                 # Thin HTTP handlers (router → service → db)
│   │   ├── auth.py             # POST /api/auth/login, GET /api/auth/me
│   │   ├── conversation.py     # CRUD /api/conversations
│   │   ├── chat.py             # POST /api/chat/stream (SSE)
│   │   ├── storage.py          # GET /api/storage/list, /api/storage/read
│   │   ├── datasource.py       # GET /api/datasource/tables, /columns
│   │   ├── debug.py            # GET /api/debug/{message_id}
│   │   └── workflow.py         # GET /api/workflow/executions/{id}, /conversations/{id}/executions
│   └── service/                # Business logic
│       ├── chat.py             # Default chat streaming, mode dispatcher (none|dynamic|yaml)
│       ├── agent.py            # Dynamic agent: LLM tool-calling loop with max_iterations guard
│       ├── engine.py           # YAML workflow engine: keyword matching, template resolution, step execution
│       ├── tools.py            # Tool registry + 5 built-in tool implementations
│       ├── storage.py          # TOS object storage client (list_files, read_file)
│       ├── datasource.py       # SQLite database metadata reader
│       └── debug.py            # Debug log retrieval
├── workflows/                  # YAML workflow definition files
│   └── explore_table.yaml
├── alembic/                    # Database migrations
├── tests/                      # pytest test suite (59 tests)
│   ├── conftest.py
│   ├── test_tools.py           # 17 tests
│   ├── test_engine.py          # 18 tests
│   ├── test_agent.py           # 6 tests
│   └── test_workflow_db.py     # 18 tests
├── conf.yml                    # Configuration file
├── pyproject.toml              # Dependencies (uv)
└── Dockerfile
```

### 4.2 Layer Separation

```
Router (HTTP) → Service (business logic) → DB (data access)
```

- **Routers** handle HTTP concerns (request parsing, response formatting, HTTP exceptions).
- **Services** contain business logic and raise `ValueError`/`PermissionError`; routers convert to `HTTPException`.
- **DB layer** provides async CRUD functions using SQLAlchemy sessions.

### 4.3 Chat Service Dispatcher

`service/chat.py:stream_chat()` determines the effective mode:

```
effective_mode = body.workflow_mode or config.workflow.mode
```

| Mode | Generator | Description |
|------|-----------|-------------|
| `none` | `_generate()` | Direct LLM streaming with context injection |
| `dynamic` | `agent.run_agent_loop()` | LLM tool-calling loop, step-by-step SSE events |
| `yaml` | `engine.run_yaml_workflow()` | Predefined YAML workflow, template resolution |

### 4.4 Dynamic Agent Loop (`service/agent.py`)

```
User message → create WorkflowExecution → loop (max_iterations):
  ├─ Call LLM with tool schemas
  ├─ If tool_calls: for each tool → create WorkflowStep → execute → yield step_start/step_end → feed result back
  └─ If content: stream as final answer → save assistant message + debug log → yield end
```

### 4.5 YAML Workflow Engine (`service/engine.py`)

```
User message → load YAML files → keyword match → run_yaml_workflow():
  ├─ Create WorkflowExecution
  ├─ For each step:
  │   ├─ Resolve {{ templates }} with runtime context
  │   ├─ Execute tool_call or llm_call step
  │   └─ Yield step_start/step_end SSE events
  ├─ Resolve final_answer template
  └─ Stream final content → save assistant message + debug log → yield end
```

### 4.6 Database Schema

| Table | Key Columns |
|-------|------------|
| `users` | `id`, `username`, `password_hash` |
| `conversations` | `id`, `user_id` (FK), `title`, `created_at` |
| `messages` | `id`, `conversation_id` (FK), `role`, `content`, `created_at` |
| `debug_logs` | `id`, `message_id` (FK), request model/temperature/max_tokens, system/user prompts, response content/usage, timing |
| `workflow_executions` | `id`, `conversation_id` (FK), `message_id` (FK), `mode`, `workflow_name`, `status`, `final_answer`, `started_at`, `finished_at` |
| `workflow_steps` | `id`, `execution_id` (FK), `step_index`, `step_type`, `step_name`, `input`, `output`, `status`, `error`, `started_at`, `finished_at` |

Relationships: `Conversation → WorkflowExecution → WorkflowStep` (cascade delete). `Message → DebugLog` (1:1 optional).

### 4.7 Debug Logging Workflow

1. On streaming request arrival, backend records `start_time`.
2. The exact system prompt, user prompt (with injected context), and LLM parameters are captured.
3. After the LLM stream finishes, the full response text, token usage, and `end_time` are stored in `debug_logs` (linked to the assistant `message_id`).
4. `GET /api/debug/{message_id}` returns the complete record (with ownership validation).

### 4.8 Configuration

```yaml
# backend/conf.yml
llm:
  api_base: "https://aimodels.example.com/v1"
  api_key: "sk-xxxx"              # Override: LLM_API_KEY
  model: "openai/MiniMax-M2.5"
  max_tokens: 20480
  temperature: 0.7

auth:
  jwt_secret: "change-in-production"  # Override: JWT_SECRET
  token_expire_hours: 24

object_storage:
  endpoint: ""                    # e.g. "tos-cn-beijing.volces.com" (optional)
  region: ""                      # e.g. "cn-beijing" (optional)
  access_key: ""                  # Override: OS_ACCESS_KEY
  secret_key: ""                  # Override: OS_SECRET_KEY
  bucket: "dataagent"

datasources:
  - name: "sample_db"
    type: "sqlite"
    path: "./data/sample.db"

workflow:
  mode: "none"                    # "none" | "dynamic" | "yaml"; Override: WORKFLOW_MODE
  max_iterations: 10              # Override: WORKFLOW_MAX_ITERATIONS
  yaml_dir: "workflows"
  tools:
    - name: "execute_sql"
      description: "Execute a read-only SQL query..."
      parameters:
        datasource_name: {type: "string", description: "..."}
        query: {type: "string", description: "..."}
      enabled: true
    # ... list_tables, get_table_schema, read_file, list_files
```

Config is loaded via `config.py` using Pydantic models. Environment variables override YAML values (e.g., `LLM_API_KEY`, `JWT_SECRET`, `OS_ACCESS_KEY`, `OS_SECRET_KEY`, `WORKFLOW_MODE`).

## 5. Frontend Architecture

### 5.1 Component Tree

```
Layout
├── Top Bar (hamburger, title, resource toggle)
├── SidebarHistory (left, w-64, collapsible)
├── ChatArea (center, flex-1)
│   ├── Message bubbles (ReactMarkdown + remarkGfm)
│   ├── Debug button → openDebugDrawer(msg.id)
│   └── Input area + context badges
├── ResourcePanel (right, w-80, collapsible)
│   ├── Object Storage tab (file browser)
│   ├── Data Sources tab (table/column tree)
│   └── Workflow tab (WorkflowPanel)
└── DebugDrawer (overlay, conditional)
```

### 5.2 State Management (Zustand)

| Category | State Fields |
|----------|-------------|
| Auth | `token`, `user` |
| Conversations | `conversations`, `currentConversationId`, `messages`, `fetchingConversation` |
| Context | `selectedFiles`, `selectedTables` |
| UI | `leftSidebarOpen`, `resourcePanelOpen`, `debugDrawerOpen`, `debugMessageId` |
| Workflow | `workflowSteps` |
| Streaming | `isStreaming` |

### 5.3 SSE Streaming (Frontend)

Uses `fetch` + `ReadableStream` via `api.streamChat()` — an async generator function:

1. Sends `POST /api/chat/stream` with `ChatRequest` body.
2. Reads the response body via `ReadableStream.getReader()`.
3. Buffers and parses `data: <json>\n\n` lines into `SSEEvent` objects.
4. Yields each parsed event to the caller.

`ChatArea.handleSend()` consumes the generator and dispatches each event:

| SSE Event | Action |
|-----------|--------|
| `chunk` | `appendToLastAssistant(content)` |
| `end` | `setLastAssistantMessageId(message_id)` |
| `error` | `appendToLastAssistant("\n\n[Error: ...]")` |
| `step_start` | `setWorkflowStep({ step_id, step_name, step_type, status: "running" })` |
| `step_end` | `updateWorkflowStep(step_id, { status: "completed", output })` |
| `step_error` | `updateWorkflowStep(step_id, { status: "failed", error })` |

### 5.4 WorkflowPanel Component

Renders a vertical step timeline showing each workflow step's status:

- **Running:** Animated spinner (blue)
- **Completed:** Green checkmark
- **Failed:** Red X-circle

Each completed/failed step is expandable to show its output or error. Steps are color-coded by type (`tool_call` → purple, `llm_call` → blue).

### 5.5 TypeScript Types

```typescript
type SSEEvent =
  | { type: "chunk"; content: string }
  | { type: "end"; message_id: number }
  | { type: "error"; error: string }
  | { type: "step_start"; step_id: number; step_name: string; step_type: string }
  | { type: "step_chunk"; step_id: number; content: string }
  | { type: "step_end"; step_id: number; output: string | null }
  | { type: "step_error"; step_id: number; error: string };

interface WorkflowStep {
  step_id: number;
  step_name: string;
  step_type: string;
  status: "running" | "completed" | "failed";
  output: string | null;
  error: string | null;
}
```

## 6. Deployment

### 6.1 docker-compose.yml

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/conf.yml:/app/conf.yml
      - ./data:/data
    environment:
      - ENV=production
  frontend:
    build: ./frontend
    ports:
      - "9280:9280"
    depends_on:
      - backend
    environment:
      - VITE_API_URL=http://backend:8000
```

### 6.2 Running Locally

```bash
# Backend
cd backend && uv sync && uv run uvicorn app.main:app --port 8000

# Frontend (proxies /api to localhost:8000 via vite.config.ts)
cd frontend && npm install && npm run dev
```

### 6.3 Testing

```bash
cd backend && uv run pytest tests/ -v
```

59 tests across 4 files: `test_tools.py` (17), `test_engine.py` (18), `test_agent.py` (6), `test_workflow_db.py` (18).

## 7. Security

- JWT-based authentication on all endpoints except login.
- Password hashing via `bcrypt`.
- Resource ownership validation on all user-specific endpoints (conversations, debug logs, workflow executions).
- SQL injection prevention: table name validation via regex (`^[a-zA-Z0-9_]+$`), parameterized queries.
- `execute_sql` tool only allows SELECT queries (read-only).