"""
Database abstraction layer for Todo and Project Task Management.
Supports MySQL (via PyMySQL) and SQLite, configured via .env file.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Tuple

from dotenv import load_dotenv

# Load environment variables from .env in project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Database Configuration
DEFAULT_DB_FILE = os.path.join(BASE_DIR, "todos.db")
DEFAULT_DB_PATH = DEFAULT_DB_FILE


def get_db_type() -> str:
    """Detect configured database type ('mysql', 'postgres', or 'sqlite')."""
    db_type = os.environ.get("DB_TYPE", "").strip().lower()
    if not db_type:
        # If user provided DB_USER and DB_PASSWORD, default to mysql, else sqlite
        if os.environ.get("DB_USER") and os.environ.get("DB_PASSWORD"):
            return "mysql"
        return "sqlite"
    return db_type


class DBContext:
    """Wrapper that normalizes queries and result sets across SQLite and MySQL."""
    def __init__(self, conn: Any, is_mysql: bool = False):
        self.conn = conn
        self.is_mysql = is_mysql

    def execute(self, query: str, params: Optional[Tuple[Any, ...] | List[Any]] = None) -> Any:
        cursor = self.conn.cursor()
        sql = query
        if self.is_mysql:
            # MySQL uses %s instead of ?
            sql = sql.replace("?", "%s")
        if params is not None:
            cursor.execute(sql, tuple(params))
        else:
            cursor.execute(sql)
        return cursor

    def commit(self) -> None:
        self.conn.commit()


@contextmanager
def get_db(sqlite_path: Optional[str] = None) -> Iterator[DBContext]:
    """Context manager yielding a normalized DBContext."""
    db_type = get_db_type()

    if db_type == "mysql" and sqlite_path is None:
        import pymysql
        import pymysql.cursors

        host = os.environ.get("DB_HOST", "localhost")
        port = int(os.environ.get("DB_PORT", "3306"))
        user = os.environ.get("DB_USER", "root")
        password = os.environ.get("DB_PASSWORD", "")
        db_name = os.environ.get("DB_NAME", "todo_db")

        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=db_name,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
        except pymysql.MySQLError as err:
            # If the database does not exist yet (error 1049: Unknown database), auto-create it
            if err.args[0] == 1049:
                init_mysql_database()
                conn = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=db_name,
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False
                )
            else:
                raise ConnectionError(
                    f"Failed to connect to MySQL ({user}@{host}:{port}/{db_name}). "
                    f"Please verify your credentials in .env.\nDetails: {err}"
                ) from err

        context = DBContext(conn, is_mysql=True)
        try:
            yield context
        finally:
            conn.close()

    else:
        # SQLite
        path = sqlite_path or os.environ.get("SQLITE_DB_PATH") or os.environ.get("TODO_DB_PATH") or DEFAULT_DB_FILE
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        context = DBContext(conn, is_mysql=False)
        try:
            yield context
        finally:
            conn.close()


def init_mysql_database() -> None:
    """Connect to MySQL without database selection and create the database if missing."""
    import pymysql
    host = os.environ.get("DB_HOST", "localhost")
    port = int(os.environ.get("DB_PORT", "3306"))
    user = os.environ.get("DB_USER", "root")
    password = os.environ.get("DB_PASSWORD", "")
    db_name = os.environ.get("DB_NAME", "todo_db")

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset="utf8mb4"
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables, indexes, and default project."""
    db_type = get_db_type() if db_path is None else "sqlite"

    if db_type == "mysql" and db_path is None:
        init_mysql_database()

    with get_db(db_path) as db:
        if db.is_mysql:
            # MySQL table schemas
            db.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    description TEXT,
                    created_at VARCHAR(64) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_id INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    status VARCHAR(32) NOT NULL DEFAULT 'todo',
                    priority VARCHAR(32) NOT NULL DEFAULT 'medium',
                    due_date VARCHAR(64) DEFAULT NULL,
                    tags VARCHAR(255) DEFAULT '',
                    created_at VARCHAR(64) NOT NULL,
                    updated_at VARCHAR(64) NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # Safe index creation in MySQL
            for index_name, col_name in [("idx_tasks_status", "status"), ("idx_tasks_priority", "priority")]:
                cur = db.execute(f"""
                    SELECT COUNT(1) as count FROM information_schema.statistics 
                    WHERE table_schema = DATABASE() AND table_name = 'tasks' AND index_name = '{index_name}';
                """)
                res = cur.fetchone()
                if not res or (isinstance(res, dict) and res.get("count", 0) == 0):
                    try:
                        db.execute(f"CREATE INDEX {index_name} ON tasks({col_name});")
                    except Exception:
                        pass
        else:
            # SQLite table schemas
            db.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );
            """)

            db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
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
            """)

            db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);")
            db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
            db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority);")

        # Create default 'General' project if none exists
        cur = db.execute("SELECT id FROM projects WHERE name = ?;", ("General",))
        if not cur.fetchone():
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?);",
                ("General", "Default project for miscellaneous tasks", now)
            )

        db.commit()


