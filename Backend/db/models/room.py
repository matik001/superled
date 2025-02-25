import enum

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from db.db_init import Base
from sqlalchemy import Integer, Enum

class ColorType(enum.Enum):
    WRGB_BLEXBOX = 1
    CCT_BLEBOX = 2
    WRGB_BLEXBOX_WITH_CLOSET = 3


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, index=True)
    url = Column(String(100))
    is_enabled = Column(Boolean, default=True)
    desired_color = Column(String(50))
    detection_time = Column(Integer, default=15*60)  # in seconds
    min_adc = Column(Integer, default=0)
    max_adc = Column(Integer, default=65535)
    closet_brightness = Column(Integer, default=0)
    type = Column(Enum(ColorType), default=ColorType.WRGB_BLEXBOX)
    use_motion_detector = Column(Boolean, default=False)
    house = relationship("House", back_populates="rooms")
    house_id = Column(Integer, ForeignKey("houses.id"))
