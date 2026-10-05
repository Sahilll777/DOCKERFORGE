import os

import psycopg


DATABASE_URL = os.environ["DATABASE_URL"]


def check_database_connection():
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            return cursor.fetchone()


def get_cache_demo_data():
    with psycopg.connect(DATABASE_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    CURRENT_TIMESTAMP
                """
            )

            database, user, generated_at = cursor.fetchone()

            return {
                "database": database,
                "user": user,
                "generated_at": generated_at.isoformat(),
            }
