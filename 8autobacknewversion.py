"""
Auto Backup Speckle Data

This script merges the functionality of:
1. Listening for project updates via WebSocket (Subscription).
2. Automatically downloading the object data via HTTP (Query) when an update occurs.
"""

import asyncio
import json
import os
import datetime
from dotenv import load_dotenv

# GraphQL Imports
from gql import gql, Client
from gql.transport.websockets import WebsocketsTransport

# Import get_client from your original main.py file
# Make sure main.py is in the same directory
from main import get_client 

# --- CONFIGURATION ---
load_dotenv()
YOUR_TOKEN = os.environ.get("SPECKLE_TOKEN")
PROJECT_ID = "128262a20c" # Replace with your Project ID

# --- PART 1: DOWNLOAD FUNCTIONALITY (From Script 1) ---

def query_object_data_graphql(client, project_id: str, object_id: str) -> dict:
    """
    Query object data from Speckle using the authenticated client.
    """
    query = gql("""
    query GetObjectDataJSON($objectId: String!, $projectId: String!) {
        project(id: $projectId) {
            object(id: $objectId) {
                id
                speckleType
                data
            }
        }
    }
    """)
    
    variables = {
        "projectId": project_id,
        "objectId": object_id
    }
    
    # Execute GraphQL query using the client's HTTP session
    result = client.httpclient.execute(query, variable_values=variables)
    return result

def save_backup(client, project_id, object_id, version_id, message):
    """
    Orchestrates the download and saving of the JSON file.
    """
    print(f"   ⬇️  Starting download for Object: {object_id}...")
    
    try:
        # Execute GraphQL query
        graphql_result = query_object_data_graphql(client, project_id, object_id)
        
        data = graphql_result.get("project", {}).get("object", {}).get("data")
        if not data:
            print("   ⚠️  No data found for this object.")
            return

        # Prepare filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Clean message to be filename-safe
        clean_msg = "".join(c for c in message if c.isalnum() or c in (' ', '_')).rstrip()
        filename = f"backup_{timestamp}_{version_id}.json"
        
        # Save to JSON file in the same directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.join(script_dir, filename)
        
        output = {
            "projectId": project_id,
            "versionId": version_id,
            "objectId": object_id,
            "message": message,
            "backupTimestamp": timestamp,
            "data": data
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
            
        print(f"   ✅ Backup saved successfully: {filename}")
        
    except Exception as e:
        print(f"   ❌ Download failed: {e}")


# --- PART 2: LISTENER FUNCTIONALITY (From Script 2) ---

# Note: Added 'referencedObject' to the query to link the version to the data
subscription_query = gql("""
    subscription ProjectVersionsUpdated($projectId: String!) {
        projectVersionsUpdated(id: $projectId) {
            id
            modelId
            type
            version {
                id
                message
                createdAt
                referencedObject 
            }
        }
    }
""")

async def subscribe_and_backup():
    """
    Main async loop: Listens for updates and triggers backup.
    """
    # 1. Authenticate HTTP Client (for downloading)
    speckle_client = get_client()
    print(f"✓ Authenticated for downloads (HTTP)")

    # 2. Setup WebSocket Transport (for listening)
    transport = WebsocketsTransport(
        url="wss://app.speckle.systems/graphql",
        init_payload={
            "Authorization": f"Bearer {YOUR_TOKEN}"
        }
    )
    
    client = Client(
        transport=transport,
        fetch_schema_from_transport=False,
    )
    
    try:
        async with client as session:
            print(f"🔌 Connected to Speckle WebSocket")
            print(f"📡 Listening for updates on project: {PROJECT_ID}")
            print("Press Ctrl+C to stop\n")
            
            # Listen loop
            async for result in session.subscribe(
                subscription_query,
                variable_values={"projectId": PROJECT_ID}
            ):
                print("=" * 50)
                print("📦 New Update Received!")
                
                event_data = result.get("projectVersionsUpdated")
                
                if event_data:
                    event_type = event_data.get('type')
                    version = event_data.get('version')
                    
                    # We only care about CREATED or UPDATED events
                    if version and event_type in ['CREATED', 'UPDATED']:
                        v_id = version.get('id')
                        msg = version.get('message')
                        obj_id = version.get('referencedObject') # This is the ID needed for download
                        
                        print(f"   Version ID: {v_id}")
                        print(f"   Message: {msg}")
                        print(f"   Ref Object: {obj_id}")
                        
                        # ---> TRIGGER BACKUP <---
                        if obj_id:
                            # Note: Calling synchronous function inside async loop
                            save_backup(speckle_client, PROJECT_ID, obj_id, v_id, msg)
                        else:
                            print("   ⚠️ No referenced object found in update payload.")
                            
                print("=" * 50 + "\n")
            
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n👋 Subscription stopped by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await transport.close()
        print("🔌 Connection closed properly.")

if __name__ == "__main__":
    asyncio.run(subscribe_and_backup())