import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import Base
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv('DATABASE_URL')

if URL is None:
    raise ValueError('DATABASE_URL not found')

connect_args = {}
if "sslmode=verify-ca" in URL or "sslmode=require" in URL:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ca_path = os.path.join(BASE_DIR, "certs", "ca.pem")
    if os.path.exists(ca_path):
        connect_args = {
            "sslmode": "verify-ca",
            "sslrootcert": ca_path
        }

engine = create_engine(
    URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)