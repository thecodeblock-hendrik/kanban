from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="PM MVP Backend")


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


@app.get("/api/health")
async def healthcheck() -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "pm-mvp-backend"})
