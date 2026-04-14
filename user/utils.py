from django.db import connection

def generate_role_id():
    with connection.cursor() as cursor:
        cursor.execute("SELECT id FROM workflows_role ORDER BY created_at DESC LIMIT 1")
        last_id = cursor.fetchone()

        if last_id and last_id[0].startswith('R'):
            try:
                current_no = int(last_id[0][1:])
                new_no = current_no + 1
                return f"R{str(new_no).zfill(3)}"
            except ValueError:
                return "R001"

        return "R001"