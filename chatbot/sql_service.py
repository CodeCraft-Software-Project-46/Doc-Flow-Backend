from .db import get_db_connection
import re


class SQLService:

    @staticmethod
    def clean_sql(query):

        # Remove markdown
        query = re.sub(r"```sql", "", query, flags=re.IGNORECASE)
        query = re.sub(r"```", "", query)

        # Remove semicolon
        query = query.replace(";", "")

        # Remove extra spaces/newlines
        query = query.strip()

        return query

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
                raise Exception("Dangerous query detected.")

        # Allow only SELECT
        if not upper_query.startswith("SELECT"):
            raise Exception("Only SELECT queries are allowed.")

    @staticmethod
    def enforce_case_insensitive(query):

        # convert = comparisons into LOWER LIKE LOWER
        patterns = [
            r"(\w+)\s*=\s*'([^']+)'"
        ]

        for pattern in patterns:
            matches = re.findall(pattern, query)

            for column, value in matches:
                replacement = (
                    f"LOWER({column}) LIKE LOWER('%{value}%')"
                )

                original = f"{column} = '{value}'"

                query = query.replace(original, replacement)

        return query

    @staticmethod
    def execute_query(query):

        query = SQLService.clean_sql(query)

        query = SQLService.enforce_case_insensitive(query)

        SQLService.validate_query(query)

        print("\nFINAL SQL:")
        print(query)

        conn = get_db_connection()

        cursor = conn.cursor(dictionary=True)

        cursor.execute(query)

        results = cursor.fetchall()

        conn.close()

        return results