from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import Base, engine
from routers import items, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the SQLite tables on startup if they don't exist yet.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Campus Lost & Found", lifespan=lifespan)

app.include_router(users.router)
app.include_router(items.router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse("static/index.html")
