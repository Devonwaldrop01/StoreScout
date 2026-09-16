"""Synthetic write fixture, no production application or credentials."""
import time
from fastapi import FastAPI
app = FastAPI()
@app.get("/ready")
def ready():
    return {"fixture": True}
@app.post("/write")
def write():
    print("FIXTURE_WRITE_BEGIN", flush=True)
    time.sleep(3)
    print("FIXTURE_WRITE_COMMIT", flush=True)
    return {"completed": True}
