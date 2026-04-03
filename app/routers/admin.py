from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.database import get_session
from app.models import MenuItem, Place, Review
from app.routers.shared import current_user, is_management, pop_flash, set_flash, templates

router = APIRouter()


def _require_management(request: Request, session: Session):
    user = current_user(request, session)
    if user is None:
        set_flash(request, "error", "Please log in.")
        return None, RedirectResponse(url="/login", status_code=303)
    if not is_management(user):
        set_flash(request, "error", "Management access required.")
        return None, RedirectResponse(url="/", status_code=303)
    return user, None


@router.get("/admin/places", response_class=HTMLResponse)
def admin_places_page(request: Request, session: Session = Depends(get_session)):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

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


@router.get("/admin/places/new", response_class=HTMLResponse)
def admin_new_place_page(request: Request, session: Session = Depends(get_session)):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

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


@router.post("/admin/places/new")
def admin_create_place(
    request: Request,
    name: str = Form(...),
    cuisine: str = Form(...),
    location: str = Form(...),
    description: str = Form(default=""),
    image_url: str = Form(default="/static/img/placeholder.svg"),
    session: Session = Depends(get_session),
):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

    new_place = Place(
        name=name.strip(),
        cuisine=cuisine.strip(),
        location=location.strip(),
        description=description.strip(),
        rating=0.0,
        image_url=image_url.strip() or "/static/img/placeholder.svg",
    )
    session.add(new_place)
    session.commit()

    set_flash(request, "success", "Place created.")
    return RedirectResponse(url="/admin/places", status_code=303)


@router.get("/admin/places/{place_id}/edit", response_class=HTMLResponse)
def admin_edit_place_page(
    request: Request,
    place_id: int,
    session: Session = Depends(get_session),
):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

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


@router.post("/admin/places/{place_id}/edit")
def admin_edit_place(
    request: Request,
    place_id: int,
    name: str = Form(...),
    cuisine: str = Form(...),
    location: str = Form(...),
    description: str = Form(default=""),
    image_url: str = Form(default="/static/img/placeholder.svg"),
    session: Session = Depends(get_session),
):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    place.name = name.strip()
    place.cuisine = cuisine.strip()
    place.location = location.strip()
    place.description = description.strip()
    place.image_url = image_url.strip() or "/static/img/placeholder.svg"
    session.add(place)
    session.commit()

    set_flash(request, "success", "Place updated.")
    return RedirectResponse(url="/admin/places", status_code=303)


@router.post("/admin/places/{place_id}/delete")
def admin_delete_place(
    request: Request,
    place_id: int,
    session: Session = Depends(get_session),
):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

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


@router.get("/admin/places/{place_id}/menu/new", response_class=HTMLResponse)
def admin_new_menu_item_page(
    request: Request,
    place_id: int,
    session: Session = Depends(get_session),
):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

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


@router.post("/admin/places/{place_id}/menu/new")
def admin_add_menu_item(
    request: Request,
    place_id: int,
    name: str = Form(...),
    price: float = Form(...),
    session: Session = Depends(get_session),
):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

    place = session.exec(select(Place).where(Place.id == place_id)).first()
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")

    menu_item = MenuItem(name=name.strip(), price=price, place_id=place_id)
    session.add(menu_item)
    session.commit()

    set_flash(request, "success", "Menu item added.")
    return RedirectResponse(url="/admin/places", status_code=303)


@router.get("/admin/menu/{menu_item_id}/edit", response_class=HTMLResponse)
def admin_edit_menu_item_page(
    request: Request,
    menu_item_id: int,
    session: Session = Depends(get_session),
):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

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


@router.post("/admin/menu/{menu_item_id}/edit")
def admin_edit_menu_item(
    request: Request,
    menu_item_id: int,
    name: str = Form(...),
    price: float = Form(...),
    session: Session = Depends(get_session),
):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

    menu_item = session.exec(select(MenuItem).where(MenuItem.id == menu_item_id)).first()
    if menu_item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")

    menu_item.name = name.strip()
    menu_item.price = price
    session.add(menu_item)
    session.commit()

    set_flash(request, "success", "Menu item updated.")
    return RedirectResponse(url="/admin/places", status_code=303)


@router.post("/admin/menu/{menu_item_id}/delete")
def admin_delete_menu_item(
    request: Request,
    menu_item_id: int,
    session: Session = Depends(get_session),
):
    user, redirect = _require_management(request, session)
    if redirect:
        return redirect

    menu_item = session.exec(select(MenuItem).where(MenuItem.id == menu_item_id)).first()
    if menu_item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")

    session.delete(menu_item)
    session.commit()

    set_flash(request, "success", "Menu item deleted.")
    return RedirectResponse(url="/admin/places", status_code=303)
