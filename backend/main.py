#!/usr/bin/env python
"""Application entry point."""

from api.app import app

if __name__ == "__main__":
    import uvicorn

    print("Starting server at http://localhost:8000")
    print("Swagger UI: http://localhost:8000/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
