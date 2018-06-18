from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class Restaurant(Base):
    __tablename__ = "restaurant"
    name = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)   
    
    @property
    def serialize(self):
        return {
            "id" : self.id,
            "name" : self.name,
        }

class MenuItem(Base):
    __tablename__ = "menu_item"
    name = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    course = Column(String(500))
    description = Column(String(500))
    price = Column(String(8))
    restaurant_id = Column(Integer, ForeignKey('restaurant.id'))
    restaurant = relationship(Restaurant)
    
    @property
    def serialize(self):
        return {
            "course" : self.course,
            "description" : self.description,
            "id" : self.id,
            "name" : self.name,
            "price" : self.price
        }
    
if __name__ == "__main__":
    engine = create_engine('postgres:///happyrestaurant')
    Base.metadata.create_all(engine)