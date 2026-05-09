from .db import get_db_connection
import re


class SQLService:

    @staticmethod
    def clean_sql(query):

        # Remove markdown
        query = query.replace("```sql", "")
        query = query.replace("```", "")

        return query.strip()

    @staticmethod
    def validate_query(query):

        blocked_keywords = [
            "DELETE",
            "DROP",
            "UPDATE",
            "INSERT",
            "ALTER",
            "TRUNCATE"
        ]

        upper_query = query.upper()

        for keyword in blocked_keywords:
            if keyword in upper_query:
                raise Exception(
                    "Dangerous query detected."
                )

    @staticmethod
    def execute_query(query):

        query = SQLService.clean_sql(query)

        SQLService.validate_query(query)

        conn = get_db_connection()

        cursor = conn.cursor(dictionary=True)

        cursor.execute(query)

        results = cursor.fetchall()

        conn.close()

        return results