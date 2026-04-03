from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, func, select
from urllib.parse import quote_plus

from app.database import get_session
from app.models import MenuItem, Place, Review, User
from app.routers.shared import current_user, pop_flash, templates

router = APIRouter()


def _average_ratings_by_place(session: Session, places: list[Place]) -> dict[int, float]:
    place_ids = [place.id for place in places if place.id is not None]
    if not place_ids:
        return {}

    rating_rows = session.exec(
        select(Review.place_id, func.avg(Review.rating))
        .where(Review.place_id.in_(place_ids))
        .group_by(Review.place_id)
    ).all()

    return {
        place_id: round(float(avg_rating), 1)
        for place_id, avg_rating in rating_rows
        if avg_rating is not None
    }


@router.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    places = session.exec(select(Place)).all()
    average_ratings = _average_ratings_by_place(session, places)
    user = current_user(request, session)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "places": places,
            "average_ratings": average_ratings,
            "user": user,
            "flash": pop_flash(request),
        },
    )


@router.get("/places", response_class=HTMLResponse)
def places_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    places = session.exec(select(Place)).all()
    average_ratings = _average_ratings_by_place(session, places)
    return templates.TemplateResponse(
        request=request,
        name="places.html",
        context={
            "places": places,
            "average_ratings": average_ratings,
            "user": user,
            "flash": pop_flash(request),
        },
    )


@router.get("/places/{place_id}", response_class=HTMLResponse)
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
    average_rating_value = session.exec(
        select(func.avg(Review.rating)).where(Review.place_id == place_id)
    ).first()
    average_rating = (
        round(float(average_rating_value), 1)
        if average_rating_value is not None
        else None
    )
    destination_query = f"{place.name} {place.location}"
    place_maps_url = (
        "https://www.google.com/maps/search/?api=1&query="
        + quote_plus(destination_query)
    )
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
            "average_rating": average_rating,
            "place_maps_url": place_maps_url,
            "destination_query": destination_query,
            "user": user,
            "flash": pop_flash(request),
        },
    )
