from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.routers import upload, analyze, stats, export

app = FastAPI(title="Sentiment Analyzer")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(stats.router)
app.include_router(export.router)

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse("app/templates/index.html")

@app.get("/health")
async def health():
    return {"status": "ok"}