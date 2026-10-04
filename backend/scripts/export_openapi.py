import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.main import app
from fastapi.openapi.utils import get_openapi

def export():
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    docs_path = os.path.join(os.path.dirname(__file__), "../../docs")
    os.makedirs(docs_path, exist_ok=True)
    with open(os.path.join(docs_path, "openapi.json"), "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print("Exported openapi.json")

if __name__ == "__main__":
    export()
