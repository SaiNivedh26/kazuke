#!/usr/bin/env python3
import os
import requests
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

DATASET = f"memory_ops_test_{uuid.uuid4().hex[:6]}"
SESSION_ID = f"test_session_{uuid.uuid4().hex[:8]}"

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

def recall(query, dataset=DATASET):
    resp = requests.post(
        f"{BASE_URL}/api/v1/recall",
        json={"query": query, "searchType": "GRAPH_COMPLETION", "datasets": [dataset]},
        headers=headers, timeout=30
    )
    return resp.status_code, resp.json() if resp.ok else resp.text

def forget(dataset=DATASET, data_id=None, everything=False):
    payload = {}
    if everything:
        payload["everything"] = True
    elif data_id:
        payload["dataId"] = data_id
        payload["dataset"] = dataset
    else:
        payload["dataset"] = dataset
    resp = requests.post(
        f"{BASE_URL}/api/v1/forget",
        json=payload,
        headers=headers, timeout=90
    )
    return resp.status_code, resp.json() if resp.ok else resp.text

def get_datasets():
    resp = requests.get(f"{BASE_URL}/api/v1/datasets/", headers=headers, timeout=10)
    return resp.status_code, resp.json() if resp.ok else resp.text

def get_data(dataset=DATASET):
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
    resp = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/data", headers=headers, timeout=30)
    return resp.status_code, resp.json() if resp.ok else resp.text

def main():
    print("=" * 70)
    print("🧠 Testing add_text() → cognify() → recall() → forget()")
    print("=" * 70)
    print(f"\nDataset: {DATASET}")

    print("\n" + "=" * 70)
    print("STEP 1: add_text() - Store facts in dataset")
    print("=" * 70)
    
    facts = [
        "Alice works at Google as a software engineer.",
        "Alice lives in San Francisco and commutes by bike.",
        "Bob is Alice's manager and lives in Palo Alto."
    ]
    
    for i, fact in enumerate(facts, 1):
        code, data = add_text(fact)
        print(f"\n[{i}/{len(facts)}] add_text('{fact[:45]}...')")
        print(f"   Status: {code}")
        if isinstance(data, dict):
            status = data.get('status', 'OK')
            data_id = data.get('data_ingestion_info', [{}])[0].get('data_id', 'N/A') if data.get('data_ingestion_info') else 'N/A'
            print(f"   Result: {status}")
            print(f"   Data ID: {data_id[:12]}..." if data_id != 'N/A' else f"   Data ID: {data_id}")

    print("\n" + "=" * 70)
    print("STEP 2: cognify() - Build knowledge graph")
    print("=" * 70)
    
    code, data = cognify()
    print(f"\ncognify(dataset='{DATASET}')")
    print(f"   Status: {code}")
    if isinstance(data, dict):
        for ds_id, info in data.items():
            print(f"   Dataset: {ds_id[:12]}...")
            print(f"   Status: {info.get('status', 'OK')}")

    print("\n" + "=" * 70)
    print("STEP 3: recall() - Search the knowledge graph")
    print("=" * 70)
    
    queries = [
        "Where does Alice work?",
        "How does Alice commute?",
        "Who is Bob?"
    ]
    
    for i, q in enumerate(queries, 1):
        code, result = recall(q)
        print(f"\n[{i}/{len(queries)}] recall('{q}')")
        print(f"   Status: {code}")
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and 'search_result' in item:
                    for r in item['search_result']:
                        print(f"   💡 {r}")
                else:
                    print(f"   {item}")
        else:
            print(f"   {str(result)[:200]}")

    print("\n" + "=" * 70)
    print("STEP 4: get_data() - List data items in dataset")
    print("=" * 70)
    
    code, data = get_data()
    print(f"\nget_data(dataset='{DATASET}')")
    print(f"   Status: {code}")
    if isinstance(data, list):
        print(f"   Found {len(data)} data items:")
        for item in data[:5]:
            item_id = item.get('id', 'N/A')
            print(f"     • {item_id[:12]}...")
    else:
        print(f"   {str(data)[:200]}")

    print("\n" + "=" * 70)
    print("STEP 5: forget() - Remove all data from dataset")
    print("=" * 70)
    
    code, data = forget(dataset=DATASET)
    print(f"\nforget(dataset='{DATASET}')")
    print(f"   Status: {code}")
    print(f"   Result: {data}")

    print("\n" + "=" * 70)
    print("STEP 6: recall() - Search after forget (should be empty)")
    print("=" * 70)
    
    q = "Where does Alice work?"
    code, result = recall(q)
    print(f"\nrecall('{q}')")
    print(f"   Status: {code}")
    if code == 404:
        print("   ✅ No results (as expected after forget)")
    elif isinstance(result, list):
        if not result or all(not item.get('search_result') for item in result if isinstance(item, dict)):
            print("   ✅ No results (as expected after forget)")
        else:
            for item in result:
                if isinstance(item, dict) and 'search_result' in item:
                    for r in item['search_result']:
                        print(f"   💡 {r}")
    else:
        print(f"   {str(result)[:200]}")

    print("\n" + "=" * 70)
    print("STEP 7: Verify dataset status")
    print("=" * 70)
    
    code, datasets = get_datasets()
    print(f"\nDatasets after forget:")
    if isinstance(datasets, list):
        found = False
        for d in datasets:
            if d['name'] == DATASET:
                print(f"   • {d['name']} (id: {d['id'][:12]}...) - still exists")
                found = True
        if not found:
            print(f"   ✅ Dataset '{DATASET}' removed")
    else:
        print(f"   {str(datasets)[:200]}")

    print("\n" + "=" * 70)
    print("✅ Memory operations test complete!")
    print("=" * 70)
    print("\nSummary:")
    print("  • add_text() - stores text data in dataset")
    print("  • cognify() - builds knowledge graph from data")
    print("  • recall() - searches the knowledge graph")
    print("  • forget() - removes data from dataset")

if __name__ == "__main__":
    main()
