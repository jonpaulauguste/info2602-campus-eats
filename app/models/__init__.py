from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    password: str
    role: str = Field(default="user")

    reviews: list["Review"] = Relationship(back_populates="user")


class Place(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    cuisine: str
    location: str
    description: str = ""
    rating: float = 0.0
    image_url: str = "/static/img/placeholder.svg"

    menu_items: list["MenuItem"] = Relationship(back_populates="place")
    reviews: list["Review"] = Relationship(back_populates="place")


class MenuItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    price: float

    place_id: int = Field(foreign_key="place.id")
    place: Optional[Place] = Relationship(back_populates="menu_items")


class Review(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rating: int = Field(ge=1, le=5)
    comment: str = ""

    user_id: int = Field(foreign_key="user.id")
    place_id: int = Field(foreign_key="place.id")

    user: Optional[User] = Relationship(back_populates="reviews")
    place: Optional[Place] = Relationship(back_populates="reviews")
