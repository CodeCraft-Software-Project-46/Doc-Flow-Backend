import os
import django
import pymysql

# Correct Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django.setup()

from django.conf import settings

# Connect to AWS MySQL DB
conn = pymysql.connect(
    host=settings.DATABASES['default']['HOST'],
    user=settings.DATABASES['default']['USER'],
    password=settings.DATABASES['default']['PASSWORD'],
    database=settings.DATABASES['default']['NAME'],
    port=int(settings.DATABASES['default']['PORT']),
)

cur = conn.cursor()

# Drop all tables dynamically
cur.execute("SET FOREIGN_KEY_CHECKS = 0;")
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s;", (settings.DATABASES['default']['NAME'],))
tables = cur.fetchall()

for table in tables:
    cur.execute(f"DROP TABLE IF EXISTS `{table[0]}`;")

cur.execute("SET FOREIGN_KEY_CHECKS = 1;")
conn.commit()
cur.close()
conn.close()

print("✅ All tables dropped successfully!")