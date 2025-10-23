import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.pybites_cohort.models import Snippet

engine = create_engine("sqlite:///memory:", echo=True)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    SQLModel.metadata.create_all(engine)


def test_create_snippet():
    snippet = Snippet(title="Test Snippet", code="print('Hello, World!')")
    with Session(engine) as session:
        session.add(snippet)
        session.commit()
        session.refresh(snippet)

    assert snippet.id is not None
    assert snippet.title == "Test Snippet"
    assert snippet.code == "print('Hello, World!')"


def test_create_snippet_with_cls_method():
    snippet = {
        "title": "Test Snippet with Class Method",
        "code": "print('Hello, World!')",
    }
    snippet = Snippet.create(**snippet)
    with Session(engine) as session:
        session.add(snippet)
        session.commit()
        session.refresh(snippet)

    assert snippet.id is not None
    assert snippet.title == "Test Snippet with Class Method"
    assert snippet.code == "print('Hello, World!')"
