from sqlmodel import SQLModel, Session, create_engine, select

from app.auth import hash_password
from app.models import MenuItem, Place, Review, User

engine = create_engine("sqlite:///database.db", echo=True)


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

        connection.exec_driver_sql(
            'CREATE UNIQUE INDEX IF NOT EXISTS ix_user_username ON "user" (username)'
        )
        connection.exec_driver_sql(
            'CREATE UNIQUE INDEX IF NOT EXISTS ix_user_email ON "user" (email)'
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

        if "description" in columns:
            connection.exec_driver_sql(
                'UPDATE "place" SET location = description '
                'WHERE location = "" AND description IS NOT NULL'
            )


def seed_places(session: Session):
    existing_place = session.exec(select(Place)).first()
    if existing_place:
        return

    places = [
        Place(
            name="The Campus Grill",
            cuisine="American",
            location="Student Centre",
            rating=4.5,
            image_url="/static/img/placeholder.svg",
        ),
        Place(
            name="Roti Hut",
            cuisine="Caribbean",
            location="South Gate",
            rating=4.7,
            image_url="/static/img/placeholder.svg",
        ),
        Place(
            name="Cafe Mocha",
            cuisine="Coffee and Pastries",
            location="Library Building",
            rating=4.3,
            image_url="/static/img/placeholder.svg",
        ),
        Place(
            name="Dragon Wok",
            cuisine="Chinese",
            location="Engineering Block",
            rating=4.1,
            image_url="/static/img/placeholder.svg",
        ),
        Place(
            name="Pizza Planet",
            cuisine="Italian",
            location="North Plaza",
            rating=4.6,
            image_url="/static/img/placeholder.svg",
        ),
        Place(
            name="Doubles Express",
            cuisine="Street Food",
            location="Main Entrance",
            rating=4.8,
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

    users = []
    user_data = [
        ("bob", "bob@campuseats.com", "bobpass"),
        ("ava", "ava@campuseats.com", "password123"),
        ("mia", "mia@campuseats.com", "password123"),
    ]
    for username, email, password in user_data:
        existing_user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if existing_user:
            users.append(existing_user)
            continue

        new_user = User(
            username=username,
            email=email,
            password=hash_password(password),
        )
        session.add(new_user)
        session.flush()
        users.append(new_user)

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
    ]
    session.add_all(reviews)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    _migrate_user_table_if_needed()
    _migrate_place_table_if_needed()

    with Session(engine) as session:
        seed_places(session)
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
