from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from database import Base, engine, find_missing_columns
from routers import items, moderation, photos, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the SQLite tables on startup if they don't exist yet.
    Base.metadata.create_all(bind=engine)

    missing = find_missing_columns(engine)
    if missing:
        raise RuntimeError(
            f"The database file is out of date (missing: {', '.join(missing)}). "
            "Stop the server, delete lost_and_found.db, and start it again."
        )
    yield


app = FastAPI(title="Campus Lost & Found", lifespan=lifespan)

app.include_router(users.router)
app.include_router(items.router)
app.include_router(photos.router)
app.include_router(moderation.router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse("static/index.html")
