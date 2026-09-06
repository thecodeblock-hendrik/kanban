from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_BUILD_DIR = BASE_DIR / "frontend" / "out"

app = FastAPI(title="PM MVP Backend")


@app.get("/api/health")
async def healthcheck() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "pm-mvp-backend"})


if FRONTEND_BUILD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_BUILD_DIR), html=True), name="frontend")
else:

    @app.get("/", response_class=HTMLResponse)
    async def read_root() -> HTMLResponse:
        return HTMLResponse(
            """
            <html>
                <head>
                    <title>PM MVP</title>
                    <meta charset="utf-8" />
                </head>
                <body>
                    <h1>PM MVP</h1>
                    <p>Hello from the FastAPI backend.</p>
                </body>
            </html>
            """
        )
