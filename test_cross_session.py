#!/usr/bin/env python3
import os
import requests
import json
import uuid
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
TENANT_ID = os.getenv("TENANT_ID")
USER_ID = os.getenv("USER_ID")

headers = {
    "Content-Type": "application/json",
    "X-Api-Key": API_KEY,
    "X-Tenant-Id": TENANT_ID,
    "X-User-Id": USER_ID
}

DATASET = "cross_session_test"

def add_text(text, dataset=DATASET):
    resp = requests.post(
        f"{BASE_URL}/api/v1/add_text",
        json={"textData": [text], "datasetName": dataset},
        headers=headers, timeout=30
    )
    return resp.status_code, resp.json() if resp.ok else resp.text

def cognify(dataset=DATASET):
    resp = requests.post(
        f"{BASE_URL}/api/v1/cognify",
        json={"datasets": [dataset]},
        headers=headers, timeout=90
    )
    return resp.status_code, resp.json() if resp.ok else resp.text

def search(query, dataset=DATASET):
    resp = requests.post(
        f"{BASE_URL}/api/v1/search",
        json={"query": query, "searchType": "GRAPH_COMPLETION", "datasets": [dataset]},
        headers=headers, timeout=30
    )
    return resp.status_code, resp.json() if resp.ok else resp.text

def get_datasets():
    resp = requests.get(f"{BASE_URL}/api/v1/datasets/", headers=headers, timeout=10)
    return resp.status_code, resp.json() if resp.ok else resp.text

def get_graph(dataset=DATASET):
    datasets_resp = get_datasets()
    if datasets_resp[0] != 200:
        return datasets_resp
    ds_list = datasets_resp[1]
    ds_id = None
    for d in ds_list:
        if d["name"] == dataset:
            ds_id = d["id"]
            break
    if not ds_id:
        return 404, "Dataset not found"
    resp = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/graph", headers=headers, timeout=30)
    return resp.status_code, resp.json() if resp.ok else resp.text

def get_sessions():
    resp = requests.get(f"{BASE_URL}/api/v1/sessions", headers=headers, timeout=10)
    return resp.status_code, resp.json() if resp.ok else resp.text

def visualize(dataset=DATASET):
    datasets_resp = get_datasets()
    if datasets_resp[0] != 200:
        return datasets_resp
    ds_list = datasets_resp[1]
    ds_id = None
    for d in ds_list:
        if d["name"] == dataset:
            ds_id = d["id"]
            break
    if not ds_id:
        return 404, "Dataset not found"
    resp = requests.get(
        f"{BASE_URL}/api/v1/visualize",
        params={"dataset_ids": ds_id},
        headers=headers, timeout=30
    )
    return resp.status_code, resp.text[:500] if resp.ok else resp.text

def main():
    print("=" * 70)
    print("🧠 Cross-Session Memory Test")
    print("=" * 70)

    print("\n📋 Current datasets:")
    code, data = get_datasets()
    print(f"   Status: {code}")
    if isinstance(data, list):
        for d in data:
            print(f"   • {d['name']} (id: {d['id'][:12]}...)")
    else:
        print(f"   {data}")

    SESSION_A = f"session_{uuid.uuid4().hex[:8]}"
    SESSION_B = f"session_{uuid.uuid4().hex[:8]}"

    print(f"\n{'='*70}")
    print(f"SESSION A: {SESSION_A}")
    print(f"{'='*70}")

    print("\n📝 Session A adds facts:")
    facts_a = [
        "Sai owns a blue Honda Civic parked in the garage.",
        "Sai's favorite coffee is Ethiopian roast from Blue Bottle."
    ]
    for fact in facts_a:
        code, data = add_text(fact)
        print(f"   ✅ Added: '{fact[:50]}...' → status {code}")

    code, data = cognify()
    print(f"   🔄 Cognify → status {code}")

    print("\n🔍 Session A searches:")
    code, result = search("What car does Sai own?")
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and 'search_result' in item:
                for r in item['search_result']:
                    print(f"   💡 {r}")
    else:
        print(f"   {result}")

    print(f"\n{'='*70}")
    print(f"SESSION B: {SESSION_B}")
    print(f"{'='*70}")

    print("\n📝 Session B adds more facts (same dataset):")
    facts_b = [
        "Sai's Honda Civic has a dent on the rear bumper.",
        "Sai drinks Ethiopian roast every morning at 8am."
    ]
    for fact in facts_b:
        code, data = add_text(fact)
        print(f"   ✅ Added: '{fact[:50]}...' → status {code}")

    code, data = cognify()
    print(f"   🔄 Cognify → status {code}")

    print("\n🔍 Session B searches (should see Session A's data too):")
    queries = [
        "What car does Sai own?",
        "What coffee does Sai prefer?",
        "What's the condition of Sai's car?"
    ]
    for q in queries:
        code, result = search(q)
        print(f"\n   Q: '{q}'")
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and 'search_result' in item:
                    for r in item['search_result']:
                        print(f"   💡 {r}")
        else:
            print(f"   {result}")

    print(f"\n{'='*70}")
    print("📊 Graph Structure:")
    print(f"{'='*70}")
    code, graph = get_graph()
    print(f"   Status: {code}")
    if isinstance(graph, dict):
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        print(f"   Nodes: {len(nodes)}")
        print(f"   Edges: {len(edges)}")
        if nodes:
            print(f"\n   Sample nodes:")
            for n in nodes[:10]:
                label = n.get("label", n.get("name", n.get("id", "?")))
                ntype = n.get("type", n.get("node_type", ""))
                print(f"     • {label} [{ntype}]")
    else:
        print(f"   {str(graph)[:500]}")

    print(f"\n{'='*70}")
    print("📋 Sessions list:")
    print(f"{'='*70}")
    code, sessions = get_sessions()
    print(f"   Status: {code}")
    if isinstance(sessions, list):
        for s in sessions[:5]:
            print(f"   • {s}")
    else:
        print(f"   {str(sessions)[:500]}")

    print(f"\n{'='*70}")
    print("✅ Cross-session test complete!")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
