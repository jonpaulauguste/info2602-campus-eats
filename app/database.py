from sqlmodel import SQLModel, Session, create_engine, select

from app.auth import hash_password, verify_password
from app.models import MenuItem, Place, Review, User

engine = create_engine("sqlite:///database.db", echo=True)

PLACE_IMAGE_OVERRIDES = {
    "The Campus Grill": "/static/img/campus-grill.jpg",
    "Cafe Mocha": "/static/img/cafe-mocha.jpg",
    "Roti Hut": "/static/img/roti-hut.jpg",
    "Pizza Planet": "/static/img/pizza-planet.jpg",
    "Dragon Wok": "/static/img/dragon-wok.jpg",
    "Doubles Express": "/static/img/doubles-express.jpg",
    "Barry's Gyro": "/static/img/barrys-gyro.jpg",
    "Island Bites": "/static/img/island-bites.jpg",
}

PLACE_DETAILS_OVERRIDES = {
    "The Campus Grill": {
        "location": "Student Centre",
        "description": "Burgers, fries, and comfort food near the student center.",
    },
    "Roti Hut": {
        "location": "South Gate",
        "description": "Fresh roti, curry dishes, and local favorites.",
    },
    "Cafe Mocha": {
        "location": "Library Building",
        "description": "Coffee, pastries, and quick breakfast options.",
    },
    "Dragon Wok": {
        "location": "Engineering Block",
        "description": "Wok-fried noodles, rice bowls, and lunch specials.",
    },
    "Pizza Planet": {
        "location": "North Plaza",
        "description": "Pizza slices, pasta bowls, and garlic bread.",
    },
    "Doubles Express": {
        "location": "Main Entrance",
        "description": "Street-side doubles, drinks, and quick bites.",
    },
}


def _migrate_user_table_if_needed():
    with engine.begin() as connection:
        columns = [
            row[1]
            for row in connection.exec_driver_sql('PRAGMA table_info("user")').all()
        ]
        if not columns:
            return

        if "username" not in columns and "name" in columns:
            connection.exec_driver_sql(
                'ALTER TABLE "user" RENAME COLUMN name TO username'
            )
            columns = [
                row[1]
                for row in connection.exec_driver_sql(
                    'PRAGMA table_info("user")'
                ).all()
            ]

        if "password" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE \"user\" ADD COLUMN password VARCHAR NOT NULL DEFAULT ''"
            )

        if "role" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE \"user\" ADD COLUMN role VARCHAR NOT NULL DEFAULT 'user'"
            )

        connection.exec_driver_sql(
            'CREATE UNIQUE INDEX IF NOT EXISTS ix_user_username ON "user" (username)'
        )
        connection.exec_driver_sql(
            'CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON "user" (email)'
        )
        connection.exec_driver_sql(
            'UPDATE "user" SET role = "user" WHERE role IS NULL OR role = ""'
        )


def _migrate_place_table_if_needed():
    with engine.begin() as connection:
        columns = [
            row[1]
            for row in connection.exec_driver_sql('PRAGMA table_info("place")').all()
        ]
        if not columns:
            return

        if "location" not in columns:
            connection.exec_driver_sql(
                'ALTER TABLE "place" ADD COLUMN location VARCHAR NOT NULL DEFAULT ""'
            )
            columns.append("location")

        if "description" not in columns:
            connection.exec_driver_sql(
                'ALTER TABLE "place" ADD COLUMN description VARCHAR NOT NULL DEFAULT ""'
            )
            columns.append("description")

        if "description" in columns:
            connection.exec_driver_sql(
                'UPDATE "place" SET location = description '
                'WHERE location = "" AND description IS NOT NULL'
            )
            connection.exec_driver_sql(
                'UPDATE "place" SET description = location '
                'WHERE description = "" AND location IS NOT NULL'
            )


