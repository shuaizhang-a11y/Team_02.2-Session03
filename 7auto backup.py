import asyncio
import json
import os
import datetime
from dotenv import load_dotenv

# GraphQL Imports
from gql import gql, Client
from gql.transport.websockets import WebsocketsTransport
from gql.transport.aiohttp import AIOHTTPTransport

# --- CONFIGURATION ---
load_dotenv()
SPECKLE_TOKEN = os.environ.get("SPECKLE_TOKEN")
SPECKLE_SERVER = "app.speckle.systems"  # Change if using a custom server
PROJECT_ID = "128262a20c"    
OBJECT_ID = "cae9cccc231d4fc7c7331c1c9d15696a"           # REPLACE with your Project ID

if not SPECKLE_TOKEN:
    raise ValueError("❌ Please set SPECKLE_TOKEN in your environment variables or .env file.")

# --- GRAPHQL QUERIES ---

# 1. Subscription: Listen for new versions
SUB_PROJECT_UPDATES = gql("""
    subscription OnProjectUpdate($projectId: String!) {
        projectVersionsUpdated(id: $projectId) {
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

# 2. Query: Fetch the actual object data (The "Backup" part)
QUERY_OBJECT_DATA = gql("""
    query GetObjectData($projectId: String!, $objectId: String!) {
        project(id: $projectId) {
            object(id: $objectId) {
                id
                speckleType
                data
            }
        }
    }
""")

# --- HELPER FUNCTIONS ---

async def fetch_and_save_data(version_id, object_id, message):
    """
    Connects via HTTP to fetch the object data and saves it to a JSON file.
    """
    print(f"   ⏳ Starting backup for Object: {object_id}...")

    # Set up HTTP Transport for the standard query (WebSockets is for subs only)
    transport = AIOHTTPTransport(
        url=f"https://{SPECKLE_SERVER}/graphql",
        headers={"Authorization": f"Bearer {SPECKLE_TOKEN}"}
    )

    async with Client(transport=transport, fetch_schema_from_transport=False) as session:
        try:
            # Execute the query
            result = await session.execute(
                QUERY_OBJECT_DATA, 
                variable_values={"projectId": PROJECT_ID, "objectId": object_id}
            )
            
            # Extract data
            obj_data = result.get("project", {}).get("object", {}).get("data")
            
            if not obj_data:
                print("   ⚠️  No data found for this object.")
                return

            # Create a filename with timestamp and version ID
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_msg = "".join(c for c in message if c.isalnum() or c in (' ', '_')).rstrip()
            filename = f"backup_{timestamp}_{version_id}_{clean_msg[:20]}.json"
            
            # Ensure backup directory exists
            backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            filepath = os.path.join(backup_dir, filename)

            # Write to disk
            output = {
                "projectId": PROJECT_ID,
                "versionId": version_id,
                "objectId": object_id,
                "backupTime": timestamp,
                "data": obj_data
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, default=str)

            print(f"   ✅ Backup saved: {filename}")

        except Exception as e:
            print(f"   ❌ Failed to download data: {e}")

# --- MAIN SUBSCRIPTION LOOP ---

async def main():
    print(f"🔌 Connecting to Speckle at {SPECKLE_SERVER}...")
    
    # WebSocket Transport for Subscriptions
    transport = WebsocketsTransport(
        url=f"wss://{SPECKLE_SERVER}/graphql",
        init_payload={"Authorization": f"Bearer {SPECKLE_TOKEN}"}
    )

    client = Client(transport=transport, fetch_schema_from_transport=False)

    async with client as session:
        print(f"📡 Listening for updates on Project ID: {PROJECT_ID}")
        print("   (Press Ctrl+C to stop)\n")

        try:
            async for result in session.subscribe(
                SUB_PROJECT_UPDATES, 
                variable_values={"projectId": PROJECT_ID}
            ):
                event = result.get("projectVersionsUpdated", {})
                event_type = event.get("type")
                version = event.get("version", {})

                # We only care if a new version was created (CREATED or UPDATED)
                if event_type in ["CREATED", "UPDATED"] and version:
                    v_id = version.get("id")
                    obj_id = version.get("referencedObject") # The geometry hash
                    msg = version.get("message", "no_message")

                    print("=" * 60)
                    print(f"📦 New Version Detected! [ID: {v_id}]")
                    print(f"   Message: {msg}")
                    print(f"   Object ID: {obj_id}")

                    # Trigger the backup
                    if obj_id:
                        await fetch_and_save_data(v_id, obj_id, msg)
                    else:
                        print("   ⚠️  Could not find referencedObject ID in payload.")
                    print("=" * 60 + "\n")

        except asyncio.CancelledError:
            print("\n👋 Subscription cancelled.")
        except Exception as e:
            print(f"\n❌ Connection Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Backup service stopped.")