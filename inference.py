import os
import sys
import json
import time
import requests
from openai import OpenAI

GLOBAL_START = time.time()

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:8000")

client = OpenAI(
    base_url=API_BASE_URL,
    api_key=HF_TOKEN,
    timeout=300.0,
    max_retries=1
)

SYSTEM_PROMPT = """You are an expert SQL analyst. Given a database schema and a question, write a single SQL query that answers the question.

Rules:
- Return ONLY the SQL query, no explanation, no markdown fences.
- Use standard SQLite syntax.
- Be precise with column names and table names as given in the schema.
- For ranking, use window functions like DENSE_RANK() when asked for dense ranking.
- Always match the requested column order and sort order exactly.
"""


def clamp(score: float) -> float:
    return max(0.01, min(0.99, score))


def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step, action, reward, done, error=None):
    error_str = f'"{error}"' if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_str}", flush=True)


def log_end(success, steps, score, rewards):
    rewards_str = ",".join([f"{r:.2f}" for r in rewards])
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


def call_llm(question: str, schema: str) -> str:
    if time.time() - GLOBAL_START > 280:
        print("Global timeout approached (280s), skipping LLM call.", file=sys.stderr)
        return "SELECT 1"

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

    for task in tasks:
        task_id = task["id"]
        difficulty = task["difficulty"]

        log_start(task_id, "sql_query_env", MODEL_NAME)

        obs = reset_env(task_id)
        question = obs.get("question", obs.get("observation", {}).get("question", ""))
        schema = obs.get("schema_description", obs.get("observation", {}).get("schema_description", ""))

        t0 = time.time()
        sql_query = call_llm(question, schema)
        llm_time = time.time() - t0

        result = step_env(sql_query)

        obs_data = result.get("observation", result)

        reward = obs_data.get("reward", 0.01)
        if reward is None:
            reward = 0.01
        reward = clamp(float(reward))

        done = obs_data.get("done", True)
        error = obs_data.get("error", None)

        log_step(1, repr(sql_query), reward, done, error)

        success = reward >= 0.99
        log_end(success=success, steps=1, score=reward, rewards=[reward])

        total_reward += reward

        results.append({
            "task_id": task_id,
            "difficulty": difficulty,
            "question": question,
            "generated_query": sql_query,
            "reward": reward,
            "llm_time_s": round(llm_time, 2),
        })

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
