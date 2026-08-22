from django.db import connection


def run_select_query(query):
    """Executes a SELECT query through Django's own database connection
    (config.settings.DATABASES) instead of a second, separate mysql.connector
    connection. This reuses Django's connection pooling (CONN_MAX_AGE) and,
    critically, its DNS-fallback handling for the RDS host -- the previous
    raw mysql.connector.connect(host=os.getenv("DB_HOST"), ...) had no such
    fallback, so a transient DNS hiccup for the RDS hostname broke every
    chatbot query while the rest of the app (which goes through Django's
    connection) kept working."""
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
