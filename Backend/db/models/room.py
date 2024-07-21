from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from db.db_init import Base
from led_room_manager import Color


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, index=True)
    url = Column(String(100))
    is_enabled = Column(Boolean, default=True)
    desired_color = Column(String(50), default=str(Color(0,0,0,255)))
    detection_time = Column(Integer, default=15*60)  # in seconds
    min_adc = Column(Integer, default=0)
    max_adc = Column(Integer, default=65535)
    house = relationship("House", back_populates="rooms")
    house_id = Column(Integer, ForeignKey("houses.id"))
