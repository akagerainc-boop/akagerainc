import os
from database import engine
from sqlalchemy import text

print('DB_URL', os.getenv('DATABASE_URL'))
conn = engine.connect()
print('CONNECTED')
res = conn.execute(text('SHOW TABLES LIKE :name'), {'name': 'images'})
print(res.fetchall())
conn.close()
