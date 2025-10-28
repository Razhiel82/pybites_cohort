from enum import Enum

from decouple import config
from sqlmodel import Field, Session, SQLModel, create_engine, select

DATABASE_URL = config("DATABASE_URL")


class Language(str, Enum):
    python = "py"
    javascript = "js"
    rust = "rs"


class Snippet(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: int | None = Field(default=None, primary_key=True)
    title: str
    code: str

    @classmethod
    def create(cls, **kwargs):
        snippet = cls(**kwargs)
        return snippet


engine = create_engine(DATABASE_URL, echo=True)

with Session(engine) as session:
    snippet = Snippet(title="snippet 1", code="print('Snippet 1')")
    session.add(snippet)
    session.commit()
    session.refresh(snippet)

with Session(engine) as session:
    snippet = session.exec(select(Snippet)).all()

with Session(engine) as session:
    snippet = session.get(Snippet, 1)

with Session(engine) as session:
    snippet = session.exec(select(Snippet).where(Snippet.title == "Laptop")).first()

with Session(engine) as session:
    snippet = session.get(Snippet, 1)
    if snippet:
        snippet.code = "print('Snippet 1')"
        session.add(snippet)
        session.commit()

with Session(engine) as session:
    snippet = session.get(Snippet, 1)
    if snippet:
        session.delete(snippet)
        session.commit()

if __name__ == "__main__":  # pragma: no cover
    SQLModel.metadata.create_all(engine)
    print("Database + table created!")
