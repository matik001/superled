from typing import List

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Mapped

from db.db_init import Base
from db.models.room import Room


class House(Base):
    __tablename__ = "houses"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), index=True)
    description = Column(String(200))

    rooms: Mapped[List['Room']] = relationship("Room", back_populates="house")