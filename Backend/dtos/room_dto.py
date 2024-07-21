from pydantic import BaseModel
from sqlalchemy.orm import relationship


class RoomCreateDTO(BaseModel):
    name: str
    url: str
    is_enabled: bool
    desired_color: str
    detection_time: int
    min_adc: int
    max_adc: int
    house_id: int

    class Config:
        orm_mode = True


class RoomUpdateDTO(RoomCreateDTO):
    class Config:
        orm_mode = True


class RoomDTO(RoomUpdateDTO):
    id: int
    class Config:
        orm_mode = True
