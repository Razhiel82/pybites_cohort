import os

from dotenv import load_dotenv
from sqlmodel import Field, Session, SQLModel, create_engine, select

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# SQLITE_FILE_NAME = os.getenv("SQLITE_FILE_NAME")

engine = create_engine(DATABASE_URL, echo=True)


class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    price: float


SQLModel.metadata.create_all(engine)

# with Session(engine) as session:
#     item = Item(name="Laptop", price=999.99)
#     session.add(item)
#     session.commit()
#     session.refresh(item)

with Session(engine) as session:
    item = session.exec(select(Item)).all

with Session(engine) as session:
    item = session.get(Item, 1)

with Session(engine) as session:
    item = session.exec(select(Item).where(Item.name == "Laptop")).first()

with Session(engine) as session:
    item = session.get(Item, 1)
    if item:
        item.price = 899.00
        session.add(item)
        session.commit()


with Session(engine) as session:
    item = session.get(Item, 1)
    if item:
        session.delete(item)
        session.commit()
