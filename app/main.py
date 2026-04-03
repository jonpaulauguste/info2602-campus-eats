from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import SECRET_KEY
from app.database import create_db_and_tables
from app.routers import admin, auth, places, reviews


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(places.router)
app.include_router(reviews.router)
app.include_router(admin.router)
