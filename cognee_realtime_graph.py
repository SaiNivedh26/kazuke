#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
TENANT_ID = os.getenv("TENANT_ID")
USER_ID = os.getenv("USER_ID")

if not all([BASE_URL, API_KEY, TENANT_ID, USER_ID]):
    print("Error: Missing environment variables. Check .env file.")
    exit(1)

headers = {
    "Content-Type": "application/json",
    "X-Api-Key": API_KEY,
    "X-Tenant-Id": TENANT_ID,
    "X-User-Id": USER_ID
}

DATASET = "realtime_memory"

def add_text(text, dataset=DATASET):
    print(f"\n📝 Adding to graph...")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/v1/add_text",
            json={"textData": [text], "datasetName": dataset},
            headers=headers, timeout=30
        )
        
        if resp.status_code not in [200, 201]:
            print(f"❌ Add failed: {resp.status_code} - {resp.text}")
            return False, None
        
        data = resp.json()
        data_id = None
        if data.get('data_ingestion_info'):
            data_id = data['data_ingestion_info'][0].get('data_id')
        
        print("✅ Text added")
        
        print("🔄 Building graph...")
        cognify_resp = requests.post(
            f"{BASE_URL}/api/v1/cognify",
            json={"datasets": [dataset]},
            headers=headers, timeout=90
        )
        
        if cognify_resp.status_code not in [200, 201, 202]:
            print(f"❌ Cognify failed: {cognify_resp.status_code}")
            return False, data_id
        
        print("✅ Graph updated")
        return True, data_id
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False, None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False, None

def recall(query, dataset=DATASET):
    print(f"\n🔍 Recall: '{query}'")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/v1/recall",
            json={"query": query, "searchType": "GRAPH_COMPLETION", "datasets": [dataset]},
            headers=headers, timeout=30
        )
        
        if resp.status_code == 404:
            print("   ⚠️  No data in graph")
            return None
        
        if resp.status_code != 200:
            print(f"❌ Recall failed: {resp.status_code}")
            return None
        
        result = resp.json()
        if isinstance(result, dict) and 'text' in result:
            print(f"   💡 {result['text']}")
        elif isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and 'text' in item:
                    print(f"   💡 {item['text']}")
                elif isinstance(item, dict) and 'search_result' in item:
                    for r in item['search_result']:
                        print(f"   💡 {r}")
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def forget_data(data_id=None, memory_only=False, dataset=DATASET):
    print(f"\n🗑️  Forget...")
    try:
        payload = {}
        if data_id:
            payload["dataset"] = dataset
            payload["dataId"] = data_id
            print(f"   Removing data_id: {data_id[:12]}...")
        elif memory_only:
            payload["dataset"] = dataset
            payload["memoryOnly"] = True
            print(f"   Clearing graph (keeping raw files)")
        else:
            payload["dataset"] = dataset
            print(f"   Removing entire dataset: {dataset}")
        
        resp = requests.post(
            f"{BASE_URL}/api/v1/forget",
            json=payload,
            headers=headers, timeout=90
        )
        
        if resp.status_code != 200:
            print(f"❌ Forget failed: {resp.status_code} - {resp.text}")
            return False
        
        result = resp.json()
        print(f"✅ {result.get('status', 'success')}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def list_data(dataset=DATASET):
    print(f"\n📋 Listing data in '{dataset}'...")
    try:
        datasets_resp = requests.get(f"{BASE_URL}/api/v1/datasets/", headers=headers, timeout=10)
        if datasets_resp.status_code != 200:
            print(f"❌ Failed to list datasets")
            return []
        
        ds_list = datasets_resp.json()
        ds_id = None
        for d in ds_list:
            if d["name"] == dataset:
                ds_id = d["id"]
                break
        
        if not ds_id:
            print(f"   Dataset '{dataset}' not found")
            return []
        
        resp = requests.get(f"{BASE_URL}/api/v1/datasets/{ds_id}/data", headers=headers, timeout=30)
        
        if resp.status_code != 200:
            print(f"❌ Failed: {resp.status_code}")
            return []
        
        data_items = resp.json()
        if isinstance(data_items, list):
            print(f"   Found {len(data_items)} data items:")
            for item in data_items:
                item_id = item.get('id', 'N/A')
                print(f"     • {item_id}")
            return data_items
        else:
            print(f"   {str(data_items)[:200]}")
            return []
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def main():
    print("=" * 70)
    print("🧠 Real-Time Knowledge Graph Builder")
    print("=" * 70)
    print("\nCommands:")
    print("  • <text>              - Add text to graph")
    print("  • recall <query>      - Search the graph")
    print("  • forget <data_id>    - Remove specific data")
    print("  • forget --memory     - Clear graph (keep raw files)")
    print("  • forget --all        - Remove entire dataset")
    print("  • list                - List all data items")
    print("  • quit                - Exit")
    print("=" * 70)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'quit':
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower().startswith('recall '):
                query = user_input[7:].strip()
                if query:
                    recall(query, DATASET)
                else:
                    print("Please provide a search query")
            
            elif user_input.lower().startswith('forget '):
                args = user_input[7:].strip()
                if args == '--memory':
                    forget_data(memory_only=True, dataset=DATASET)
                elif args == '--all':
                    forget_data(dataset=DATASET)
                else:
                    data_id = args.strip()
                    if data_id:
                        forget_data(data_id=data_id, dataset=DATASET)
                    else:
                        print("Usage: forget <data_id> | forget --memory | forget --all")
            
            elif user_input.lower() == 'list':
                list_data(DATASET)
            
            else:
                success, data_id = add_text(user_input, DATASET)
                if success and data_id:
                    print(f"   Data ID: {data_id}")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
