from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import Place, Review
from app.routers.shared import current_user, set_flash, update_place_rating

router = APIRouter()


@router.post("/places/{place_id}/reviews")
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
