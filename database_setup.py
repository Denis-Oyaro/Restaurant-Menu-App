from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user_table'


    name =Column(String(250), nullable = False)
    id = Column(Integer, primary_key = True)
    email = Column(String(250), nullable = False)
    picture = Column(String(250))


    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'         : self.id,
           'picture'         : self.picture,
           'email'         : self.email
       }
       
       
class Restaurant(Base):
    __tablename__ = "restaurant"
    name = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    user_id = Column(Integer,ForeignKey('user_table.id'))
    user_table = relationship(User)
    
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
    user_id = Column(Integer,ForeignKey('user_table.id'))
    user_table = relationship(User)
    
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
    engine = create_engine('postgres:///happyrestaurantwithusers')
    Base.metadata.create_all(engine)