from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker as _sessionmaker

Base = declarative_base()


class URLMap(Base):
    __tablename__ = "url_map"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    target = Column(Text, nullable=False)


# Expose a sessionmaker factory symbol expected by `main.py`
sessionmaker = _sessionmaker
