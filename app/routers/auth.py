from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from app.auth import ACCESS_COOKIE_NAME, create_access_token, hash_password, verify_password
from app.database import get_session
from app.models import User
from app.routers.shared import current_user, pop_flash, set_flash, templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"user": None, "flash": pop_flash(request)},
    )


@router.post("/login")
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


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, session: Session = Depends(get_session)):
    user = current_user(request, session)
    if user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={"user": None, "flash": pop_flash(request)},
    )


@router.post("/signup")
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


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(ACCESS_COOKIE_NAME)
    return response
