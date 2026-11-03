"""
Quick runner for Todo & Project Task Manager.
Runs interactive mode, CLI commands, or starts the MCP server.
"""

from __future__ import annotations

import os
import sys

# Ensure local directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
import server


def print_banner() -> None:
    db_type = db.get_db_type().upper()
    print("=" * 60)
    print(f"       TODO & PROJECT TASK MANAGER (Backend: {db_type})")
    print("=" * 60)


def interactive_menu() -> None:
    db.init_db()
    while True:
        print_banner()
        print("1. List All Tasks")
        print("2. Add a New Task")
        print("3. Mark Task as Completed")
        print("4. View Projects & Progress")
        print("5. Workspace Summary")
        print("6. Run Read-Only SQL Query")
        print("7. Launch Web Dashboard (http://127.0.0.1:8000)")
        print("8. Start MCP Server (Stdio Mode)")
        print("9. Exit")
        print("-" * 60)
        
        choice = input("Enter choice (1-9): ").strip()

        if choice == "1":
            from cli import cmd_list, argparse
            cmd_list(argparse.Namespace(project=None, status=None, priority=None, search=None, limit=50))
        elif choice == "2":
            title = input("Task Title: ").strip()
            if not title:
                print("Title cannot be empty.\n")
                continue
            project = input("Project (default 'General'): ").strip() or "General"
            priority = input("Priority [low/medium/high/urgent] (default 'medium'): ").strip().lower() or "medium"
            due = input("Due Date (YYYY-MM-DD, optional): ").strip() or None
            tags = input("Tags (comma-separated, optional): ").strip()
            task = db.create_task(title=title, project_name=project, priority=priority, due_date=due, tags=tags)
            print(f"\n[+] Created Task #{task['id']} under '{task['project']}'.\n")
        elif choice == "3":
            task_id_str = input("Enter Task ID to mark completed: ").strip()
            if task_id_str.isdigit():
                task = db.update_task(task_id=int(task_id_str), status="completed")
                if task:
                    print(f"\n[x] Task #{task_id_str} marked as COMPLETED.\n")
                else:
                    print(f"\n[!] Task #{task_id_str} not found.\n")
            else:
                print("Invalid task ID.\n")
        elif choice == "4":
            from cli import cmd_projects, argparse
            cmd_projects(argparse.Namespace(add=None, desc=None, delete=None))
        elif choice == "5":
            from cli import cmd_summary, argparse
            cmd_summary(argparse.Namespace(project=None))
        elif choice == "6":
            query = input("Enter SQL Query: ").strip()
            if query:
                from cli import cmd_sql, argparse
                cmd_sql(argparse.Namespace(query=query))
        elif choice == "7":
            import uvicorn
            import webbrowser
            print("\nStarting Web Dashboard at http://127.0.0.1:8000 ...")
            webbrowser.open("http://127.0.0.1:8000")
            uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
            break
        elif choice == "8":
            print("\nStarting MCP Server on stdio (press Ctrl+C to stop)...")
            server.mcp.run()
            break
        elif choice == "9":
            print("\nGoodbye!\n")
            break
        else:
            print("Invalid choice, please enter 1 to 8.\n")


def main() -> None:
    if len(sys.argv) > 1:
        flag = sys.argv[1].lower()
        if flag in ("--web", "-w", "web"):
            import uvicorn
            import webbrowser
            print("Launching Web Dashboard at http://127.0.0.1:8000 ...")
            webbrowser.open("http://127.0.0.1:8000")
            uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
            return
        elif flag in ("--server", "-s", "server"):
            db.init_db()
            print("Starting MCP Server on stdio...")
            server.mcp.run()
            return
        elif flag in ("--status", "status", "--check", "check"):
            db.init_db()
            print(f"Successfully connected to database backend: {db.get_db_type().upper()}")
            from cli import cmd_list, argparse
            cmd_list(argparse.Namespace(project=None, status=None, priority=None, search=None, limit=50))
            return

    # If run in a non-interactive pipe, start MCP server
    if not sys.stdin.isatty():
        db.init_db()
        server.mcp.run()
    else:
        interactive_menu()


if __name__ == "__main__":
    main()

