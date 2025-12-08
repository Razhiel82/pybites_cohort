from enum import Enum
from typing import Optional

from decouple import config
from sqlmodel import (
    Field,
    Session,
    SQLModel,
    create_engine,
    select,
)


class Language(str, Enum):
    python = "py"
    javascript = "js"
    rust = "rs"
    golang = "go"


class Snippet(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    code: str
    description: str
    favorite: bool = Field(default=False)
    language: Language = Field(default=Language.python)

    @classmethod
    def create(cls, **kwargs):
        return cls(**kwargs)


if __name__ == "__main__":  # pragma: no cover
    DB_USER = config("DB_USER")
    DB_PASS = config("DB_PASS")
    DB_HOST = config("DB_HOST")
    DB_PORT = config("DB_PORT")
    DB_NAME = config("DB_NAME")

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    engine = create_engine(DATABASE_URL, echo=False)
    SQLModel.metadata.create_all(engine)

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

    print("Database + table created!")
