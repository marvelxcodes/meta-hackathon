import sqlite3
import uuid
import textwrap
from openenv.core.env_server import Environment
from models import SQLAction, SQLObservation, SQLState


SCHEMA_SQL = textwrap.dedent("""\
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        salary REAL NOT NULL,
        hire_date TEXT NOT NULL,
        manager_id INTEGER,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (manager_id) REFERENCES employees(id)
    );

    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        budget REAL NOT NULL,
        location TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        department_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        FOREIGN KEY (department_id) REFERENCES departments(id)
    );

    CREATE TABLE IF NOT EXISTS project_assignments (
        id INTEGER PRIMARY KEY,
        employee_id INTEGER NOT NULL,
        project_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        hours_per_week REAL DEFAULT 40,
        FOREIGN KEY (employee_id) REFERENCES employees(id),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );
""")

SEED_SQL = textwrap.dedent("""\
    INSERT INTO departments (id, name, budget, location) VALUES
        (1, 'Engineering', 500000, 'San Francisco'),
        (2, 'Marketing', 200000, 'New York'),
        (3, 'Sales', 300000, 'Chicago'),
        (4, 'HR', 150000, 'San Francisco'),
        (5, 'Finance', 250000, 'New York');

    INSERT INTO employees (id, name, department, salary, hire_date, manager_id, is_active) VALUES
        (1, 'Alice Chen', 'Engineering', 145000, '2019-03-15', NULL, 1),
        (2, 'Bob Martinez', 'Engineering', 130000, '2020-07-01', 1, 1),
        (3, 'Carol White', 'Marketing', 95000, '2021-01-10', NULL, 1),
        (4, 'David Kim', 'Sales', 85000, '2020-11-20', NULL, 1),
        (5, 'Eve Johnson', 'Engineering', 155000, '2018-06-01', 1, 1),
        (6, 'Frank Brown', 'HR', 78000, '2022-02-14', NULL, 1),
        (7, 'Grace Lee', 'Finance', 110000, '2019-09-30', NULL, 1),
        (8, 'Hank Wilson', 'Sales', 92000, '2021-04-05', 4, 1),
        (9, 'Ivy Davis', 'Engineering', 140000, '2020-01-15', 1, 0),
        (10, 'Jack Taylor', 'Marketing', 88000, '2022-08-01', 3, 1),
        (11, 'Karen Moore', 'Engineering', 125000, '2021-06-15', 1, 1),
        (12, 'Leo Garcia', 'Finance', 105000, '2020-03-20', 7, 1);

    INSERT INTO projects (id, name, department_id, start_date, end_date, status) VALUES
        (1, 'Website Redesign', 2, '2024-01-15', '2024-06-30', 'completed'),
        (2, 'Cloud Migration', 1, '2024-03-01', NULL, 'active'),
        (3, 'Sales Dashboard', 3, '2024-02-01', '2024-08-15', 'completed'),
        (4, 'Mobile App v2', 1, '2024-06-01', NULL, 'active'),
        (5, 'Hiring Pipeline', 4, '2024-04-01', NULL, 'active'),
        (6, 'Q3 Campaign', 2, '2024-07-01', '2024-09-30', 'completed'),
        (7, 'Budget Forecast', 5, '2024-05-01', NULL, 'active');

    INSERT INTO project_assignments (id, employee_id, project_id, role, hours_per_week) VALUES
        (1, 1, 2, 'Tech Lead', 30),
        (2, 2, 2, 'Developer', 40),
        (3, 2, 4, 'Developer', 20),
        (4, 5, 4, 'Tech Lead', 35),
        (5, 11, 2, 'Developer', 40),
        (6, 3, 1, 'Project Manager', 40),
        (7, 10, 6, 'Content Creator', 30),
        (8, 4, 3, 'Sales Lead', 25),
        (9, 8, 3, 'Analyst', 40),
        (10, 6, 5, 'HR Lead', 20),
        (11, 7, 7, 'Finance Lead', 35),
        (12, 12, 7, 'Analyst', 40);
""")


