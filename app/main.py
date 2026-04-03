from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from app.database import create_db_and_tables

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


# Sample data for now — will be replaced by database queries later
CATEGORIES = [
    {"name": "Food", "icon": "🍔"},
    {"name": "Drinks", "icon": "🥤"},
    {"name": "Coffee", "icon": "☕"},
    {"name": "Snacks", "icon": "🍿"},
    {"name": "Desserts", "icon": "🍰"},
    {"name": "Healthy", "icon": "🥗"},
    {"name": "Bakery", "icon": "🥐"},
    {"name": "Vegetarian", "icon": "🥬"},
]

SAMPLE_PLACES = [
    {
        "id": 1,
        "name": "The Campus Grill",
        "cuisine": "American",
        "location": "Student Centre",
        "rating": 4.5,
        "image_url": "/static/img/placeholder.svg",
        "tags": ["Burgers", "Fries"],
    },
    {
        "id": 2,
        "name": "Roti Hut",
        "cuisine": "Caribbean",
        "location": "South Gate",
        "rating": 4.7,
        "image_url": "/static/img/placeholder.svg",
        "tags": ["Roti", "Curry"],
    },
    {
        "id": 3,
        "name": "Café Mocha",
        "cuisine": "Coffee & Pastries",
        "location": "Library Building",
        "rating": 4.3,
        "image_url": "/static/img/placeholder.svg",
        "tags": ["Coffee", "Pastries"],
    },
    {
        "id": 4,
        "name": "Dragon Wok",
        "cuisine": "Chinese",
        "location": "Engineering Block",
        "rating": 4.1,
        "image_url": "/static/img/placeholder.svg",
        "tags": ["Fried Rice", "Noodles"],
    },
    {
        "id": 5,
        "name": "Pizza Planet",
        "cuisine": "Italian",
        "location": "North Plaza",
        "rating": 4.6,
        "image_url": "/static/img/placeholder.svg",
        "tags": ["Pizza", "Pasta"],
    },
    {
        "id": 6,
        "name": "Doubles Express",
        "cuisine": "Street Food",
        "location": "Main Entrance",
        "rating": 4.8,
        "image_url": "/static/img/placeholder.svg",
        "tags": ["Doubles", "Aloo Pie"],
    },
]


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "categories": CATEGORIES,
            "places": SAMPLE_PLACES,
            "user": None,  # No auth yet
        }
    )