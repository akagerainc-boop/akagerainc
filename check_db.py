import os
from database import engine
from sqlalchemy import text

print('DB_URL', os.getenv('DATABASE_URL'))
conn = engine.connect()
print('CONNECTED')
print(conn.execute(text('SHOW TABLES LIKE "images"')).fetchall())
conn.close()