SCHEMA_DESCRIPTION = textwrap.dedent("""\
Tables:
  employees(id INT PK, name TEXT, department TEXT, salary REAL, hire_date TEXT, manager_id INT FK->employees.id, is_active INT)
  departments(id INT PK, name TEXT UNIQUE, budget REAL, location TEXT)
  projects(id INT PK, name TEXT, department_id INT FK->departments.id, start_date TEXT, end_date TEXT, status TEXT)
  project_assignments(id INT PK, employee_id INT FK->employees.id, project_id INT FK->projects.id, role TEXT, hours_per_week REAL)
""")


TASKS = [
    {
        "id": "easy_1",
        "difficulty": "easy",
        "question": "List the names and salaries of all active employees in the Engineering department, ordered by salary descending.",
        "expected_query_pattern": None,
        "validate": lambda rows: (
            len(rows) == 4
            and rows[0][0] == "Eve Johnson"
            and rows[0][1] == 155000
            and rows[-1][0] == "Karen Moore"
        ),
        "expected_result": "[('Eve Johnson', 155000.0), ('Alice Chen', 145000.0), ('Bob Martinez', 130000.0), ('Karen Moore', 125000.0)]",
    },
    {
        "id": "easy_2",
        "difficulty": "easy",
        "question": "Find the total budget across all departments located in 'New York'.",
        "validate": lambda rows: (
            len(rows) == 1
            and abs(rows[0][0] - 450000) < 0.01
        ),
        "expected_result": "[(450000.0,)]",
    },
    {
        "id": "easy_3",
        "difficulty": "easy",
        "question": "How many projects have a status of 'active'?",
        "validate": lambda rows: (
            len(rows) == 1
            and rows[0][0] == 4
        ),
        "expected_result": "[(4,)]",
    },
    {
        "id": "medium_1",
        "difficulty": "medium",
        "question": "For each department, find the number of active employees and the average salary of active employees. Return department name, employee count, and average salary rounded to 2 decimal places. Order by average salary descending.",
        "validate": lambda rows: (
            len(rows) == 5
            and rows[0][0] == "Engineering"
            and rows[0][1] == 4
        ),
        "expected_result": "[('Engineering', 4, 138750.0), ('Finance', 2, 107500.0), ('Marketing', 2, 91500.0), ('Sales', 2, 88500.0), ('HR', 1, 78000.0)]",
    },
    {
        "id": "medium_2",
        "difficulty": "medium",
        "question": "Find all employees who are assigned to more than one project. Return the employee name and the number of projects they're assigned to, ordered by project count descending.",
        "validate": lambda rows: (
            len(rows) == 1
            and rows[0][0] == "Bob Martinez"
            and rows[0][1] == 2
        ),
        "expected_result": "[('Bob Martinez', 2)]",
    },
    {
        "id": "medium_3",
        "difficulty": "medium",
        "question": "List department names where the total salary expenditure of active employees exceeds the department budget. Return department name, total salary, and budget.",
        "validate": lambda rows: (
            len(rows) == 1
            and rows[0][0] == "Engineering"
        ),
        "expected_result": "[('Engineering', 555000.0, 500000.0)]",
    },
    {
        "id": "hard_1",
        "difficulty": "hard",
        "question": "Find the names of employees who manage other employees (i.e., appear as manager_id for at least one other active employee). For each manager, show their name, department, and how many active direct reports they have. Order by number of direct reports descending, then by name.",
        "validate": lambda rows: (
            len(rows) >= 3
            and rows[0][0] == "Alice Chen"
            and rows[0][2] == 3
        ),
        "expected_result": "[('Alice Chen', 'Engineering', 3), ('Carol White', 'Marketing', 1), ('David Kim', 'Sales', 1), ('Grace Lee', 'Finance', 1)]",
    },
    {
        "id": "hard_2",
        "difficulty": "hard",
        "question": "For each active project, calculate the total weekly person-hours committed. Then find which department has the highest total committed hours across all its active projects. Return the department name and total hours.",
        "validate": lambda rows: (
            len(rows) == 1
            and rows[0][0] == "Engineering"
        ),
        "expected_result": "[('Engineering', 165.0)]",
    },
    {
        "id": "hard_3",
        "difficulty": "hard",
        "question": "Rank all active employees by salary within their department. Return employee name, department, salary, and their rank within the department (1 = highest salary). Use dense ranking. Order by department, then rank.",
        "validate": lambda rows: (
            len(rows) == 11
            and rows[0][0] == "Eve Johnson"
            and rows[0][3] == 1
        ),
        "expected_result": "[('Eve Johnson', 'Engineering', 155000.0, 1), ('Alice Chen', 'Engineering', 145000.0, 2), ('Bob Martinez', 'Engineering', 130000.0, 3), ('Karen Moore', 'Engineering', 125000.0, 4), ('Grace Lee', 'Finance', 110000.0, 1), ('Leo Garcia', 'Finance', 105000.0, 2), ('Frank Brown', 'HR', 78000.0, 1), ('Carol White', 'Marketing', 95000.0, 1), ('Jack Taylor', 'Marketing', 88000.0, 2), ('Hank Wilson', 'Sales', 92000.0, 1), ('David Kim', 'Sales', 85000.0, 2)]",
    },
]


