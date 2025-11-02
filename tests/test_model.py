import pytest
from sqlmodel import Session, SQLModel, create_engine

from pybites_cohort.models import Snippet


@pytest.fixture
def engine(scope="function"):
    return create_engine("sqlite:///:memory:", echo=True)


@pytest.fixture(scope="function", autouse=True)
def setup_database(engine):
    SQLModel.metadata.create_all(engine)
    yield


def test_create_snippet(engine):
    snippet = Snippet(title="Test Snippet", code="print('Hello, World!')")
    with Session(engine) as session:
        session.add(snippet)
        session.commit()
        session.refresh(snippet)

    assert snippet.id is not None
    assert snippet.title == "Test Snippet"
    assert snippet.code == "print('Hello, World!')"


def test_create_snippet_with_cls_method(engine):
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
