from typing import List, Optional
from openenv.core.env_server import Action, Observation, State


class SQLAction(Action):
    query: str


class SQLObservation(Observation):
    task_id: str = ""
    question: str = ""
    schema_description: str = ""
    query_result: Optional[str] = None
    expected_result: Optional[str] = None
    error: Optional[str] = None
    message: str = ""
    difficulty: str = ""


class SQLState(State):
    current_task_id: str = ""
    difficulty: str = ""
    total_tasks: int = 0
