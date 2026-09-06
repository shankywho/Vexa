"""Export OpenAPI / Swagger JSON specification for ClosePilot backend."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import create_app  # noqa: E402


def export_openapi() -> None:
    app = create_app()
    openapi_schema = app.openapi()

    workspace_root = backend_dir.parent
    docs_api_dir = workspace_root / "docs" / "api"
    docs_api_dir.mkdir(parents=True, exist_ok=True)

    output_paths = [
        docs_api_dir / "openapi.json",
        docs_api_dir / "swagger.json",
        workspace_root / "openapi.json",
        workspace_root / "swagger.json",
    ]

    schema_str = json.dumps(openapi_schema, indent=2, ensure_ascii=False) + "\n"

    for path in output_paths:
        path.write_text(schema_str, encoding="utf-8")
        print(f"Exported Swagger/OpenAPI spec to: {path.relative_to(workspace_root)}")

    num_paths = len(openapi_schema.get("paths", {}))
    version = openapi_schema.get("info", {}).get("version", "unknown")
    print(f"\nSuccessfully generated Swagger specification (Version {version}, {num_paths} endpoints).")


if __name__ == "__main__":
    export_openapi()
