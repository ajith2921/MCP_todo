"""
Command-line interface (CLI) to manage Todo and Project Tasks with local SQLite.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional
import database as db


def format_status(status: str) -> str:
    icons = {
        "todo": "[ ] TODO",
        "in_progress": "[~] IN PROGRESS",
        "completed": "[x] COMPLETED",
        "blocked": "[!] BLOCKED"
    }
    return icons.get(status.lower(), status.upper())


def format_priority(priority: str) -> str:
    icons = {
        "urgent": "URGENT",
        "high": "HIGH",
        "medium": "MED",
        "low": "LOW"
    }
    return icons.get(priority.lower(), priority.upper())


def cmd_list(args: argparse.Namespace) -> None:
    tasks = db.list_tasks(
        project_name=args.project,
        status=args.status,
        priority=args.priority,
        search=args.search,
        limit=args.limit
    )

    if not tasks:
        print("\nNo tasks found matching criteria.\n")
        return

    print("\n" + "=" * 90)
    print(f"{'ID':<4} {'STATUS':<15} {'PRIORITY':<8} {'PROJECT':<14} {'TITLE':<32} {'DUE'}")
    print("-" * 90)
    for t in tasks:
        due = t["due_date"] or "-"
        title = t["title"][:30] + ".." if len(t["title"]) > 32 else t["title"]
        proj = t["project"][:12] + ".." if len(t["project"]) > 14 else t["project"]
        print(f"{t['id']:<4} {format_status(t['status']):<15} {format_priority(t['priority']):<8} {proj:<14} {title:<32} {due}")
    print("=" * 90)
    print(f"Total: {len(tasks)} task(s)\n")


def cmd_add(args: argparse.Namespace) -> None:
    task = db.create_task(
        title=args.title,
        project_name=args.project or "General",
        description=args.desc or "",
        priority=args.priority or "medium",
        status=args.status or "todo",
        due_date=args.due,
        tags=args.tags or ""
    )
    print(f"\n[+] Created task #{task['id']} '{task['title']}' under project '{task['project']}'.\n")


def cmd_done(args: argparse.Namespace) -> None:
    task = db.update_task(task_id=args.id, status="completed")
    if task:
        print(f"\n[x] Task #{args.id} marked as COMPLETED.\n")
    else:
        print(f"\n[!] Task #{args.id} not found.\n", file=sys.stderr)


def cmd_update(args: argparse.Namespace) -> None:
    task = db.update_task(
        task_id=args.id,
        title=args.title,
        description=args.desc,
        status=args.status,
        priority=args.priority,
        due_date=args.due,
        tags=args.tags,
        project_name=args.project
    )
    if task:
        print(f"\n[*] Task #{args.id} updated successfully.\n")
    else:
        print(f"\n[!] Task #{args.id} not found.\n", file=sys.stderr)


def cmd_delete(args: argparse.Namespace) -> None:
    deleted = db.delete_task(args.id)
    if deleted:
        print(f"\n[-] Task #{args.id} deleted.\n")
    else:
        print(f"\n[!] Task #{args.id} not found.\n", file=sys.stderr)


def cmd_show(args: argparse.Namespace) -> None:
    task = db.get_task(args.id)
    if not task:
        print(f"\n[!] Task #{args.id} not found.\n", file=sys.stderr)
        return

    print("\n" + "=" * 50)
    print(f"Task #{task['id']}: {task['title']}")
    print("-" * 50)
    print(f"Project:     {task['project']}")
    print(f"Status:      {format_status(task['status'])}")
    print(f"Priority:    {format_priority(task['priority'])}")
    print(f"Due Date:    {task['due_date'] or 'None'}")
    print(f"Tags:        {task['tags'] or 'None'}")
    print(f"Created At:  {task['created_at']}")
    print(f"Updated At:  {task['updated_at']}")
    if task["description"]:
        print("\nDescription:")
        print(f"  {task['description']}")
    print("=" * 50 + "\n")


def cmd_projects(args: argparse.Namespace) -> None:
    if args.add:
        proj = db.create_project(name=args.add, description=args.desc or "")
        print(f"\n[+] Project '{proj['name']}' created.\n")
        return

    if args.delete:
        deleted = db.delete_project(args.delete)
        if deleted:
            print(f"\n[-] Project '{args.delete}' deleted.\n")
        else:
            print(f"\n[!] Project '{args.delete}' not found.\n", file=sys.stderr)
        return

    projects = db.list_projects()
    print("\n" + "=" * 80)
    print(f"{'ID':<4} {'PROJECT':<20} {'TOTAL':<7} {'DONE':<7} {'IN PROGRESS':<13} {'PROGRESS'}")
    print("-" * 80)
    for p in projects:
        bar_len = int(p['completion_percentage'] / 5)
        bar = "#" * bar_len + "-" * (20 - bar_len)
        print(f"{p['id']:<4} {p['name']:<20} {p['total_tasks']:<7} {p['completed_tasks']:<7} {p['in_progress_tasks']:<13} [{bar}] {p['completion_percentage']}%")
    print("=" * 80 + "\n")


def cmd_summary(args: argparse.Namespace) -> None:
    summary = db.get_project_summary(args.project)
    title = f"Project Summary ({args.project})" if args.project else "Global Workspace Summary"
    print("\n" + "=" * 45)
    print(f"{title:^45}")
    print("-" * 45)
    print(f"Total Projects:   {summary.get('total_projects', 1)}")
    print(f"Total Tasks:      {summary['total_tasks']}")
    print(f"  Completed:      {summary['completed']} ({summary['completion_percentage']}%)")
    print(f"  In Progress:    {summary['in_progress']}")
    print(f"  To Do:          {summary['todo']}")
    print(f"  Blocked:        {summary['blocked']}")
    print("-" * 45)
    print("Priority Breakdown:")
    print(f"  Urgent:         {summary['urgent']}")
    print(f"  High:           {summary['high']}")
    print(f"  Medium:         {summary['medium']}")
    print(f"  Low:            {summary['low']}")
    print("=" * 45 + "\n")


def cmd_sql(args: argparse.Namespace) -> None:
    try:
        rows = db.execute_safe_query(args.query)
        if not rows:
            print("\nQuery returned 0 rows.\n")
            return
        keys = list(rows[0].keys())
        print("\n" + " | ".join(keys))
        print("-" * (sum(len(k) for k in keys) + len(keys) * 3))
        for r in rows:
            print(" | ".join(str(r[k]) for k in keys))
        print(f"\n({len(rows)} row(s))\n")
    except Exception as e:
        print(f"\n[!] SQL Error: {e}\n", file=sys.stderr)


def main() -> None:
    db.init_db()
    parser = argparse.ArgumentParser(description="Local SQLite Todo & Task Manager CLI")
    subparsers = parser.add_subparsers(dest="command")

    # list
    p_list = subparsers.add_parser("list", help="List tasks")
    p_list.add_argument("-p", "--project", help="Filter by project")
    p_list.add_argument("-s", "--status", choices=["todo", "in_progress", "completed", "blocked"], help="Filter by status")
    p_list.add_argument("--priority", choices=["low", "medium", "high", "urgent"], help="Filter by priority")
    p_list.add_argument("-q", "--search", help="Search tasks")
    p_list.add_argument("-n", "--limit", type=int, default=50, help="Max tasks to show")
    p_list.set_defaults(func=cmd_list)

    # add
    p_add = subparsers.add_parser("add", help="Add a new task")
    p_add.add_argument("title", help="Task title")
    p_add.add_argument("-p", "--project", default="General", help="Project name (default: General)")
    p_add.add_argument("-d", "--desc", help="Detailed description")
    p_add.add_argument("--priority", choices=["low", "medium", "high", "urgent"], default="medium")
    p_add.add_argument("-s", "--status", choices=["todo", "in_progress", "completed", "blocked"], default="todo")
    p_add.add_argument("--due", help="Due date (YYYY-MM-DD)")
    p_add.add_argument("-t", "--tags", help="Comma-separated tags")
    p_add.set_defaults(func=cmd_add)

    # done
    p_done = subparsers.add_parser("done", help="Mark task as completed")
    p_done.add_argument("id", type=int, help="Task ID")
    p_done.set_defaults(func=cmd_done)

    # update
    p_update = subparsers.add_parser("update", help="Update task properties")
    p_update.add_argument("id", type=int, help="Task ID")
    p_update.add_argument("-t", "--title", help="New title")
    p_update.add_argument("-d", "--desc", help="New description")
    p_update.add_argument("-s", "--status", choices=["todo", "in_progress", "completed", "blocked"])
    p_update.add_argument("--priority", choices=["low", "medium", "high", "urgent"])
    p_update.add_argument("--due", help="New due date (YYYY-MM-DD)")
    p_update.add_argument("--tags", help="New tags")
    p_update.add_argument("-p", "--project", help="Move to project")
    p_update.set_defaults(func=cmd_update)

    # delete
    p_delete = subparsers.add_parser("delete", help="Delete a task")
    p_delete.add_argument("id", type=int, help="Task ID")
    p_delete.set_defaults(func=cmd_delete)

    # show
    p_show = subparsers.add_parser("show", help="Show full task details")
    p_show.add_argument("id", type=int, help="Task ID")
    p_show.set_defaults(func=cmd_show)

    # projects
    p_proj = subparsers.add_parser("projects", help="List or manage projects")
    p_proj.add_argument("--add", help="Add a new project")
    p_proj.add_argument("-d", "--desc", help="Description for new project")
    p_proj.add_argument("--delete", help="Delete project by name")
    p_proj.set_defaults(func=cmd_projects)

    # summary
    p_sum = subparsers.add_parser("summary", help="Show project statistics")
    p_sum.add_argument("-p", "--project", help="Filter summary to specific project")
    p_sum.set_defaults(func=cmd_summary)

    # sql
    p_sql = subparsers.add_parser("sql", help="Run read-only SQL query")
    p_sql.add_argument("query", help="SQL SELECT query")
    p_sql.set_defaults(func=cmd_sql)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        cmd_list(argparse.Namespace(project=None, status=None, priority=None, search=None, limit=50))


if __name__ == "__main__":
    main()

