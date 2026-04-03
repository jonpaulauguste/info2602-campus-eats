from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.auth import get_user_from_cookie
from app.models import Place, Review, User

templates = Jinja2Templates(directory="app/templates")


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
