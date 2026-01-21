"""
01b - Create a Speckle Model

This script demonstrates how to create a new model (branch) in an existing Speckle project.
"""

from main import get_client
from specklepy.core.api.inputs.model_inputs import CreateModelInput


# TODO: Replace with your project ID
PROJECT_ID = "128262a20c"
MODEL_NAME = "homework/session03/team_02.3"


def main():
    # Authenticate
    client = get_client()

    # Create a new model (branch) in the project
    model = client.model.create(CreateModelInput(
        projectId=PROJECT_ID,
        name=MODEL_NAME,
        description="Model created for session 03"
    ))

    print(f"✓ Created model: {model.id}")
    print(f"  Model name: {model.name}")
    print(f"  Project ID: {PROJECT_ID}")


if __name__ == "__main__":
    main()
