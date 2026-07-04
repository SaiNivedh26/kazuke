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

DATASET = f"update_test_{uuid.uuid4().hex[:6]}"

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

def forget(dataset=DATASET, data_id=None, memory_only=False):
    payload = {}
    if data_id:
        payload["dataset"] = dataset
        payload["dataId"] = data_id
    elif memory_only:
        payload["dataset"] = dataset
        payload["memoryOnly"] = True
    else:
        payload["dataset"] = dataset
    resp = requests.post(
        f"{BASE_URL}/api/v1/forget",
        json=payload,
        headers=headers, timeout=90
    )
    return resp.status_code, resp.json() if resp.ok else resp.text

def get_data(dataset=DATASET):
    datasets_resp = requests.get(f"{BASE_URL}/api/v1/datasets/", headers=headers, timeout=10)
    if datasets_resp.status_code != 200:
        return datasets_resp.status_code, datasets_resp.text
    ds_list = datasets_resp.json()
    ds_id = None
    for d in ds_list:
        if d["name"] == dataset:
            ds_id = d["id"]
            break
    if not ds_id:
        return 404, "Dataset not found"
    resp = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/data", headers=headers, timeout=30)
    return resp.status_code, resp.json() if resp.ok else resp.text

def print_recall_result(code, result, query):
    print(f"\nrecall('{query}')")
    print(f"   Status: {code}")
    if isinstance(result, dict):
        if 'text' in result:
            print(f"   💡 {result['text']}")
        elif 'error' in result:
            print(f"   ⚠️  {result['error']}")
        else:
            print(f"   📦 {result}")
    elif isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                if 'text' in item:
                    print(f"   💡 {item['text']}")
                elif 'search_result' in item:
                    for r in item['search_result']:
                        print(f"   💡 {r}")
                else:
                    print(f"   📦 {item}")
    else:
        print(f"   {str(result)[:200]}")

def main():
    print("=" * 70)
    print("🧠 Testing Graph Update: Add → Forget → Update")
    print("=" * 70)
    print(f"\nDataset: {DATASET}")

    print("\n" + "=" * 70)
    print("STEP 1: Add initial fact - 'John works at Microsoft'")
    print("=" * 70)
    
    code, data = add_text("John works at Microsoft as a software engineer.")
    print(f"\nadd_text('John works at Microsoft...')")
    print(f"   Status: {code}")
    
    old_data_id = None
    if isinstance(data, dict) and data.get('data_ingestion_info'):
        old_data_id = data['data_ingestion_info'][0].get('data_id')
        print(f"   Data ID: {old_data_id}" if old_data_id else "   Data ID: N/A")

    print("\n" + "=" * 70)
    print("STEP 2: Cognify the graph")
    print("=" * 70)
    
    code, data = cognify()
    print(f"\ncognify() → Status: {code}")

    print("\n" + "=" * 70)
    print("STEP 3: Recall - Should show John works at Microsoft")
    print("=" * 70)
    
    code, result = recall("Where does John work?")
    print_recall_result(code, result, "Where does John work?")

    print("\n" + "=" * 70)
    print("STEP 4: Forget the old fact (John works at Microsoft)")
    print("=" * 70)
    
    if old_data_id:
        code, data = forget(data_id=old_data_id)
        print(f"\nforget(data_id='{old_data_id}')")
        print(f"   Status: {code}")
        print(f"   Result: {data}")
    else:
        print("\n⚠️  No data_id found, skipping forget")

    print("\n" + "=" * 70)
    print("STEP 5: Add corrected fact - 'John is unemployed'")
    print("=" * 70)
    
    code, data = add_text("John is currently unemployed and looking for new opportunities.")
    print(f"\nadd_text('John is currently unemployed...')")
    print(f"   Status: {code}")

    print("\n" + "=" * 70)
    print("STEP 6: Cognify again to update the graph")
    print("=" * 70)
    
    code, data = cognify()
    print(f"\ncognify() → Status: {code}")

    print("\n" + "=" * 70)
    print("STEP 7: Recall - Should show John is unemployed now")
    print("=" * 70)
    
    code, result = recall("Where does John work?")
    print_recall_result(code, result, "Where does John work?")

    print("\n" + "=" * 70)
    print("STEP 8: Test memory_only=True (clear graph, keep raw files)")
    print("=" * 70)
    
    code, data = forget(memory_only=True)
    print(f"\nforget(memory_only=True)")
    print(f"   Status: {code}")
    print(f"   Result: {data}")

    print("\n" + "=" * 70)
    print("STEP 9: Recall after memory_only - Should be empty")
    print("=" * 70)
    
    code, result = recall("Where does John work?")
    print_recall_result(code, result, "Where does John work?")

    print("\n" + "=" * 70)
    print("STEP 10: Cognify again - Should rebuild from raw files")
    print("=" * 70)
    
    code, data = cognify()
    print(f"\ncognify() → Status: {code}")

    print("\n" + "=" * 70)
    print("STEP 11: Recall - Should work again")
    print("=" * 70)
    
    code, result = recall("What is John's employment status?")
    print_recall_result(code, result, "What is John's employment status?")

    print("\n" + "=" * 70)
    print("✅ Graph update test complete!")
    print("=" * 70)
    print("\nSummary:")
    print("  • forget(data_id=...) - removes specific data item")
    print("  • forget(memory_only=True) - clears graph/vectors, keeps raw files")
    print("  • improve() - SDK-only, not available via HTTP API")
    print("  • To update graph: forget old data → add new data → cognify")

if __name__ == "__main__":
    main()
