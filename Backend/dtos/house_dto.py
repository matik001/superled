from pydantic import BaseModel
from sqlalchemy.orm import relationship


class HouseCreateDTO(BaseModel):
    id: int
    name: str
    description: str



    class Config:
        orm_mode = True


class HouseUpdateDTO(HouseCreateDTO):
    class Config:
        orm_mode = True


class HouseDTO(HouseUpdateDTO):
    id: int
    class Config:
        orm_mode = True
