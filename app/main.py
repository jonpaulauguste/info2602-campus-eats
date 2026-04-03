from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    ACCESS_COOKIE_NAME,
    SECRET_KEY,
    create_access_token,
    get_user_from_cookie,
    hash_password,
    verify_password,
)
from app.database import create_db_and_tables, get_session
from app.models import MenuItem, Place, Review, User

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


def set_flash(request: Request, category: str, message: str):
    request.session["flash"] = {"category": category, "message": message}


def pop_flash(request: Request):
    return request.session.pop("flash", None)


def current_user(request: Request, session: Session):
    return get_user_from_cookie(request, session)


@app.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    places = session.exec(select(Place)).all()
    user = current_user(request, session)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "places": places,
            "user": user,
            "flash": pop_flash(request),
        },
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"user": None, "flash": pop_flash(request)},
    )


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.username == username)).first()
    if not user or not verify_password(password, user.password):
        set_flash(request, "error", "Invalid username or password.")
        return RedirectResponse(url="/login", status_code=303)

    token = create_access_token({"sub": user.username})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
    )
    return response


@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={"user": None, "flash": pop_flash(request)},
    )


@app.post("/signup")
def signup(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    existing_user = session.exec(select(User).where(User.username == username)).first()
    if existing_user:
        set_flash(request, "error", "Username is already taken.")
        return RedirectResponse(url="/signup", status_code=303)

    existing_email = session.exec(select(User).where(User.email == email)).first()
    if existing_email:
        set_flash(request, "error", "Email is already in use.")
        return RedirectResponse(url="/signup", status_code=303)

    new_user = User(username=username, email=email, password=hash_password(password))
    session.add(new_user)
    session.commit()

    set_flash(request, "success", "Signup successful. Please log in.")
    return RedirectResponse(url="/login", status_code=303)


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(ACCESS_COOKIE_NAME)
    return response


@app.get("/places", response_class=HTMLResponse)
def places_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)

    places = session.exec(select(Place)).all()
    return templates.TemplateResponse(
        request=request,
        name="places.html",
        context={
            "places": places,
            "user": user,
            "flash": pop_flash(request),
        },
    )


@app.get("/places/{place_id}", response_class=HTMLResponse)
def place_detail(
    request: Request,
    place_id: int,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)

    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    menu_items = session.exec(
        select(MenuItem).where(MenuItem.place_id == place_id)
    ).all()

    review_rows = session.exec(
        select(Review, User)
        .join(User, User.id == Review.user_id)
        .where(Review.place_id == place_id)
    ).all()
    reviews = [
        {
            "rating": review.rating,
            "comment": review.comment,
            "user_name": review_user.username,
        }
        for review, review_user in review_rows
    ]

    return templates.TemplateResponse(
        request=request,
        name="place_detail.html",
        context={
            "place": place,
            "menu_items": menu_items,
            "reviews": reviews,
            "user": user,
            "flash": pop_flash(request),
        },
    )
