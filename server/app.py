from openenv.core.env_server import create_fastapi_app
from .environment import SQLEnvironment
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import SQLAction, SQLObservation

app = create_fastapi_app(SQLEnvironment, action_cls=SQLAction, observation_cls=SQLObservation)


@app.get("/tasks")
def list_tasks():
    env = SQLEnvironment()
    return {"tasks": env.get_tasks()}

def main():
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
