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

