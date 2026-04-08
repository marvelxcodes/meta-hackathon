from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from models import SQLAction, SQLObservation, SQLState


class SQLEnv(EnvClient[SQLAction, SQLObservation, SQLState]):
    def _step_payload(self, action: SQLAction) -> dict:
        return {"query": action.query}

    def _parse_result(self, payload: dict) -> StepResult:
        obs_data = payload.get("observation", {})
        return StepResult(
            observation=SQLObservation(
                done=payload.get("done", False),
                reward=payload.get("reward"),
                task_id=obs_data.get("task_id", ""),
                question=obs_data.get("question", ""),
                schema_description=obs_data.get("schema_description", ""),
                query_result=obs_data.get("query_result"),
                expected_result=obs_data.get("expected_result"),
                error=obs_data.get("error"),
                message=obs_data.get("message", ""),
                difficulty=obs_data.get("difficulty", ""),
            ),
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> SQLState:
        return SQLState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            current_task_id=payload.get("current_task_id", ""),
            difficulty=payload.get("difficulty", ""),
            total_tasks=payload.get("total_tasks", 0),
        )
