"""
FastAPI Web Application for Todo & Project Task Manager.
Backed by local SQL (MySQL / SQLite) with live API and modern Dashboard UI.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db

# Initialize database
db.init_db()

app = FastAPI(title="Project Task Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Pydantic Request Models
# -----------------------------------------------------------------------------

class TaskCreateRequest(BaseModel):
    title: str
    project: str = "General"
    description: str = ""
    priority: str = "medium"
    status: str = "todo"
    due_date: Optional[str] = None
    tags: str = ""


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    project: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    tags: Optional[str] = None


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""


class SqlQueryRequest(BaseModel):
    query: str


# -----------------------------------------------------------------------------
# REST API Endpoints
# -----------------------------------------------------------------------------

@app.get("/api/db-status")
def get_db_status() -> Dict[str, Any]:
    db_type = db.get_db_type()
    version = "Unknown"
    db_name = "todos.db" if db_type == "sqlite" else os.environ.get("DB_NAME", "todo_db")
    try:
        with db.get_db() as context:
            if context.is_mysql:
                cur = context.execute("SELECT VERSION() as v;")
                res = cur.fetchone()
                version = res["v"] if res else "MySQL 8.0"
            else:
                cur = context.execute("SELECT sqlite_version() as v;")
                res = cur.fetchone()
                version = res["v"] if res else "SQLite 3"
    except Exception as e:
        version = f"Error: {e}"

    return {
        "db_type": db_type.upper(),
        "db_name": db_name,
        "version": version
    }


@app.get("/api/summary")
def get_summary(project: Optional[str] = None) -> Dict[str, Any]:
    return db.get_project_summary(project)


@app.get("/api/projects")
def list_projects() -> List[Dict[str, Any]]:
    return db.list_projects()


@app.post("/api/projects")
def create_project(req: ProjectCreateRequest) -> Dict[str, Any]:
    try:
        return db.create_project(name=req.name, description=req.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/projects/{name}")
def delete_project(name: str) -> Dict[str, Any]:
    try:
        deleted = db.delete_project(name)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "message": f"Project '{name}' deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/tasks")
def list_tasks(
    project: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500)
) -> List[Dict[str, Any]]:
    return db.list_tasks(
        project_name=project,
        status=status,
        priority=priority,
        search=search,
        limit=limit
    )


@app.post("/api/tasks")
def create_task(req: TaskCreateRequest) -> Dict[str, Any]:
    try:
        return db.create_task(
            title=req.title,
            project_name=req.project,
            description=req.description,
            priority=req.priority,
            status=req.status,
            due_date=req.due_date,
            tags=req.tags
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/tasks/{task_id}")
def get_task(task_id: int) -> Dict[str, Any]:
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, req: TaskUpdateRequest) -> Dict[str, Any]:
    try:
        updated = db.update_task(
            task_id=task_id,
            title=req.title,
            description=req.description,
            status=req.status,
            priority=req.priority,
            due_date=req.due_date,
            tags=req.tags,
            project_name=req.project
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Task not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/api/tasks/{task_id}/toggle")
def toggle_task_status(task_id: int) -> Dict[str, Any]:
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    new_status = "todo" if task["status"] == "completed" else "completed"
    updated = db.update_task(task_id=task_id, status=new_status)
    return updated


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int) -> Dict[str, Any]:
    deleted = db.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "message": f"Task #{task_id} deleted"}


@app.post("/api/sql")
def execute_sql(req: SqlQueryRequest) -> Dict[str, Any]:
    try:
        rows = db.execute_safe_query(req.query)
        return {"success": True, "count": len(rows), "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------------------------------------------------------
# Frontend Dashboard HTML
# -----------------------------------------------------------------------------

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TaskFlow | Project Task Manager</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 50: '#eef2ff', 100: '#e0e7ff', 500: '#6366f1', 600: '#4f46e5', 700: '#4338ca' }
          }
        }
      }
    }
  </script>
  <!-- Google Fonts Inter -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .badge-urgent { background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
    .badge-high { background-color: #ffedd5; color: #9a3412; border: 1px solid #fed7aa; }
    .badge-medium { background-color: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe; }
    .badge-low { background-color: #f3f4f6; color: #374151; border: 1px solid #e5e7eb; }

    .status-completed { background-color: #dcfce7; color: #166534; }
    .status-in_progress { background-color: #fef9c3; color: #854d0e; }
    .status-blocked { background-color: #fee2e2; color: #991b1b; }
    .status-todo { background-color: #f3f4f6; color: #4b5563; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col">

  <!-- Header Navigation -->
  <header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white font-bold text-xl shadow-md shadow-indigo-100">
          ✓
        </div>
        <div>
          <h1 class="text-xl font-bold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">TaskFlow</h1>
          <p class="text-xs text-slate-400 font-medium">Project Task & Todo Manager</p>
        </div>
        <div id="db-badge" class="ml-4 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1">
          <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span id="db-label">Loading DB...</span>
        </div>
      </div>

      <div class="flex items-center space-x-3">
        <button onclick="openSqlModal()" class="px-3 py-2 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors flex items-center space-x-1">
          <span>⚡ SQL Console</span>
        </button>
        <button onclick="openProjectModal()" class="px-3 py-2 text-xs font-medium text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition-colors flex items-center space-x-1">
          <span>+ New Project</span>
        </button>
        <button onclick="openTaskModal()" class="px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm shadow-indigo-200 transition-colors flex items-center space-x-1">
          <span class="font-bold text-sm">+</span>
          <span>Add Task</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full grid grid-cols-1 lg:grid-cols-4 gap-8">

    <!-- Sidebar: Projects & Stats -->
    <aside class="lg:col-span-1 space-y-6">

      <!-- Summary KPI Card -->
      <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
        <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">Workspace Progress</h2>
        <div class="space-y-4">
          <div>
            <div class="flex justify-between items-center text-sm font-medium mb-1.5">
              <span class="text-slate-600">Completion</span>
              <span id="stat-percent" class="text-indigo-600 font-bold">0%</span>
            </div>
            <div class="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
              <div id="stat-progress-bar" class="bg-indigo-600 h-2.5 rounded-full transition-all duration-500" style="width: 0%"></div>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 pt-2">
            <div class="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <div class="text-xs text-slate-400 font-medium">Total Tasks</div>
              <div id="stat-total" class="text-xl font-bold text-slate-800">0</div>
            </div>
            <div class="p-3 bg-emerald-50/60 rounded-xl border border-emerald-100/60">
              <div class="text-xs text-emerald-600 font-medium">Completed</div>
              <div id="stat-completed" class="text-xl font-bold text-emerald-700">0</div>
            </div>
            <div class="p-3 bg-amber-50/60 rounded-xl border border-amber-100/60">
              <div class="text-xs text-amber-600 font-medium">In Progress</div>
              <div id="stat-progress" class="text-xl font-bold text-amber-700">0</div>
            </div>
            <div class="p-3 bg-rose-50/60 rounded-xl border border-rose-100/60">
              <div class="text-xs text-rose-600 font-medium">Urgent</div>
              <div id="stat-urgent" class="text-xl font-bold text-rose-700">0</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Projects Navigation List -->
      <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm">
        <div class="flex items-center justify-between mb-3">
          <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Projects</h2>
          <span id="project-count" class="text-xs font-medium text-slate-400">0</span>
        </div>
        <nav id="projects-list" class="space-y-1.5">
          <!-- Dynamically inserted projects -->
        </nav>
      </div>

    </aside>

    <!-- Content: Tasks Area -->
    <section class="lg:col-span-3 space-y-6">

      <!-- Filter & Search Toolbar -->
      <div class="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3 items-center justify-between">
        <!-- Search bar -->
        <div class="relative w-full sm:w-72">
          <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 text-sm">🔍</span>
          <input 
            type="text" 
            id="search-input" 
            placeholder="Search tasks or tags..." 
            oninput="handleSearch()"
            class="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
          >
        </div>

        <!-- Filters -->
        <div class="flex items-center space-x-2 w-full sm:w-auto">
          <select id="filter-status" onchange="loadTasks()" class="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/20">
            <option value="">All Statuses</option>
            <option value="todo">To Do</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="blocked">Blocked</option>
          </select>

          <select id="filter-priority" onchange="loadTasks()" class="text-xs bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500/20">
            <option value="">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      <!-- Current Selected Project Header -->
      <div class="flex items-center justify-between px-1">
        <div>
          <h2 id="current-project-title" class="text-lg font-bold text-slate-800">All Tasks</h2>
          <p id="current-project-desc" class="text-xs text-slate-400">Showing all active and completed tasks across all projects</p>
        </div>
        <span id="filtered-task-count" class="text-xs font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">0 tasks</span>
      </div>

      <!-- Tasks List Container -->
      <div id="tasks-container" class="space-y-3">
        <!-- Rendered Task Cards -->
      </div>

    </section>
  </main>

  <!-- Add / Edit Task Modal -->
  <div id="task-modal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
    <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100">
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <h3 id="task-modal-title" class="font-bold text-slate-800 text-base">New Task</h3>
        <button onclick="closeTaskModal()" class="text-slate-400 hover:text-slate-600 text-lg">✕</button>
      </div>

      <form id="task-form" onsubmit="handleTaskSubmit(event)" class="space-y-4 pt-4">
        <input type="hidden" id="task-form-id">

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Title *</label>
          <input type="text" id="task-title" required placeholder="e.g. Implement user login API" class="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:outline-none">
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Project</label>
            <input type="text" id="task-project" list="project-suggestions" placeholder="General" class="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:outline-none">
            <datalist id="project-suggestions"></datalist>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Priority</label>
            <select id="task-priority" class="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:outline-none">
              <option value="medium">Medium</option>
              <option value="urgent">Urgent</option>
              <option value="high">High</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Status</label>
            <select id="task-status" class="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:outline-none">
              <option value="todo">To Do</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="blocked">Blocked</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-600 mb-1">Due Date</label>
            <input type="date" id="task-due-date" class="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:outline-none">
          </div>
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Tags (comma-separated)</label>
          <input type="text" id="task-tags" placeholder="frontend, auth, bug" class="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:outline-none">
        </div>

        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Description / Notes</label>
          <textarea id="task-desc" rows="3" placeholder="Provide extra context or links..." class="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"></textarea>
        </div>

        <div class="flex justify-end space-x-2 pt-2 border-t border-slate-100">
          <button type="button" onclick="closeTaskModal()" class="px-4 py-2 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl">Cancel</button>
          <button type="submit" class="px-5 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm">Save Task</button>
        </div>
      </form>
    </div>
  </div>

  <!-- New Project Modal -->
  <div id="project-modal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
    <div class="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <h3 class="font-bold text-slate-800 text-base">New Project</h3>
        <button onclick="closeProjectModal()" class="text-slate-400 hover:text-slate-600 text-lg">✕</button>
      </div>

      <form onsubmit="handleProjectSubmit(event)" class="space-y-4 pt-4">
        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Project Name *</label>
          <input type="text" id="project-name-input" required placeholder="e.g. Mobile App" class="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:outline-none">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-600 mb-1">Description</label>
          <textarea id="project-desc-input" rows="2" placeholder="Project goals and scope..." class="w-full text-xs p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"></textarea>
        </div>
        <div class="flex justify-end space-x-2 pt-2 border-t border-slate-100">
          <button type="button" onclick="closeProjectModal()" class="px-4 py-2 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-xl">Cancel</button>
          <button type="submit" class="px-5 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm">Create Project</button>
        </div>
      </form>
    </div>
  </div>

  <!-- SQL Console Modal -->
  <div id="sql-modal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
    <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-100 flex flex-col max-h-[85vh]">
      <div class="flex items-center justify-between pb-3 border-b border-slate-100">
        <div class="flex items-center space-x-2">
          <span class="text-indigo-600 font-bold">⚡</span>
          <h3 class="font-bold text-slate-800 text-base">Live Read-Only SQL Console</h3>
        </div>
        <button onclick="closeSqlModal()" class="text-slate-400 hover:text-slate-600 text-lg">✕</button>
      </div>

      <div class="py-4 space-y-3 flex-1 overflow-y-auto">
        <p class="text-xs text-slate-500">Run safe read-only queries against your connected database (SELECT statements only):</p>
        <textarea id="sql-input" rows="3" class="w-full font-mono text-xs p-3 bg-slate-900 text-emerald-400 rounded-xl focus:outline-none">SELECT p.name AS project, COUNT(t.id) as task_count FROM projects p LEFT JOIN tasks t ON p.id = t.project_id GROUP BY p.id;</textarea>
        <div class="flex justify-between items-center">
          <div class="space-x-1">
            <button onclick="setSqlSample('SELECT * FROM tasks ORDER BY id DESC LIMIT 10;')" class="text-[10px] bg-slate-100 px-2 py-1 rounded text-slate-600 hover:bg-slate-200">Recent Tasks</button>
            <button onclick="setSqlSample('SELECT status, COUNT(*) as count FROM tasks GROUP BY status;')" class="text-[10px] bg-slate-100 px-2 py-1 rounded text-slate-600 hover:bg-slate-200">Status Counts</button>
          </div>
          <button onclick="runSql()" class="px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm">Run Query</button>
        </div>

        <div id="sql-output" class="mt-4 p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs overflow-x-auto min-h-[100px] text-slate-600">
          Result table will appear here...
        </div>
      </div>
    </div>
  </div>

  <!-- JavaScript Client -->
  <script>
    let activeProject = '';
    let searchDebounceTimer = null;
    let allProjects = [];

    async function init() {
      await loadDbStatus();
      await loadProjects();
      await loadSummary();
      await loadTasks();
    }

    async function loadDbStatus() {
      try {
        const res = await fetch('/api/db-status');
        const data = await res.json();
        document.getElementById('db-label').textContent = `${data.db_type} (${data.db_name})`;
      } catch (err) {
        document.getElementById('db-label').textContent = 'DB Offline';
      }
    }

    async function loadSummary() {
      try {
        const url = activeProject ? `/api/summary?project=${encodeURIComponent(activeProject)}` : '/api/summary';
        const res = await fetch(url);
        const data = await res.json();

        document.getElementById('stat-percent').textContent = `${data.completion_percentage}%`;
        document.getElementById('stat-progress-bar').style.width = `${data.completion_percentage}%`;
        document.getElementById('stat-total').textContent = data.total_tasks;
        document.getElementById('stat-completed').textContent = data.completed;
        document.getElementById('stat-progress').textContent = data.in_progress;
        document.getElementById('stat-urgent').textContent = data.urgent;
      } catch (err) {
        console.error('Failed to load summary', err);
      }
    }

    async function loadProjects() {
      try {
        const res = await fetch('/api/projects');
        allProjects = await res.json();
        document.getElementById('project-count').textContent = allProjects.length;

        const nav = document.getElementById('projects-list');
        const suggestions = document.getElementById('project-suggestions');
        suggestions.innerHTML = '';

        let html = `
          <button onclick="selectProject('')" class="w-full text-left px-3 py-2 rounded-xl text-xs font-medium flex items-center justify-between transition-colors ${activeProject === '' ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-50'}">
            <span>All Projects</span>
            <span class="text-[11px] text-slate-400">${allProjects.reduce((sum, p) => sum + p.total_tasks, 0)}</span>
          </button>
        `;

        allProjects.forEach(p => {
          suggestions.innerHTML += `<option value="${p.name}">`;
          const isSelected = activeProject.toLowerCase() === p.name.toLowerCase();
          html += `
            <button onclick="selectProject('${p.name}')" class="w-full text-left px-3 py-2 rounded-xl text-xs font-medium flex items-center justify-between transition-colors ${isSelected ? 'bg-indigo-50 text-indigo-700 font-semibold' : 'text-slate-600 hover:bg-slate-50'}">
              <span class="truncate">${p.name}</span>
              <span class="text-[11px] px-1.5 py-0.5 rounded-full ${p.completion_percentage === 100 ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500'}">${p.completed_tasks}/${p.total_tasks}</span>
            </button>
          `;
        });

        nav.innerHTML = html;
      } catch (err) {
        console.error('Failed to load projects', err);
      }
    }

    function selectProject(name) {
      activeProject = name;
      document.getElementById('current-project-title').textContent = name || 'All Tasks';
      document.getElementById('current-project-desc').textContent = name 
        ? `Filtered by project: ${name}` 
        : 'Showing all active and completed tasks across all projects';
      
      loadProjects();
      loadSummary();
      loadTasks();
    }

    async function loadTasks() {
      const status = document.getElementById('filter-status').value;
      const priority = document.getElementById('filter-priority').value;
      const search = document.getElementById('search-input').value;

      const params = new URLSearchParams();
      if (activeProject) params.append('project', activeProject);
      if (status) params.append('status', status);
      if (priority) params.append('priority', priority);
      if (search) params.append('search', search);

      try {
        const res = await fetch(`/api/tasks?${params.toString()}`);
        const tasks = await res.json();
        renderTasks(tasks);
      } catch (err) {
        console.error('Failed to load tasks', err);
      }
    }

    function renderTasks(tasks) {
      const container = document.getElementById('tasks-container');
      document.getElementById('filtered-task-count').textContent = `${tasks.length} task${tasks.length === 1 ? '' : 's'}`;

      if (!tasks.length) {
        container.innerHTML = `
          <div class="bg-white rounded-2xl p-12 text-center border border-slate-200">
            <div class="w-12 h-12 mx-auto mb-3 bg-slate-100 rounded-full flex items-center justify-center text-slate-400 text-xl">📝</div>
            <h3 class="font-bold text-slate-700 text-sm">No tasks found</h3>
            <p class="text-xs text-slate-400 mt-1">Try relaxing filters or add a new task to get started.</p>
            <button onclick="openTaskModal()" class="mt-4 px-4 py-2 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-sm">
              + Add First Task
            </button>
          </div>
        `;
        return;
      }

      let html = '';
      tasks.forEach(t => {
        const isDone = t.status === 'completed';
        const tagsList = t.tags ? t.tags.split(',').map(s => s.trim()).filter(Boolean) : [];

        html += `
          <div class="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm hover:shadow-md transition-shadow flex items-start justify-between gap-4 group">
            <div class="flex items-start space-x-3.5 flex-1 min-w-0">
              <!-- Checkbox -->
              <input 
                type="checkbox" 
                ${isDone ? 'checked' : ''} 
                onchange="toggleTask(${t.id})" 
                class="mt-1 w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 cursor-pointer accent-indigo-600"
              >

              <div class="space-y-1.5 flex-1 min-w-0">
                <div class="flex items-center space-x-2 flex-wrap gap-y-1">
                  <span class="text-xs font-semibold px-2 py-0.5 rounded-full badge-${t.priority}">${t.priority.toUpperCase()}</span>
                  <span class="text-xs font-medium px-2 py-0.5 rounded-full status-${t.status}">${t.status.replace('_', ' ').toUpperCase()}</span>
                  <span class="text-xs text-slate-400 font-medium">📁 ${t.project}</span>
                  ${t.due_date ? `<span class="text-xs text-slate-500 font-medium">📅 ${t.due_date}</span>` : ''}
                </div>

                <h4 class="text-sm font-semibold ${isDone ? 'line-through text-slate-400' : 'text-slate-800'} break-words">
                  ${escapeHtml(t.title)}
                </h4>

                ${t.description ? `<p class="text-xs text-slate-500 leading-relaxed">${escapeHtml(t.description)}</p>` : ''}

                ${tagsList.length ? `
                  <div class="flex items-center space-x-1.5 pt-1">
                    ${tagsList.map(tag => `<span class="text-[10px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md">#${escapeHtml(tag)}</span>`).join('')}
                  </div>
                ` : ''}
              </div>
            </div>

            <!-- Action buttons -->
            <div class="flex items-center space-x-1 opacity-80 group-hover:opacity-100 transition-opacity">
              <button onclick="editTask(${t.id})" class="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-slate-50 rounded-lg text-xs" title="Edit">✏️</button>
              <button onclick="deleteTaskItem(${t.id})" class="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-slate-50 rounded-lg text-xs" title="Delete">🗑️</button>
            </div>
          </div>
        `;
      });

      container.innerHTML = html;
    }

    async function toggleTask(id) {
      await fetch(`/api/tasks/${id}/toggle`, { method: 'PATCH' });
      await loadSummary();
      await loadProjects();
      await loadTasks();
    }

    async function deleteTaskItem(id) {
      if (!confirm('Are you sure you want to delete this task?')) return;
      await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
      await loadSummary();
      await loadProjects();
      await loadTasks();
    }

    function openTaskModal(task = null) {
      document.getElementById('task-modal-title').textContent = task ? 'Edit Task' : 'New Task';
      document.getElementById('task-form-id').value = task ? task.id : '';
      document.getElementById('task-title').value = task ? task.title : '';
      document.getElementById('task-project').value = task ? task.project : (activeProject || 'General');
      document.getElementById('task-priority').value = task ? task.priority : 'medium';
      document.getElementById('task-status').value = task ? task.status : 'todo';
      document.getElementById('task-due-date').value = task && task.due_date ? task.due_date : '';
      document.getElementById('task-tags').value = task ? task.tags : '';
      document.getElementById('task-desc').value = task ? task.description : '';

      document.getElementById('task-modal').classList.remove('hidden');
    }

    function closeTaskModal() {
      document.getElementById('task-modal').classList.add('hidden');
    }

    async function editTask(id) {
      const res = await fetch(`/api/tasks/${id}`);
      const task = await res.json();
      openTaskModal(task);
    }

    async function handleTaskSubmit(e) {
      e.preventDefault();
      const id = document.getElementById('task-form-id').value;
      const payload = {
        title: document.getElementById('task-title').value,
        project: document.getElementById('task-project').value || 'General',
        priority: document.getElementById('task-priority').value,
        status: document.getElementById('task-status').value,
        due_date: document.getElementById('task-due-date').value || null,
        tags: document.getElementById('task-tags').value,
        description: document.getElementById('task-desc').value
      };

      if (id) {
        await fetch(`/api/tasks/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetch('/api/tasks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }

      closeTaskModal();
      await loadSummary();
      await loadProjects();
      await loadTasks();
    }

    function openProjectModal() {
      document.getElementById('project-name-input').value = '';
      document.getElementById('project-desc-input').value = '';
      document.getElementById('project-modal').classList.remove('hidden');
    }

    function closeProjectModal() {
      document.getElementById('project-modal').classList.add('hidden');
    }

    async function handleProjectSubmit(e) {
      e.preventDefault();
      const name = document.getElementById('project-name-input').value;
      const desc = document.getElementById('project-desc-input').value;
      try {
        const res = await fetch('/api/projects', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, description: desc })
        });
        if (!res.ok) {
          const err = await res.json();
          alert(err.detail || 'Error creating project');
          return;
        }
        closeProjectModal();
        await loadProjects();
        selectProject(name);
      } catch (err) {
        alert(err);
      }
    }

    function openSqlModal() {
      document.getElementById('sql-modal').classList.remove('hidden');
    }

    function closeSqlModal() {
      document.getElementById('sql-modal').classList.add('hidden');
    }

    function setSqlSample(sql) {
      document.getElementById('sql-input').value = sql;
      runSql();
    }

    async function runSql() {
      const query = document.getElementById('sql-input').value;
      const out = document.getElementById('sql-output');
      out.innerHTML = '<span class="text-slate-400">Executing...</span>';
      try {
        const res = await fetch('/api/sql', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query })
        });
        const data = await res.json();
        if (!res.ok) {
          out.innerHTML = `<span class="text-rose-600 font-semibold">Error: ${escapeHtml(data.detail)}</span>`;
          return;
        }

        if (!data.rows || !data.rows.length) {
          out.innerHTML = '<span class="text-slate-500">Query executed successfully. 0 rows returned.</span>';
          return;
        }

        const keys = Object.keys(data.rows[0]);
        let tableHtml = `<div class="font-semibold text-slate-700 mb-2">(${data.count} row${data.count === 1 ? '' : 's'})</div>`;
        tableHtml += '<table class="w-full text-left border-collapse border border-slate-200"><thead><tr class="bg-slate-100">';
        keys.forEach(k => tableHtml += `<th class="border border-slate-200 px-2 py-1 text-slate-700 font-semibold">${escapeHtml(k)}</th>`);
        tableHtml += '</tr></thead><tbody>';
        data.rows.forEach(r => {
          tableHtml += '<tr class="hover:bg-slate-50">';
          keys.forEach(k => tableHtml += `<td class="border border-slate-200 px-2 py-1">${escapeHtml(String(r[k]))}</td>`);
          tableHtml += '</tr>';
        });
        tableHtml += '</tbody></table>';
        out.innerHTML = tableHtml;
      } catch (err) {
        out.innerHTML = `<span class="text-rose-600 font-semibold">Network error: ${escapeHtml(String(err))}</span>`;
      }
    }

    function handleSearch() {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(loadTasks, 250);
    }

    function escapeHtml(str) {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    window.onload = init;
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def serve_index() -> str:
    """Serve the interactive task dashboard."""
    return INDEX_HTML


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)

