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

def add_text_to_graph(text, dataset_name="realtime_memory"):
    print(f"\n📝 Adding text to knowledge graph: '{text[:50]}...'")
    
    try:
        add_response = requests.post(
            f"{BASE_URL}/api/v1/add_text",
            json={
                "textData": [text],
                "datasetName": dataset_name
            },
            headers=headers,
            timeout=30
        )
        
        if add_response.status_code not in [200, 201]:
            print(f"❌ Add text failed: {add_response.status_code} - {add_response.text}")
            return False
        
        print("✅ Text added successfully")
        try:
            print(f"   Response: {add_response.json()}")
        except:
            pass
        
        print("🔄 Building knowledge graph...")
        cognify_response = requests.post(
            f"{BASE_URL}/api/v1/cognify",
            json={"datasets": [dataset_name]},
            headers=headers,
            timeout=90
        )
        
        if cognify_response.status_code not in [200, 201, 202]:
            print(f"❌ Cognify failed: {cognify_response.status_code} - {cognify_response.text}")
            return False
        
        print("✅ Knowledge graph updated successfully")
        try:
            print(f"   Response: {cognify_response.json()}")
        except:
            pass
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def search_graph(query, dataset_name="realtime_memory"):
    print(f"\n🔍 Searching graph for: '{query}'")
    
    try:
        search_response = requests.post(
            f"{BASE_URL}/api/v1/search",
            json={
                "query": query,
                "searchType": "GRAPH_COMPLETION",
                "datasets": [dataset_name]
            },
            headers=headers,
            timeout=30
        )
        
        if search_response.status_code != 200:
            print(f"❌ Search failed: {search_response.status_code} - {search_response.text}")
            return None
        
        result = search_response.json()
        print("\n📊 Search Results:")
        if isinstance(result, list):
            for i, item in enumerate(result, 1):
                print(f"\n[{i}] {item}")
        else:
            print(result)
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def main():
    print("=" * 60)
    print("🧠 Real-Time Knowledge Graph Builder - Demo")
    print("=" * 60)
    
    dataset_name = "realtime_memory"
    
    sample_data = [
        "This is my water bottle. It was gifted by my grandfather.",
        "My work desk is where I keep my laptop and keys.",
        "The kitchen shelf contains my coffee mug and spices.",
        "My phone is usually kept on the nightstand."
    ]
    
    print("\n📥 Adding sample data to knowledge graph...")
    for i, text in enumerate(sample_data, 1):
        print(f"\n[{i}/{len(sample_data)}]")
        add_text_to_graph(text, dataset_name)
    
    print("\n" + "=" * 60)
    print("🔍 Testing search functionality...")
    print("=" * 60)
    
    search_queries = [
        "What was gifted by grandfather?",
        "Where are the keys kept?",
        "What's on the kitchen shelf?"
    ]
    
    for i, query in enumerate(search_queries, 1):
        print(f"\n[{i}/{len(search_queries)}]")
        search_graph(query, dataset_name)
    
    print("\n" + "=" * 60)
    print("✅ Demo completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    main()
