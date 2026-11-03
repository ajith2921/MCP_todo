"""
Unit tests for the local SQLite Todo & Task Manager and MCP Server tools.
"""

import os
import tempfile
import unittest

import database as db
import server


class TestTodoDatabase(unittest.TestCase):
    def setUp(self):
        # Create a temporary database file for each test
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_path = self.temp_db.name
        db.init_db(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def test_init_and_default_project(self):
        projects = db.list_projects(self.db_path)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["name"], "General")

    def test_create_and_list_project(self):
        proj = db.create_project("Backend API", "Core REST services", self.db_path)
        self.assertEqual(proj["name"], "Backend API")
        
        # Duplicate project name should raise error
        with self.assertRaises(ValueError):
            db.create_project("Backend API", "Duplicate", self.db_path)

        projects = db.list_projects(self.db_path)
        names = [p["name"] for p in projects]
        self.assertIn("Backend API", names)
        self.assertIn("General", names)

    def test_create_task_with_auto_project(self):
        task = db.create_task(
            title="Design DB Schema",
            project_name="Data Team",
            description="Create tables for tasks and projects",
            priority="high",
            status="todo",
            due_date="2026-11-15",
            tags="db, architecture",
            db_path=self.db_path
        )
        self.assertEqual(task["title"], "Design DB Schema")
        self.assertEqual(task["project"], "Data Team")
        self.assertEqual(task["priority"], "high")
        self.assertEqual(task["status"], "todo")

        # Verify project was auto-created
        projects = db.list_projects(self.db_path)
        self.assertIn("Data Team", [p["name"] for p in projects])

    def test_list_and_filter_tasks(self):
        db.create_task("Task 1", project_name="ProjA", priority="low", status="todo", db_path=self.db_path)
        db.create_task("Task 2", project_name="ProjA", priority="urgent", status="in_progress", db_path=self.db_path)
        db.create_task("Task 3", project_name="ProjB", priority="high", status="completed", db_path=self.db_path)

        # Filter by project
        proj_a_tasks = db.list_tasks(project_name="ProjA", db_path=self.db_path)
        self.assertEqual(len(proj_a_tasks), 2)

        # Filter by status
        completed_tasks = db.list_tasks(status="completed", db_path=self.db_path)
        self.assertEqual(len(completed_tasks), 1)
        self.assertEqual(completed_tasks[0]["title"], "Task 3")

        # Search term
        search_tasks = db.list_tasks(search="Task 2", db_path=self.db_path)
        self.assertEqual(len(search_tasks), 1)
        self.assertEqual(search_tasks[0]["title"], "Task 2")

    def test_update_and_delete_task(self):
        task = db.create_task("Initial Title", project_name="General", db_path=self.db_path)
        task_id = task["id"]

        updated = db.update_task(
            task_id=task_id,
            title="Updated Title",
            status="completed",
            priority="urgent",
            db_path=self.db_path
        )
        self.assertEqual(updated["title"], "Updated Title")
        self.assertEqual(updated["status"], "completed")
        self.assertEqual(updated["priority"], "urgent")

        # Delete task
        deleted = db.delete_task(task_id, self.db_path)
        self.assertTrue(deleted)
        self.assertIsNone(db.get_task(task_id, self.db_path))

    def test_project_summary(self):
        db.create_task("T1", project_name="App", status="completed", priority="high", db_path=self.db_path)
        db.create_task("T2", project_name="App", status="in_progress", priority="urgent", db_path=self.db_path)
        db.create_task("T3", project_name="App", status="todo", priority="medium", db_path=self.db_path)

        summary = db.get_project_summary("App", self.db_path)
        self.assertEqual(summary["total_tasks"], 3)
        self.assertEqual(summary["completed"], 1)
        self.assertEqual(summary["in_progress"], 1)
        self.assertEqual(summary["todo"], 1)
        self.assertEqual(summary["urgent"], 1)
        self.assertEqual(summary["completion_percentage"], 33.3)

    def test_safe_sql_queries(self):
        db.create_task("Sample SQL Task", project_name="General", db_path=self.db_path)
        
        # Valid SELECT query
        results = db.execute_safe_query("SELECT id, title FROM tasks WHERE title = 'Sample SQL Task';", self.db_path)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Sample SQL Task")

        # Disallow DROP/INSERT/UPDATE/DELETE queries
        with self.assertRaises(ValueError):
            db.execute_safe_query("DELETE FROM tasks;", self.db_path)

        with self.assertRaises(ValueError):
            db.execute_safe_query("DROP TABLE tasks;", self.db_path)


class TestMCPServerTools(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.prev_default = db.DEFAULT_DB_PATH
        os.environ["TODO_DB_PATH"] = self.temp_db.name
        db.DEFAULT_DB_PATH = self.temp_db.name
        db.init_db(self.temp_db.name)

    def tearDown(self):
        db.DEFAULT_DB_PATH = self.prev_default
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except PermissionError:
                pass

    def test_mcp_tools(self):
        # 1. Add project
        res_proj = server.add_project("Frontend", "Client app")
        self.assertTrue(res_proj["success"])

        # 2. Add task
        res_task = server.add_task(
            title="Setup React UI",
            project="Frontend",
            priority="high",
            due_date="2026-11-20"
        )
        self.assertTrue(res_task["success"])
        task_id = res_task["task"]["id"]

        # 3. List tasks
        tasks = server.list_tasks(project="Frontend")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Setup React UI")

        # 4. Update task
        res_update = server.update_task(task_id=task_id, status="completed")
        self.assertTrue(res_update["success"])
        self.assertEqual(res_update["task"]["status"], "completed")

        # 5. Project summary
        summary = server.get_project_summary("Frontend")
        self.assertEqual(summary["completed"], 1)

        # 6. Read resources
        res_json = server.resource_summary()
        self.assertIn("completed", res_json)

        # 7. Prompt
        prompt_text = server.prompt_daily_standup("Frontend")
        self.assertIn("daily standup", prompt_text.lower())


if __name__ == "__main__":
    unittest.main()
