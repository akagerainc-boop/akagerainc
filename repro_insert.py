from database import SessionLocal
from models import Image
from datetime import datetime

session = SessionLocal()
try:
    img = Image(
        data=b'abc',
        filename='test.png',
        mime_type='image/png',
        alt_text='test',
        page_type='home',
        order=0,
        is_active=True,
    )
    session.add(img)
    session.commit()
    print('INSERT_OK', img.id)
except Exception as e:
    print('ERROR', repr(e))
    session.rollback()
finally:
    session.close()
