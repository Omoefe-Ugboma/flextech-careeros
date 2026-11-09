
from sqlalchemy import text
from app.core.database import engine


def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database()")
        )

        database_name = result.scalar_one()

        assert database_name == "careeros_db"

        print(f"Connected successfully to: {database_name}")


if __name__ == "__main__":
    test_database_connection()
