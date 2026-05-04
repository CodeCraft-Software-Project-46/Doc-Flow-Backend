import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    mysql_connector = __import__("mysql.connector", fromlist=["connector"])
    return mysql_connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


# We manually connect to MySQL because:

# ✔ no Django models
# ✔ direct table access
# ✔ flexible for testing