def _create_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA_SQL)
    conn.executescript(SEED_SQL)
    return conn


def _execute_query(conn: sqlite3.Connection, query: str) -> tuple:
    try:
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        return rows, None
    except Exception as e:
        return None, str(e)


def _clamp(score: float) -> float:
    return max(0.01, min(0.99, score))


def _grade(task: dict, rows) -> float:
    if rows is None:
        return 0.01
    try:
        if task["validate"](rows):
            return 0.99
    except Exception:
        pass

    expected_str = task["expected_result"]
    actual_str = str(rows)
    if actual_str.strip() == expected_str.strip():
        return 0.99

    if len(rows) == 0:
        return 0.01

    try:
        expected_rows = eval(expected_str)
        if len(rows) == len(expected_rows):
            matching = sum(1 for a, b in zip(rows, expected_rows) if a == b)
            return _clamp(round(matching / len(expected_rows), 2))
        elif len(rows) > 0:
            return 0.2
    except Exception:
        pass
    return 0.1


class SQLEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        self._state = SQLState()
        self._conn = None
        self._current_task = TASKS[0]
        self._task_index = 0

    def reset(self, seed=None, episode_id=None, task_id=None, **kwargs) -> SQLObservation:
        self._conn = _create_db()
        self._task_index = 0

        if task_id:
            matched = [t for t in TASKS if t["id"] == task_id]
            if matched:
                self._current_task = matched[0]
                self._task_index = TASKS.index(matched[0])
            else:
                self._current_task = TASKS[0]
        else:
            self._current_task = TASKS[0]

        self._state = SQLState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            current_task_id=self._current_task["id"],
            difficulty=self._current_task["difficulty"],
            total_tasks=len(TASKS),
        )

        return SQLObservation(
            done=False,
            reward=None,
            task_id=self._current_task["id"],
            question=self._current_task["question"],
            schema_description=SCHEMA_DESCRIPTION,
            message=f"Write a SQL query to answer the question. Difficulty: {self._current_task['difficulty']}",
            difficulty=self._current_task["difficulty"],
        )

    def step(self, action: SQLAction, timeout_s=None, **kwargs) -> SQLObservation:
        self._state.step_count += 1
        task = self._current_task

        query = action.query.strip()
        if not query:
            return SQLObservation(
                done=True,
                reward=0.01,
                task_id=task["id"],
                question=task["question"],
                schema_description=SCHEMA_DESCRIPTION,
                error="Empty query submitted",
                message="No query provided. Score: 0.0",
                difficulty=task["difficulty"],
            )

        rows, error = _execute_query(self._conn, query)

        if error:
            return SQLObservation(
                done=True,
                reward=0.01,
                task_id=task["id"],
                question=task["question"],
                schema_description=SCHEMA_DESCRIPTION,
                error=error,
                query_result=None,
                expected_result=task["expected_result"],
                message=f"SQL error: {error}",
                difficulty=task["difficulty"],
            )

        reward = _grade(task, rows)
        
        reward = _clamp(float(reward))

        return SQLObservation(
            done=True,
            reward=reward,
            task_id=task["id"],
            question=task["question"],
            schema_description=SCHEMA_DESCRIPTION,
            query_result=str(rows),
            expected_result=task["expected_result"],
            message=f"Query executed. Score: {reward}",
            difficulty=task["difficulty"],
        )

    @property
    def state(self) -> SQLState:
        return self._state

    def get_tasks(self) -> list:
        return [{"id": t["id"], "difficulty": t["difficulty"], "question": t["question"]} for t in TASKS]
