from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime

Base = declarative_base()


class URLMap(Base):
    __tablename__ = "url_map"

    id = Column(Integer, primary_key=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    target = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

