import os
import uuid
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
TENANT_ID = os.getenv("TENANT_ID")
USER_ID = os.getenv("USER_ID")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

cognee_headers = {
    "Content-Type": "application/json",
    "X-Api-Key": API_KEY,
    "X-Tenant-Id": TENANT_ID,
    "X-User-Id": USER_ID
}

active_sessions = {}
ws_connections = set()

class AddTextRequest(BaseModel):
    text: str
    dataset_name: str = "realtime_memory"
    session_id: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    dataset_name: str = "realtime_memory"

class SessionRequest(BaseModel):
    session_id: Optional[str] = None
    dataset_name: str = "realtime_memory"

class ForgetRequest(BaseModel):
    dataset_name: str = "realtime_memory"

def get_headers():
    return {
        "Content-Type": "application/json",
        "X-Api-Key": API_KEY,
        "X-Tenant-Id": TENANT_ID,
        "X-User-Id": USER_ID
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("static/index.html")

@app.get("/api/datasets")
async def list_datasets():
    resp = requests.get(f"{BASE_URL}/api/v1/datasets/", headers=get_headers(), timeout=10)
    return resp.json()

@app.post("/api/add")
async def add_text(req: AddTextRequest):
    add_resp = requests.post(
        f"{BASE_URL}/api/v1/add_text",
        json={"textData": [req.text], "datasetName": req.dataset_name},
        headers=get_headers(),
        timeout=30
    )
    if add_resp.status_code not in [200, 201]:
        return {"error": add_resp.text, "status": add_resp.status_code}

    cognify_resp = requests.post(
        f"{BASE_URL}/api/v1/cognify",
        json={"datasets": [req.dataset_name]},
        headers=get_headers(),
        timeout=90
    )

    datasets = requests.get(f"{BASE_URL}/api/v1/datasets/", headers=get_headers(), timeout=10).json()
    dataset_id = None
    for ds in datasets:
        if ds["name"] == req.dataset_name:
            dataset_id = ds["id"]
            break

    graph_data = {"nodes": [], "edges": []}
    if dataset_id:
        graph_resp = requests.get(
            f"{BASE_URL}/api/v1/datasets/{dataset_id}/graph",
            headers=get_headers(),
            timeout=10
        )
        if graph_resp.status_code == 200:
            graph_data = graph_resp.json()

    for ws in ws_connections:
        try:
            await ws.send_json({"type": "graph_update", "data": graph_data})
        except:
            pass

    return {
        "status": "success",
        "add": add_resp.json(),
        "cognify": cognify_resp.json() if cognify_resp.status_code in [200, 201, 202] else None,
        "graph": graph_data
    }

@app.post("/api/search")
async def search_graph(req: SearchRequest):
    resp = requests.post(
        f"{BASE_URL}/api/v1/search",
        json={
            "query": req.query,
            "searchType": "GRAPH_COMPLETION",
            "datasets": [req.dataset_name]
        },
        headers=get_headers(),
        timeout=30
    )
    return resp.json()

@app.get("/api/graph/{dataset_name}")
async def get_graph(dataset_name: str):
    datasets = requests.get(f"{BASE_URL}/api/v1/datasets/", headers=get_headers(), timeout=10).json()
    dataset_id = None
    for ds in datasets:
        if ds["name"] == dataset_name:
            dataset_id = ds["id"]
            break

    if not dataset_id:
        return {"nodes": [], "edges": []}

    resp = requests.get(
        f"{BASE_URL}/api/v1/datasets/{dataset_id}/graph",
        headers=get_headers(),
        timeout=10
    )
    if resp.status_code == 200:
        return resp.json()
    return {"nodes": [], "edges": []}

@app.post("/api/session/create")
async def create_session(req: SessionRequest):
    session_id = req.session_id or str(uuid.uuid4())
    active_sessions[session_id] = {
        "id": session_id,
        "dataset_name": req.dataset_name,
        "created_at": str(uuid.uuid4())
    }
    return {"session_id": session_id, "status": "created"}

@app.post("/api/session/reset")
async def reset_session(req: SessionRequest):
    forget_resp = requests.post(
        f"{BASE_URL}/api/v1/forget",
        json={"dataset": req.dataset_name},
        headers=get_headers(),
        timeout=30
    )

    for ws in ws_connections:
        try:
            await ws.send_json({"type": "graph_update", "data": {"nodes": [], "edges": []}})
        except:
            pass

    return {
        "status": "reset",
        "forget": forget_resp.json() if forget_resp.status_code == 200 else forget_resp.text
    }

@app.get("/api/sessions")
async def list_sessions():
    return list(active_sessions.values())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_connections.add(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "refresh":
                dataset_name = data.get("dataset_name", "realtime_memory")
                datasets = requests.get(f"{BASE_URL}/api/v1/datasets/", headers=get_headers(), timeout=10).json()
                dataset_id = None
                for ds in datasets:
                    if ds["name"] == dataset_name:
                        dataset_id = ds["id"]
                        break
                if dataset_id:
                    graph_resp = requests.get(
                        f"{BASE_URL}/api/v1/datasets/{dataset_id}/graph",
                        headers=get_headers(),
                        timeout=10
                    )
                    if graph_resp.status_code == 200:
                        await websocket.send_json({"type": "graph_update", "data": graph_resp.json()})
    except WebSocketDisconnect:
        ws_connections.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
