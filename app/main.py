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


def is_management(user: User | None) -> bool:
    return bool(user and user.role in ("management", "admin"))


def update_place_rating(session: Session, place_id: int):
    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        return

    reviews = session.exec(select(Review).where(Review.place_id == place_id)).all()
    if reviews:
        place.rating = round(sum(review.rating for review in reviews) / len(reviews), 1)
        session.add(place)


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

    new_user = User(
        username=username,
        email=email,
        password=hash_password(password),
        role="user",
    )
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

    menu_items = session.exec(select(MenuItem).where(MenuItem.place_id == place_id)).all()

    review_rows = session.exec(
        select(Review, User)
        .join(User, User.id == Review.user_id)
        .where(Review.place_id == place_id)
    ).all()
    reviews = [
        {
            "id": review.id,
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


@app.post("/places/{place_id}/reviews")
def add_review(
    request: Request,
    place_id: int,
    rating: int = Form(...),
    comment: str = Form(default=""),
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in to leave a review.")
        return RedirectResponse(url="/login", status_code=303)

    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    if rating < 1 or rating > 5:
        set_flash(request, "error", "Rating must be between 1 and 5.")
        return RedirectResponse(url=f"/places/{place_id}", status_code=303)

    review = Review(
        rating=rating,
        comment=comment.strip(),
        user_id=user.id,
        place_id=place_id,
    )
    session.add(review)
    session.flush()

    update_place_rating(session, place_id)
    session.commit()

    set_flash(request, "success", "Review added.")
    return RedirectResponse(url=f"/places/{place_id}", status_code=303)


@app.get("/admin/places", response_class=HTMLResponse)
def admin_places_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    places = session.exec(select(Place)).all()
    menu_items_by_place = {
        place.id: session.exec(select(MenuItem).where(MenuItem.place_id == place.id)).all()
        for place in places
    }

    return templates.TemplateResponse(
        request=request,
        name="admin_places.html",
        context={
            "places": places,
            "menu_items_by_place": menu_items_by_place,
            "user": user,
            "flash": pop_flash(request),
        },
    )


@app.get("/admin/places/new", response_class=HTMLResponse)
def admin_new_place_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="admin_place_form.html",
        context={
            "title": "Add New Place",
            "action_url": "/admin/places/new",
            "submit_label": "Create Place",
            "place": None,
            "user": user,
            "flash": pop_flash(request),
        },
    )


@app.post("/admin/places/new")
def admin_create_place(
    request: Request,
    name: str = Form(...),
    cuisine: str = Form(...),
    location: str = Form(...),
    image_url: str = Form(default="/static/img/placeholder.svg"),
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    new_place = Place(
        name=name.strip(),
        cuisine=cuisine.strip(),
        location=location.strip(),
        rating=0.0,
        image_url=image_url.strip() or "/static/img/placeholder.svg",
    )
    session.add(new_place)
    session.commit()

    set_flash(request, "success", "Place created.")
    return RedirectResponse(url="/admin/places", status_code=303)


@app.get("/admin/places/{place_id}/edit", response_class=HTMLResponse)
def admin_edit_place_page(
    request: Request,
    place_id: int,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    return templates.TemplateResponse(
        request=request,
        name="admin_place_form.html",
        context={
            "title": f"Edit Place: {place.name}",
            "action_url": f"/admin/places/{place_id}/edit",
            "submit_label": "Save Place",
            "place": place,
            "user": user,
            "flash": pop_flash(request),
        },
    )


@app.post("/admin/places/{place_id}/edit")
def admin_edit_place(
    request: Request,
    place_id: int,
    name: str = Form(...),
    cuisine: str = Form(...),
    location: str = Form(...),
    image_url: str = Form(default="/static/img/placeholder.svg"),
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    place.name = name.strip()
    place.cuisine = cuisine.strip()
    place.location = location.strip()
    place.image_url = image_url.strip() or "/static/img/placeholder.svg"
    session.add(place)
    session.commit()

    set_flash(request, "success", "Place updated.")
    return RedirectResponse(url="/admin/places", status_code=303)


@app.post("/admin/places/{place_id}/delete")
def admin_delete_place(
    request: Request,
    place_id: int,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    menu_items = session.exec(select(MenuItem).where(MenuItem.place_id == place_id)).all()
    reviews = session.exec(select(Review).where(Review.place_id == place_id)).all()
    for menu_item in menu_items:
        session.delete(menu_item)
    for review in reviews:
        session.delete(review)
    session.delete(place)
    session.commit()

    set_flash(request, "success", "Place deleted.")
    return RedirectResponse(url="/admin/places", status_code=303)


@app.get("/admin/places/{place_id}/menu/new", response_class=HTMLResponse)
def admin_new_menu_item_page(
    request: Request,
    place_id: int,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    return templates.TemplateResponse(
        request=request,
        name="admin_menu_form.html",
        context={
            "title": f"Add Menu Item: {place.name}",
            "action_url": f"/admin/places/{place_id}/menu/new",
            "submit_label": "Create Menu Item",
            "menu_item": None,
            "place": place,
            "user": user,
            "flash": pop_flash(request),
        },
    )


@app.post("/admin/places/{place_id}/menu/new")
def admin_add_menu_item(
    request: Request,
    place_id: int,
    name: str = Form(...),
    price: float = Form(...),
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    menu_item = MenuItem(name=name.strip(), price=price, place_id=place_id)
    session.add(menu_item)
    session.commit()

    set_flash(request, "success", "Menu item added.")
    return RedirectResponse(url="/admin/places", status_code=303)


@app.get("/admin/menu/{menu_item_id}/edit", response_class=HTMLResponse)
def admin_edit_menu_item_page(
    request: Request,
    menu_item_id: int,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    menu_item = session.exec(select(MenuItem).where(MenuItem.id == menu_item_id)).first()
    if menu_item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")

    place = session.exec(select(Place).where(Place.id == menu_item.place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    return templates.TemplateResponse(
        request=request,
        name="admin_menu_form.html",
        context={
            "title": f"Edit Menu Item: {menu_item.name}",
            "action_url": f"/admin/menu/{menu_item_id}/edit",
            "submit_label": "Save Menu Item",
            "menu_item": menu_item,
            "place": place,
            "user": user,
            "flash": pop_flash(request),
        },
    )


@app.post("/admin/menu/{menu_item_id}/edit")
def admin_edit_menu_item(
    request: Request,
    menu_item_id: int,
    name: str = Form(...),
    price: float = Form(...),
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    menu_item = session.exec(select(MenuItem).where(MenuItem.id == menu_item_id)).first()
    if menu_item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")

    menu_item.name = name.strip()
    menu_item.price = price
    session.add(menu_item)
    session.commit()

    set_flash(request, "success", "Menu item updated.")
    return RedirectResponse(url="/admin/places", status_code=303)


@app.post("/admin/menu/{menu_item_id}/delete")
def admin_delete_menu_item(
    request: Request,
    menu_item_id: int,
    session: Session = Depends(get_session),
):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return RedirectResponse(url="/", status_code=303)

    menu_item = session.exec(select(MenuItem).where(MenuItem.id == menu_item_id)).first()
    if menu_item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")

    session.delete(menu_item)
    session.commit()

    set_flash(request, "success", "Menu item deleted.")
    return RedirectResponse(url="/admin/places", status_code=303)
