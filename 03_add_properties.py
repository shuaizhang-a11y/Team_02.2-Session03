"""
03 - Add Properties to Objects in a Speckle Model

This script demonstrates how to receive objects from Speckle,
add custom properties, and send them back as a new version.

Use this model: https://app.speckle.systems/projects/YOUR_PROJECT_ID/models/YOUR_MODEL_ID
"""

from main import get_client
from specklepy.transports.server import ServerTransport
from specklepy.api import operations
from specklepy.objects.base import Base
from specklepy.core.api.inputs.version_inputs import CreateVersionInput



# TODO: Replace with your project, model, and version IDs
PROJECT_ID = "128262a20c"
MODEL_ID = "9884593105"
VERSION_ID = "08b571817c"


def main():
    # Authenticate
    client = get_client()

    # Get the specific version
    version = client.version.get(VERSION_ID, PROJECT_ID)
    print(f"✓ Fetching version: {version.id}")

    # Receive the data
    transport = ServerTransport(client=client, stream_id=PROJECT_ID)
    data = operations.receive(version.referenced_object, transport)

    # ---------------------------
    # Add root-level properties
    # ---------------------------
    data["custom_property"] = "Team_02.2"
    data["analysis_date"] = "2026-01-18"
    data["processed_by"] = "Shuai Zhang"



    # ---------------------------
    # Modify Designer names in child elements
    # ---------------------------
  # Modify Designer names in child elements
    # ---------------------------
    elements = getattr(data, "@elements", None) or getattr(data, "elements", [])

    for i, element in enumerate(elements or []):
        if not isinstance(element, Base):
            continue

        # Optional: add index and tag
        element["element_index"] = i
        element["custom_tag"] = f"Element_{i:03d}"

        # Skip if no properties
        if "properties" not in element.get_member_names():
            continue

        props = element["properties"]

        # Find Identity dictionary (where Viewer reads Designer)
        identity = None
        if "Identity" in props and isinstance(props["Identity"], dict):
            identity = props["Identity"]
        elif "BIM" in props and "Identity" in props["BIM"] and isinstance(props["BIM"]["Identity"], dict):
            identity = props["BIM"]["Identity"]

        if not identity:
            continue

        # Modify Designer based on Module
        module = identity.get("Module")
        if module == 1:
            identity["Designer"] = "Giovanni Carlo"
        elif module == 3:
            identity["Designer"] = "Hala Lahlou"

    print(f"✓ Updated Designer names for elements.")

    # ---------------------------
    # Send the modified data back
    # ---------------------------
    object_id = operations.send(data, [transport])
    print(f"✓ Sent object: {object_id}")

    # Create a new version in Speckle
    version = client.version.create(
        CreateVersionInput(
            projectId=PROJECT_ID,
            modelId=MODEL_ID,
            objectId=object_id,
            message="Updated Designer names for Module 1 & 3"
        )
    )

    print(f"✓ Created new version: {version.id}")

# ---------------------------
# ENTRY POINT
# ---------------------------
if __name__ == "__main__":
    main()