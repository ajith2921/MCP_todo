"""
Model Context Protocol (MCP) Server for Todo and Project Task Management.
Backed by local SQLite.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer

import database as db

# Initialize the MCP Server
mcp = MCPServer(
    name="todo-manager",
    instructions="A local SQL-backed Todo and Project Task Manager MCP Server. Manage projects, tasks, priorities, statuses, and deadlines."
)


# -----------------------------------------------------------------------------
# MCP Tools - Projects
# -----------------------------------------------------------------------------

@mcp.tool()
def add_project(name: str, description: str = "") -> Dict[str, Any]:
    """Create a new project in the local SQL database.
    
    Args:
        name: Name of the project (unique, e.g. 'Website Redesign', 'Mobile App').
        description: Optional description of the project scope and goals.
    """
    try:
        project = db.create_project(name=name, description=description)
        return {
            "success": True,
            "message": f"Project '{name}' created successfully.",
            "project": project
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def list_projects() -> List[Dict[str, Any]]:
    """List all projects in the database along with task completion statistics."""
    return db.list_projects()


@mcp.tool()
def delete_project(name: str) -> Dict[str, Any]:
    """Delete a project and all associated tasks from the database.
    
    Args:
        name: The name of the project to remove. Note: Cannot delete the 'General' default project.
    """
    try:
        deleted = db.delete_project(name=name)
        if deleted:
            return {"success": True, "message": f"Project '{name}' deleted."}
        return {"success": False, "message": f"Project '{name}' not found."}
    except Exception as e:
        return {"success": False, "error": str(e)}


# -----------------------------------------------------------------------------
# MCP Tools - Tasks
# -----------------------------------------------------------------------------

@mcp.tool()
def add_task(
    title: str,
    project: str = "General",
    description: str = "",
    priority: str = "medium",
    status: str = "todo",
    due_date: Optional[str] = None,
    tags: str = ""
) -> Dict[str, Any]:
    """Add a new task to a project in the local SQL database.
    
    Args:
        title: Short title describing the task.
        project: Project name the task belongs to (defaults to 'General', auto-creates if non-existent).
        description: Detailed notes or instructions for the task.
        priority: Task priority ('low', 'medium', 'high', 'urgent'). Defaults to 'medium'.
        status: Initial status ('todo', 'in_progress', 'completed', 'blocked'). Defaults to 'todo'.
        due_date: Optional due date in ISO format (e.g. '2026-11-10').
        tags: Optional comma-separated tags/labels (e.g. 'frontend, bug, auth').
    """
    try:
        task = db.create_task(
            title=title,
            project_name=project,
            description=description,
            priority=priority,
            status=status,
            due_date=due_date,
            tags=tags
        )
        return {
            "success": True,
            "message": f"Task #{task['id']} '{task['title']}' created under project '{task['project']}'.",
            "task": task
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def list_tasks(
    project: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Query and filter tasks in the database.
    
    Args:
        project: Filter by project name (e.g. 'Mobile App').
        status: Filter by status ('todo', 'in_progress', 'completed', 'blocked').
        priority: Filter by priority ('low', 'medium', 'high', 'urgent').
        search: Substring search across task title, description, or tags.
        limit: Maximum number of tasks to return (default 50).
    """
    return db.list_tasks(
        project_name=project,
        status=status,
        priority=priority,
        search=search,
        limit=limit
    )


@mcp.tool()
def get_task(task_id: int) -> Dict[str, Any]:
    """Get full details of a specific task by its numerical ID.
    
    Args:
        task_id: The ID of the task.
    """
    task = db.get_task(task_id)
    if task:
        return {"found": True, "task": task}
    return {"found": False, "message": f"Task #{task_id} not found."}


