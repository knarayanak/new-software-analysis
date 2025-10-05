from fastapi import FastAPI
from app.routers import router as root_router

app = FastAPI(title="New software analysis")
app.include_router(root_router)

@app.get("/")
def read_root():
    return {"status": "ok"}
