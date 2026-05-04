from .db import get_db_connection

# 1. Get document info
def get_document(doc_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT id, title, status, summary
        FROM documents
        WHERE id = %s
    """

    cursor.execute(query, (doc_id,))
    result = cursor.fetchone()

    conn.close()
    return result


# 2. Get responsible person
def get_task(doc_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT assigned_user, status
        FROM workflows_taskinstance
        WHERE document_id = %s
    """

    cursor.execute(query, (doc_id,))
    result = cursor.fetchone()

    conn.close()
    return result