import os
import sys
import json
import time
import requests
from openai import OpenAI

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:8000")

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

SYSTEM_PROMPT = """You are an expert SQL analyst. Given a database schema and a question, write a single SQL query that answers the question.

Rules:
- Return ONLY the SQL query, no explanation, no markdown fences.
- Use standard SQLite syntax.
- Be precise with column names and table names as given in the schema.
- For ranking, use window functions like DENSE_RANK() when asked for dense ranking.
- Always match the requested column order and sort order exactly.
"""


def call_llm(question: str, schema: str) -> str:
    user_prompt = f"{SYSTEM_PROMPT}\n\nSchema:\n{schema}\n\nQuestion: {question}\n\nSQL Query:"
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.01,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            raw = "\n".join(lines).strip()
        return raw
    except Exception as e:
        import traceback
        print(f"LLM Call Failed: {e}", file=sys.stderr)
        traceback.print_exc()
        return "SELECT 1"


def reset_env(task_id: str) -> dict:
    resp = requests.post(f"{ENV_URL}/reset", json={"task_id": task_id}, timeout=30)
    return resp.json()


def step_env(query: str) -> dict:
    resp = requests.post(f"{ENV_URL}/step", json={"action": {"query": query}}, timeout=30)
    return resp.json()


def get_tasks() -> list:
    resp = requests.get(f"{ENV_URL}/tasks", timeout=30)
    return resp.json()["tasks"]


def main():
    tasks = get_tasks()
    total_reward = 0.0
    results = []

    for i, task in enumerate(tasks):
        task_id = task["id"]
        difficulty = task["difficulty"]

        print(f"[START] task={task_id} env=sql_query_env model={MODEL_NAME}")

        obs = reset_env(task_id)
        question = obs.get("question", obs.get("observation", {}).get("question", ""))
        schema = obs.get("schema_description", obs.get("observation", {}).get("schema_description", ""))

        t0 = time.time()
        sql_query = call_llm(question, schema)
        llm_time = time.time() - t0

        result = step_env(sql_query)
        
        # Handle OpenEnv format wrapper
        obs_data = result.get("observation", result)
        
        reward = obs_data.get("reward", 0.0)
        if reward is None:
            reward = 0.0
            
        reward_str = f"{reward:.2f}"
        
        done = obs_data.get("done", True)
        done_str = "true" if done else "false"
        
        error = obs_data.get("error", None)
        error_str = repr(error) if error else "null"
        
        action_str = repr(sql_query)
        
        print(f"[STEP] step=1 action={action_str} reward={reward_str} done={done_str} error={error_str}")
        
        success_str = "true" if reward >= 0.99 else "false"
        print(f"[END] success={success_str} steps=1 score={reward_str} rewards={reward_str}")

        total_reward += reward

        step_info = {
            "task_id": task_id,
            "difficulty": difficulty,
            "question": question,
            "generated_query": sql_query,
            "reward": reward,
            "llm_time_s": round(llm_time, 2),
        }
        results.append(step_info)

    avg_reward = total_reward / len(tasks) if tasks else 0

    summary = {
        "total_reward": total_reward,
        "average_reward": avg_reward,
        "tasks_completed": len(results),
        "results": results,
    }
    with open("outputs/inference_results.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    main()
