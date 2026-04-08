---
title: OpenEnv SQL Query
emoji: 📊
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---
# SQL Query Environment

An OpenEnv environment that trains AI agents to write correct SQL queries against a relational database. The agent receives a database schema and a natural language question, then must produce a SQL query that returns the expected result.

## Why This Problem

Text-to-SQL is one of the most practically valuable NLP tasks. It directly maps to real business use cases: analysts querying dashboards, developers building data tools, and non-technical users interacting with databases through natural language. Training agents on this improves a foundational capability with clear, measurable correctness.

## Environment Description

The environment runs an in-memory SQLite database with 4 tables modeling a typical company structure:

| Table | Description |
|---|---|
| `employees` | Staff records with salary, department, hire date, manager hierarchy |
| `departments` | Department metadata with budgets and locations |
| `projects` | Project tracking with status and timelines |
| `project_assignments` | Many-to-many between employees and projects with roles/hours |

### Action Space

The agent submits a single action per step:

```python
class SQLAction(Action):
    query: str  # A SQL query string
```

### Observation Space

After each step, the agent receives:

```python
class SQLObservation(Observation):
    task_id: str              # Unique task identifier
    question: str             # Natural language question
    schema_description: str   # Schema reference
    query_result: str | None  # Actual query output
    expected_result: str | None  # Expected output
    error: str | None         # SQL error if any
    message: str              # Human-readable feedback
    difficulty: str           # easy | medium | hard
    done: bool                # Always True after step
    reward: float             # 0.0 - 1.0
```

## Tasks (9 total)

### Easy (3 tasks)
- Filter and sort active employees by department
- Aggregate budgets by location
- Count projects by status

### Medium (3 tasks)
- Group-by with multiple aggregates (count + average salary per department)
- Find employees on multiple projects (JOIN + GROUP BY + HAVING)
- Compare salary totals against department budgets (cross-table comparison)

### Hard (3 tasks)
- Self-join to find managers and count their reports
- Multi-hop join across 3 tables with conditional aggregation
- Window functions (DENSE_RANK) for intra-department salary ranking

## Reward Function

| Condition | Reward |
|---|---|
| Results match exactly | 1.0 |
| Row-level partial match | `matching_rows / total_rows` |
| Non-empty but wrong result | 0.1 - 0.2 |
| SQL error or empty result | 0.0 |

Partial credit lets the agent learn incrementally — getting the right rows in the wrong order, or missing a column, still produces a positive signal.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the environment server
cd server && uvicorn app:app --host 0.0.0.0 --port 8000

# Run inference (set env vars first)
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your-api-key"
export ENV_URL="http://localhost:8000"
python inference.py
```

## Docker

```bash
docker build -t sql-query-env .
docker run -p 8000:8000 sql-query-env
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/reset` | POST | Reset environment with optional `task_id` |
| `/step` | POST | Submit a SQL query `{"query": "SELECT ..."}` |
| `/state` | GET | Get current episode state |
| `/health` | GET | Health check |
| `/tasks` | GET | List all available tasks |
| `/ws` | WebSocket | Persistent session connection |

## Project Structure

```
sql_query_env/
├── models.py              # Action, Observation, State types
├── client.py              # WebSocket client
├── server/
│   ├── environment.py     # Core environment logic + task definitions
│   ├── app.py             # FastAPI server
│   └── requirements.txt   # Server dependencies
├── inference.py           # Baseline inference script
├── openenv.yaml           # OpenEnv manifest
├── Dockerfile             # Container definition
├── requirements.txt       # Full dependencies
├── pyproject.toml         # Package config
└── README.md
```
