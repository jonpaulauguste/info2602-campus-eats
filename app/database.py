from sqlmodel import SQLModel, Session, create_engine, select

from app.models import MenuItem, Place, Review, User

engine = create_engine("sqlite:///database.db", echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        existing_place = session.exec(select(Place)).first()
        if existing_place:
            return

        users = [
            User(name="Ava Singh", email="ava@campuseats.com"),
            User(name="Jayden Lee", email="jayden@campuseats.com"),
            User(name="Mia Persad", email="mia@campuseats.com"),
        ]
        session.add_all(users)
        session.flush()

        places = [
            Place(
                name="The Campus Grill",
                cuisine="American",
                rating=4.5,
                description="Burgers, fries, and comfort food near the student center.",
                image_url="/static/img/placeholder.svg",
            ),
            Place(
                name="Roti Hut",
                cuisine="Caribbean",
                rating=4.7,
                description="Fresh roti, curry dishes, and local favorites.",
                image_url="/static/img/placeholder.svg",
            ),
            Place(
                name="Cafe Mocha",
                cuisine="Coffee and Pastries",
                rating=4.3,
                description="Coffee, sandwiches, and quick breakfast options.",
                image_url="/static/img/placeholder.svg",
            ),
            Place(
                name="Dragon Wok",
                cuisine="Chinese",
                rating=4.1,
                description="Wok-fried noodles, rice bowls, and lunch specials.",
                image_url="/static/img/placeholder.svg",
            ),
            Place(
                name="Pizza Planet",
                cuisine="Italian",
                rating=4.6,
                description="Pizza slices, pasta bowls, and garlic bread.",
                image_url="/static/img/placeholder.svg",
            ),
            Place(
                name="Doubles Express",
                cuisine="Street Food",
                rating=4.8,
                description="Fast local bites including doubles and pies.",
                image_url="/static/img/placeholder.svg",
            ),
        ]
        session.add_all(places)
        session.flush()

        menu_items = [
            MenuItem(name="Classic Burger", price=35.0, place_id=places[0].id),
            MenuItem(name="Loaded Fries", price=22.0, place_id=places[0].id),
            MenuItem(name="Iced Tea", price=10.0, place_id=places[0].id),
            MenuItem(name="Chicken Roti", price=28.0, place_id=places[1].id),
            MenuItem(name="Goat Roti", price=32.0, place_id=places[1].id),
            MenuItem(name="Solo", price=8.0, place_id=places[1].id),
            MenuItem(name="Cappuccino", price=18.0, place_id=places[2].id),
            MenuItem(name="Ham Sandwich", price=24.0, place_id=places[2].id),
            MenuItem(name="Blueberry Muffin", price=12.0, place_id=places[2].id),
            MenuItem(name="Chicken Chow Mein", price=30.0, place_id=places[3].id),
            MenuItem(name="Beef Fried Rice", price=29.0, place_id=places[3].id),
            MenuItem(name="Spring Rolls", price=16.0, place_id=places[3].id),
            MenuItem(name="Pepperoni Slice", price=14.0, place_id=places[4].id),
            MenuItem(name="Cheese Pizza", price=55.0, place_id=places[4].id),
            MenuItem(name="Pasta Alfredo", price=33.0, place_id=places[4].id),
            MenuItem(name="Doubles", price=7.0, place_id=places[5].id),
            MenuItem(name="Aloo Pie", price=9.0, place_id=places[5].id),
            MenuItem(name="Mauby", price=6.0, place_id=places[5].id),
        ]
        session.add_all(menu_items)

        reviews = [
            Review(
                rating=5,
                comment="Fast service and great flavor.",
                user_id=users[0].id,
                place_id=places[1].id,
            ),
            Review(
                rating=4,
                comment="Good food, portions were decent.",
                user_id=users[1].id,
                place_id=places[0].id,
            ),
            Review(
                rating=5,
                comment="Best doubles on campus.",
                user_id=users[2].id,
                place_id=places[5].id,
            ),
            Review(
                rating=4,
                comment="Coffee was nice and hot.",
                user_id=users[0].id,
                place_id=places[2].id,
            ),
        ]
        session.add_all(reviews)
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
