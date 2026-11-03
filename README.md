# Local SQL Todo & Project Task Manager with MCP

A lightweight, robust project and task management system powered by a **local SQL database (MySQL / SQLite)** and exposed through the **Model Context Protocol (MCP)**. It allows AI assistants (Antigravity, Claude, Cursor) as well as humans (via an interactive CLI) to organize projects, track tasks, manage deadlines, and run analytics.

---

## Database Configuration (`.env`)

Configure your database connection in [`.env`](file:///d:/To_do/.env):

```dotenv
# Database Type: mysql or sqlite
DB_TYPE=mysql

# MySQL Connection Details
DB_HOST=localhost
DB_PORT=3306
DB_NAME=todo_db
DB_USER=root
DB_PASSWORD=your_password_here

# SQLite Database File (fallback or if DB_TYPE=sqlite)
SQLITE_DB_PATH=todos.db
```

The database initialization automatically creates the `todo_db` database and schema (`projects` and `tasks` tables with foreign keys and indexes) if they do not exist yet.

---

## Features

- **Local SQL Database (`todos.db`)**:
  - Full relational schema (`projects` and `tasks`) using SQLite standard library (`sqlite3`).
  - Zero external database installation or setup required.
  - Foreign key constraints with cascading deletes and index-optimized queries.
  - Priority rankings (`urgent`, `high`, `medium`, `low`) and status states (`todo`, `in_progress`, `completed`, `blocked`).
- **Standard MCP Server (`server.py`)**:
  - 10 comprehensive MCP tools for projects, tasks, status updates, metrics, and safe SQL queries.
  - MCP Resources for reading live JSON state (`todo://projects`, `todo://tasks`, `todo://summary`).
  - MCP Prompts for AI workflows like `daily-standup`.
- **Interactive CLI (`cli.py`)**:
  - Colored/symbolized terminal task list, status bars, and filters.
  - Subcommands: `list`, `add`, `done`, `update`, `show`, `delete`, `projects`, `summary`, `sql`.

---

## Quick Start

### 1. Environment & Setup

The project includes an initialized virtual environment:

```powershell
# Activate venv if needed
.\.venv\Scripts\Activate.ps1

# Install requirements (already installed in .venv)
pip install -r requirements.txt
```

### 2. Using the CLI

```powershell
# List all tasks
python cli.py list

# Add a project
python cli.py projects --add "Marketing Launch" --desc "Campaign tasks"

# Add a task to a project
python cli.py add "Draft launch email" --project "Marketing Launch" --priority high --due 2026-11-10 -t "email, promo"

# Mark a task as completed
python cli.py done 1

# View task details
python cli.py show 1

# View project progress bars
python cli.py projects

# View overall summary statistics
python cli.py summary

# Run a safe read-only SQL query
python cli.py sql "SELECT project, title, priority, status FROM tasks WHERE status != 'completed'"
```

---

## MCP Server Configuration

To connect this server to any MCP client (such as Claude Desktop, Cursor, or Antigravity), use the following configuration:

```json
{
  "mcpServers": {
    "todo-manager": {
      "command": "d:\\To_do\\.venv\\Scripts\\python.exe",
      "args": [
        "d:\\To_do\\server.py"
      ],
      "env": {
        "TODO_DB_PATH": "d:\\To_do\\todos.db"
      }
    }
  }
}
```

### Starting the MCP Server Manually

```powershell
.\.venv\Scripts\python.exe server.py
```

---

## MCP Tools Reference

| Tool | Parameters | Description |
|---|---|---|
| `add_project` | `name`, `description` | Create a new project. |
| `list_projects` | *none* | List all projects with task counts and progress percentages. |
| `delete_project` | `name` | Delete a project and cascade delete all its tasks. |
| `add_task` | `title`, `project`, `description`, `priority`, `status`, `due_date`, `tags` | Create a task (auto-creates project if it does not exist). |
| `list_tasks` | `project`, `status`, `priority`, `search`, `limit` | Query and filter tasks with sorting by priority and status. |
| `get_task` | `task_id` | Retrieve full details of a specific task. |
| `update_task` | `task_id`, `status`, `priority`, `title`, `description`, `due_date`, `tags`, `project` | Update task fields (e.g. mark done or change priority). |
| `delete_task` | `task_id` | Delete a task by ID. |
| `get_project_summary` | `project` (optional) | Summary metrics (total tasks, done %, status and priority breakdown). |
| `query_database` | `sql_query` | Run custom read-only `SELECT` queries against SQLite. |

### MCP Resources

- `todo://projects`: JSON representation of all projects and task completion statistics.
- `todo://tasks`: JSON list of all active tasks.
- `todo://summary`: Overall workspace metrics.

### MCP Prompts

- `daily-standup`: Gathers currently active, in-progress, and blocked tasks to generate a daily standup report.

---

## Database Schema

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo', 'in_progress', 'completed', 'blocked')),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'urgent')),
    due_date TEXT DEFAULT NULL,
    tags TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);
```

---

## Running Unit Tests

```powershell
.\.venv\Scripts\python.exe -m unittest tests/test_todo.py
```