def _ensure_user(
    session: Session,
    username: str,
    email: str,
    plain_password: str,
    role: str,
) -> User:
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        user = session.exec(select(User).where(User.email == email)).first()

    if user is None:
        user = User(
            username=username,
            email=email,
            password=hash_password(plain_password),
            role=role,
        )
        session.add(user)
        session.flush()
        return user

    user.username = username
    user.email = email
    user.role = role
    if not verify_password(plain_password, user.password):
        user.password = hash_password(plain_password)

    session.add(user)
    session.flush()
    return user


def _seed_places_and_menu(session: Session):
    existing_place = session.exec(select(Place)).first()
    if existing_place:
        return

    places = [
        Place(
            name="The Campus Grill",
            cuisine="American",
            location="Student Centre",
            description="Burgers, fries, and comfort food near the student center.",
            rating=4.5,
            image_url="/static/img/campus-grill.jpg",
        ),
        Place(
            name="Roti Hut",
            cuisine="Caribbean",
            location="South Gate",
            description="Fresh roti, curry dishes, and local favorites.",
            rating=4.7,
            image_url="/static/img/roti-hut.jpg",
        ),
        Place(
            name="Cafe Mocha",
            cuisine="Coffee and Pastries",
            location="Library Building",
            description="Coffee, pastries, and quick breakfast options.",
            rating=4.3,
            image_url="/static/img/cafe-mocha.jpg",
        ),
        Place(
            name="Dragon Wok",
            cuisine="Chinese",
            location="Engineering Block",
            description="Wok-fried noodles, rice bowls, and lunch specials.",
            rating=4.1,
            image_url="/static/img/dragon-wok.jpg",
        ),
        Place(
            name="Pizza Planet",
            cuisine="Italian",
            location="North Plaza",
            description="Pizza slices, pasta bowls, and garlic bread.",
            rating=4.6,
            image_url="/static/img/pizza-planet.jpg",
        ),
        Place(
            name="Doubles Express",
            cuisine="Street Food",
            location="Main Entrance",
            description="Street-side doubles, drinks, and quick bites.",
            rating=4.8,
            image_url="/static/img/doubles-express.jpg",
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


def _sync_place_images(session: Session):
    for place_name, image_url in PLACE_IMAGE_OVERRIDES.items():
        place = session.exec(select(Place).where(Place.name == place_name)).first()
        if place is None:
            continue
        place.image_url = image_url
        session.add(place)


def _sync_place_details(session: Session):
    for place_name, details in PLACE_DETAILS_OVERRIDES.items():
        place = session.exec(select(Place).where(Place.name == place_name)).first()
        if place is None:
            continue

        # If location was incorrectly copied from description during migration, restore it.
        if place.location.strip() == place.description.strip():
            place.location = details["location"]

        if not place.description.strip():
            place.description = details["description"]

        session.add(place)


def _seed_reviews(session: Session, bob: User, student: User):
    existing_review = session.exec(select(Review)).first()
    if existing_review:
        return

    places = session.exec(select(Place)).all()
    if len(places) < 3:
        return

    reviews = [
        Review(
            rating=5,
            comment="Fast service and great flavor.",
            user_id=bob.id,
            place_id=places[1].id,
        ),
        Review(
            rating=4,
            comment="Good food and fair prices.",
            user_id=student.id,
            place_id=places[0].id,
        ),
        Review(
            rating=5,
            comment="Best doubles on campus.",
            user_id=bob.id,
            place_id=places[5].id,
        ),
    ]
    session.add_all(reviews)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate_user_table_if_needed()
    _migrate_place_table_if_needed()

    with Session(engine) as session:
        bob = _ensure_user(
            session,
            username="bob",
            email="bob@campuseats.com",
            plain_password="bobpass",
            role="user",
        )
        _ensure_user(
            session,
            username="manager",
            email="manager@campuseats.com",
            plain_password="managerpass",
            role="management",
        )
        student = _ensure_user(
            session,
            username="ava",
            email="ava@campuseats.com",
            plain_password="password123",
            role="user",
        )

        _seed_places_and_menu(session)
        _sync_place_details(session)
        _sync_place_images(session)
        _seed_reviews(session, bob=bob, student=student)
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