def now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# Project Operations
# -----------------------------------------------------------------------------

def create_project(name: str, description: str = "", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Create a new project."""
    init_db(db_path)
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Project name cannot be empty.")

    now = now_iso()
    with get_db(db_path) as db:
        try:
            cursor = db.execute(
                "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?);",
                (clean_name, description.strip(), now)
            )
            project_id = cursor.lastrowid
            db.commit()
            return {
                "id": project_id,
                "name": clean_name,
                "description": description.strip(),
                "created_at": now
            }
        except Exception as e:
            if "UNIQUE" in str(e).upper() or "DUPLICATE" in str(e).upper():
                raise ValueError(f"Project '{clean_name}' already exists.") from e
            raise


def list_projects(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all projects along with task statistics."""
    init_db(db_path)
    with get_db(db_path) as db:
        cursor = db.execute("""
            SELECT 
                p.id,
                p.name,
                p.description,
                p.created_at,
                COUNT(t.id) as total_tasks,
                SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_tasks,
                SUM(CASE WHEN t.status = 'todo' THEN 1 ELSE 0 END) as todo_tasks,
                SUM(CASE WHEN t.status = 'blocked' THEN 1 ELSE 0 END) as blocked_tasks
            FROM projects p
            LEFT JOIN tasks t ON p.id = t.project_id
            GROUP BY p.id, p.name, p.description, p.created_at
            ORDER BY p.name ASC;
        """)
        rows = cursor.fetchall()
        projects = []
        for row in rows:
            p = dict(row)
            total = int(p["total_tasks"] or 0)
            completed = int(p["completed_tasks"] or 0)
            p["total_tasks"] = total
            p["completed_tasks"] = completed
            p["in_progress_tasks"] = int(p["in_progress_tasks"] or 0)
            p["todo_tasks"] = int(p["todo_tasks"] or 0)
            p["blocked_tasks"] = int(p["blocked_tasks"] or 0)
            p["completion_percentage"] = round((completed / total * 100), 1) if total > 0 else 0.0
            projects.append(p)
        return projects


def get_project_by_name(name: str, db: DBContext) -> Optional[Dict[str, Any]]:
    """Fetch project details by name within an active DBContext."""
    cursor = db.execute("SELECT * FROM projects WHERE LOWER(name) = LOWER(?);", (name.strip(),))
    row = cursor.fetchone()
    return dict(row) if row else None


def delete_project(name: str, db_path: Optional[str] = None) -> bool:
    """Delete a project and its associated tasks."""
    init_db(db_path)
    clean_name = name.strip()
    if clean_name.lower() == "general":
        raise ValueError("Cannot delete the default 'General' project.")

    with get_db(db_path) as db:
        cursor = db.execute("DELETE FROM projects WHERE LOWER(name) = LOWER(?);", (clean_name,))
        deleted = cursor.rowcount > 0
        db.commit()
        return deleted


# -----------------------------------------------------------------------------
# Task Operations
# -----------------------------------------------------------------------------

def create_task(
    title: str,
    project_name: str = "General",
    description: str = "",
    priority: str = "medium",
    status: str = "todo",
    due_date: Optional[str] = None,
    tags: str = "",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new task under a specific project."""
    init_db(db_path)
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("Task title cannot be empty.")

    valid_statuses = ("todo", "in_progress", "completed", "blocked")
    valid_priorities = ("low", "medium", "high", "urgent")

    clean_status = status.lower().strip()
    clean_priority = priority.lower().strip()

    if clean_status not in valid_statuses:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}")
    if clean_priority not in valid_priorities:
        raise ValueError(f"Invalid priority '{priority}'. Must be one of: {', '.join(valid_priorities)}")

    now = now_iso()
    with get_db(db_path) as db:
        proj = get_project_by_name(project_name, db)
        if not proj:
            cursor = db.execute(
                "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?);",
                (project_name.strip(), "Auto-created project", now)
            )
            project_id = cursor.lastrowid
            proj_name = project_name.strip()
        else:
            project_id = proj["id"]
            proj_name = proj["name"]

        cursor = db.execute("""
            INSERT INTO tasks (project_id, title, description, status, priority, due_date, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            project_id,
            clean_title,
            description.strip(),
            clean_status,
            clean_priority,
            due_date.strip() if due_date else None,
            tags.strip(),
            now,
            now
        ))
        task_id = cursor.lastrowid
        db.commit()

        return {
            "id": task_id,
            "project_id": project_id,
            "project": proj_name,
            "title": clean_title,
            "description": description.strip(),
            "status": clean_status,
            "priority": clean_priority,
            "due_date": due_date,
            "tags": tags.strip(),
            "created_at": now,
            "updated_at": now
        }


def list_tasks(
    project_name: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List tasks with optional filters."""
    init_db(db_path)
    with get_db(db_path) as db:
        query = """
            SELECT 
                t.id,
                t.title,
                t.description,
                t.status,
                t.priority,
                t.due_date,
                t.tags,
                t.created_at,
                t.updated_at,
                p.id as project_id,
                p.name as project
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            WHERE 1=1
        """
        params: List[Any] = []

        if project_name:
            query += " AND LOWER(p.name) = LOWER(?)"
            params.append(project_name.strip())

        if status:
            query += " AND LOWER(t.status) = LOWER(?)"
            params.append(status.strip())

        if priority:
            query += " AND LOWER(t.priority) = LOWER(?)"
            params.append(priority.strip())

        if search:
            query += " AND (LOWER(t.title) LIKE ? OR LOWER(t.description) LIKE ? OR LOWER(t.tags) LIKE ?)"
            term = f"%{search.strip().lower()}%"
            params.extend([term, term, term])

        # Priority ordering: urgent > high > medium > low
        query += """
            ORDER BY 
                CASE t.status WHEN 'todo' THEN 1 WHEN 'in_progress' THEN 2 WHEN 'blocked' THEN 3 ELSE 4 END,
                CASE t.priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 END,
                CASE WHEN t.due_date IS NULL THEN 1 ELSE 0 END, t.due_date ASC,
                t.id DESC
            LIMIT ? OFFSET ?;
        """
        params.extend([limit, offset])

        cursor = db.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_task(task_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get full details of a specific task."""
    init_db(db_path)
    with get_db(db_path) as db:
        cursor = db.execute("""
            SELECT 
                t.id,
                t.title,
                t.description,
                t.status,
                t.priority,
                t.due_date,
                t.tags,
                t.created_at,
                t.updated_at,
                p.id as project_id,
                p.name as project
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            WHERE t.id = ?;
        """, (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    tags: Optional[str] = None,
    project_name: Optional[str] = None,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update an existing task."""
    init_db(db_path)
    with get_db(db_path) as db:
        existing = get_task(task_id, db_path)
        if not existing:
            return None

        updates: List[str] = []
        params: List[Any] = []

        if title is not None:
            clean_title = title.strip()
            if not clean_title:
                raise ValueError("Task title cannot be empty.")
            updates.append("title = ?")
            params.append(clean_title)

        if description is not None:
            updates.append("description = ?")
            params.append(description.strip())

        if status is not None:
            valid_statuses = ("todo", "in_progress", "completed", "blocked")
            clean_status = status.lower().strip()
            if clean_status not in valid_statuses:
                raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}")
            updates.append("status = ?")
            params.append(clean_status)

        if priority is not None:
            valid_priorities = ("low", "medium", "high", "urgent")
            clean_priority = priority.lower().strip()
            if clean_priority not in valid_priorities:
                raise ValueError(f"Invalid priority '{priority}'. Must be one of: {', '.join(valid_priorities)}")
            updates.append("priority = ?")
            params.append(clean_priority)

        if due_date is not None:
            updates.append("due_date = ?")
            params.append(due_date.strip() if due_date else None)

        if tags is not None:
            updates.append("tags = ?")
            params.append(tags.strip())

        if project_name is not None:
            proj = get_project_by_name(project_name, db)
            now = now_iso()
            if not proj:
                cursor = db.execute(
                    "INSERT INTO projects (name, description, created_at) VALUES (?, ?, ?);",
                    (project_name.strip(), "Auto-created project", now)
                )
                proj_id = cursor.lastrowid
            else:
                proj_id = proj["id"]
            updates.append("project_id = ?")
            params.append(proj_id)

        if not updates:
            return existing

        updates.append("updated_at = ?")
        params.append(now_iso())
        params.append(task_id)

        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?;"
        db.execute(query, params)
        db.commit()

        return get_task(task_id, db_path)


def delete_task(task_id: int, db_path: Optional[str] = None) -> bool:
    """Delete a task by ID."""
    init_db(db_path)
    with get_db(db_path) as db:
        cursor = db.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
        deleted = cursor.rowcount > 0
        db.commit()
        return deleted


def get_project_summary(project_name: Optional[str] = None, db_path: Optional[str] = None) -> Dict[str, Any]:
    """Get aggregate statistics across all projects or for a specific project."""
    init_db(db_path)
    with get_db(db_path) as db:
        where_clause = ""
        params: List[Any] = []
        if project_name:
            where_clause = "WHERE LOWER(p.name) = LOWER(?)"
            params.append(project_name.strip())

        cursor = db.execute(f"""
            SELECT 
                COUNT(t.id) as total_tasks,
                SUM(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN t.status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN t.status = 'todo' THEN 1 ELSE 0 END) as todo,
                SUM(CASE WHEN t.status = 'blocked' THEN 1 ELSE 0 END) as blocked,
                SUM(CASE WHEN t.priority = 'urgent' THEN 1 ELSE 0 END) as urgent,
                SUM(CASE WHEN t.priority = 'high' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN t.priority = 'medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN t.priority = 'low' THEN 1 ELSE 0 END) as low
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            {where_clause};
        """, params)
        row = cursor.fetchone()
        stats = dict(row) if row else {}

        total = int(stats.get("total_tasks") or 0)
        completed = int(stats.get("completed") or 0)
        stats["total_tasks"] = total
        stats["completed"] = completed
        stats["in_progress"] = int(stats.get("in_progress") or 0)
        stats["todo"] = int(stats.get("todo") or 0)
        stats["blocked"] = int(stats.get("blocked") or 0)
        stats["urgent"] = int(stats.get("urgent") or 0)
        stats["high"] = int(stats.get("high") or 0)
        stats["medium"] = int(stats.get("medium") or 0)
        stats["low"] = int(stats.get("low") or 0)
        stats["completion_percentage"] = round((completed / total * 100), 1) if total > 0 else 0.0

        if not project_name:
            cur = db.execute("SELECT COUNT(*) as count FROM projects;")
            proj_res = cur.fetchone()
            stats["total_projects"] = int(proj_res["count"] if isinstance(proj_res, dict) else proj_res[0])

        return stats


def execute_safe_query(sql_query: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Execute a read-only SQL query for custom data extraction and reporting."""
    init_db(db_path)
    stripped = sql_query.strip().lower()
    if not stripped.startswith("select") and not stripped.startswith("with"):
        raise ValueError("Security restriction: Only SELECT or WITH queries are permitted via query_database.")

    disallowed = ["insert", "update", "delete", "drop", "alter", "create", "truncate", "vacuum", "pragma"]
    tokens = stripped.split()
    for token in disallowed:
        if token in tokens and token != "select":
            raise ValueError(f"Security restriction: Forbidden keyword '{token}' in query.")

    with get_db(db_path) as db:
        cursor = db.execute(sql_query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
