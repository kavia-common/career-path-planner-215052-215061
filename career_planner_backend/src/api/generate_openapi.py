import json
import os

from src.api.main import app

def generate_openapi_json() -> dict:
    """Return the FastAPI-generated OpenAPI schema."""
    return app.openapi()

if __name__ == "__main__":
    schema = generate_openapi_json()
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "interfaces")
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "openapi.json")
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Wrote OpenAPI schema to {output_path}")