@mcp.tool()
def update_task(
    task_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    tags: Optional[str] = None,
    project: Optional[str] = None
) -> Dict[str, Any]:
    """Update properties of an existing task (e.g., mark completed, change priority).
    
    Args:
        task_id: The ID of the task to update.
        status: New status ('todo', 'in_progress', 'completed', 'blocked').
        priority: New priority ('low', 'medium', 'high', 'urgent').
        title: New title for the task.
        description: New detailed description.
        due_date: New due date string (e.g. '2026-11-15') or empty string to clear.
        tags: New comma-separated tags.
        project: Move the task to a different project name.
    """
    try:
        updated = db.update_task(
            task_id=task_id,
            title=title,
            description=description,
            status=status,
            priority=priority,
            due_date=due_date,
            tags=tags,
            project_name=project
        )
        if updated:
            return {
                "success": True,
                "message": f"Task #{task_id} updated.",
                "task": updated
            }
        return {"success": False, "message": f"Task #{task_id} not found."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def delete_task(task_id: int) -> Dict[str, Any]:
    """Permanently delete a task by ID.
    
    Args:
        task_id: ID of the task to delete.
    """
    try:
        deleted = db.delete_task(task_id)
        if deleted:
            return {"success": True, "message": f"Task #{task_id} deleted."}
        return {"success": False, "message": f"Task #{task_id} not found."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
def get_project_summary(project: Optional[str] = None) -> Dict[str, Any]:
    """Get aggregate metrics and status breakdown for all projects or a specified project.
    
    Args:
        project: Optional project name. If omitted, returns global statistics across all projects.
    """
    return db.get_project_summary(project_name=project)


@mcp.tool()
def query_database(sql_query: str) -> Dict[str, Any]:
    """Execute a custom read-only SELECT query against the local SQLite database.
    Useful for analytics, custom aggregations, and reports.
    
    Args:
        sql_query: A SQL SELECT statement (e.g., "SELECT project, COUNT(*) FROM tasks GROUP BY project").
    """
    try:
        results = db.execute_safe_query(sql_query)
        return {
            "success": True,
            "row_count": len(results),
            "rows": results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# -----------------------------------------------------------------------------
# MCP Resources
# -----------------------------------------------------------------------------

@mcp.resource("todo://projects")
def resource_projects() -> str:
    """Live list of all projects and their status counts."""
    projects = db.list_projects()
    return json.dumps(projects, indent=2)


@mcp.resource("todo://tasks")
def resource_tasks() -> str:
    """Live list of all active (non-completed) tasks across all projects."""
    tasks = db.list_tasks(limit=100)
    return json.dumps(tasks, indent=2)


@mcp.resource("todo://summary")
def resource_summary() -> str:
    """Global summary of task distribution and completion rates."""
    summary = db.get_project_summary()
    return json.dumps(summary, indent=2)


# -----------------------------------------------------------------------------
# MCP Prompts
# -----------------------------------------------------------------------------

@mcp.prompt("daily-standup")
def prompt_daily_standup(project: str = "") -> str:
    """Generate a daily standup prompt based on current tasks."""
    summary = db.get_project_summary(project if project else None)
    in_progress = db.list_tasks(project_name=project if project else None, status="in_progress")
    blocked = db.list_tasks(project_name=project if project else None, status="blocked")
    
    return f"""Please prepare a structured daily standup report using the following live data:
Project scope: {project if project else 'All Projects'}
Summary stats: {json.dumps(summary)}

Tasks currently in progress:
{json.dumps(in_progress, indent=2)}

Blocked tasks needing attention:
{json.dumps(blocked, indent=2)}

Format with:
1. What was worked on / currently in progress
2. Blockers and risks requiring escalation
3. Immediate next priority items for today
"""


# -----------------------------------------------------------------------------
# Custom HTTP Endpoints (Landing Page & Health Check)
# -----------------------------------------------------------------------------

@mcp.custom_route("/health", methods=["GET"])
async def route_health(request: Any) -> Any:
    from starlette.responses import JSONResponse
    return JSONResponse({
        "status": "healthy",
        "service": "todo-manager-mcp",
        "database": db.get_db_type()
    })


@mcp.custom_route("/", methods=["GET"])
async def route_home(request: Any) -> Any:
    from starlette.responses import HTMLResponse

    db_type = db.get_db_type().upper()
    summary = db.get_project_summary()
    total_tasks = summary.get("total_tasks", 0)
    total_projects = summary.get("total_projects", 1)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TaskFlow MCP Server | Live</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>body {{ font-family: 'Inter', sans-serif; }}</style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen flex items-center justify-center p-4">
  <div class="max-w-2xl w-full bg-slate-800 rounded-2xl p-6 sm:p-8 border border-slate-700 shadow-2xl space-y-6">

    <!-- Header -->
    <div class="flex items-center justify-between border-b border-slate-700 pb-4">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-indigo-500/20">
          ✓
        </div>
        <div>
          <h1 class="text-xl font-bold text-white">TaskFlow MCP Server</h1>
          <p class="text-xs text-slate-400">Model Context Protocol Server for Claude & AI Agents</p>
        </div>
      </div>
      <div class="flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-3 py-1 rounded-full text-xs font-semibold">
        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
        <span>ONLINE</span>
      </div>
    </div>

    <!-- Quick Stats -->
    <div class="grid grid-cols-3 gap-3">
      <div class="bg-slate-900/60 p-3.5 rounded-xl border border-slate-700/50">
        <div class="text-[11px] text-slate-400 font-medium">Database Engine</div>
        <div class="text-base font-bold text-indigo-400 mt-0.5">{db_type}</div>
      </div>
      <div class="bg-slate-900/60 p-3.5 rounded-xl border border-slate-700/50">
        <div class="text-[11px] text-slate-400 font-medium">Total Projects</div>
        <div class="text-base font-bold text-white mt-0.5">{total_projects}</div>
      </div>
      <div class="bg-slate-900/60 p-3.5 rounded-xl border border-slate-700/50">
        <div class="text-[11px] text-slate-400 font-medium">Total Tasks</div>
        <div class="text-base font-bold text-white mt-0.5">{total_tasks}</div>
      </div>
    </div>

    <!-- Remote MCP SSE URL Banner -->
    <div class="bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-4 space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold text-indigo-300">MCP SSE Remote Endpoint:</span>
        <span class="text-[10px] text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">Use this URL in Claude</span>
      </div>
      <div class="flex items-center justify-between bg-slate-900/90 rounded-lg p-2.5 font-mono text-xs text-emerald-400 border border-slate-700">
        <span id="sse-url">Loading...</span>
        <button onclick="copyUrl()" class="ml-2 px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs transition">Copy</button>
      </div>
    </div>

    <!-- Claude Desktop Configuration -->
    <div class="space-y-2">
      <h2 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Claude Desktop Configuration</h2>
      <p class="text-xs text-slate-400">Paste this into your <code>claude_desktop_config.json</code>:</p>
      <pre id="claude-config" class="bg-slate-950 p-3.5 rounded-xl border border-slate-700/60 font-mono text-xs text-slate-300 overflow-x-auto leading-relaxed"></pre>
    </div>

    <!-- Available Tools List -->
    <div class="space-y-2 pt-2 border-t border-slate-700/60">
      <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-wider">10 Available MCP Tools</h2>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs text-slate-300 font-mono">
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ add_task</div>
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ list_tasks</div>
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ get_task</div>
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ update_task</div>
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ delete_task</div>
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ add_project</div>
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ list_projects</div>
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ delete_project</div>
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ get_project_summary</div>
        <div class="p-2 bg-slate-900/40 rounded-lg border border-slate-800">⚡ query_database</div>
      </div>
    </div>

  </div>

  <script>
    const currentOrigin = window.location.origin;
    const sseFullUrl = currentOrigin + '/sse';
    document.getElementById('sse-url').textContent = sseFullUrl;

    const configObj = {{
      "mcpServers": {{
        "todo-manager": {{
          "url": sseFullUrl
        }}
      }}
    }};
    document.getElementById('claude-config').textContent = JSON.stringify(configObj, null, 2);

    function copyUrl() {{
      navigator.clipboard.writeText(sseFullUrl);
      alert('Copied to clipboard: ' + sseFullUrl);
    }}
  </script>
</body>
</html>
"""
    return HTMLResponse(html)


# -----------------------------------------------------------------------------
# Main entrypoint
# -----------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Todo & Project Task MCP Server")
    parser.add_argument(
        "--transport", "-t",
        choices=["stdio", "sse"],
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport protocol (stdio for local, sse for remote cloud)"
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host to bind to for SSE (default 0.0.0.0)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=int(os.environ.get("PORT", "8000")),
        help="Port for SSE server (default 8000 or $PORT)"
    )
    args = parser.parse_args()

    db.init_db()

    if args.transport == "sse":
        print(f"Starting MCP Server on SSE transport at http://{args.host}:{args.port}/sse ...")
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

