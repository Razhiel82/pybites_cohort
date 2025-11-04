import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from pybites_cohort.models import Snippet


@pytest.fixture
def engine(scope="function"):
    return create_engine("sqlite:///:memory:", echo=True)


@pytest.fixture(scope="function", autouse=True)
def setup_database(engine):
    SQLModel.metadata.create_all(engine)
    yield


def test_list_favorite_snippets(engine):
    snippets = [
        Snippet(
            title="Snippet 1",
            code="print('Snippet 1')",
            description="First snippet",
            favorite=True,
        ),
        Snippet(
            title="Snippet 2",
            code="print('Snippet 2')",
            description="Second snippet",
            favorite=False,
        ),
        Snippet(
            title="Snippet 3",
            code="print('Snippet 3')",
            description="Third snippet",
            favorite=True,
        ),
    ]
    with Session(engine) as session:
        session.add_all(snippets)
        session.commit()

    with Session(engine) as session:
        favorite_snippets = session.exec(
            select(Snippet).where(Snippet.favorite is True)
        ).all()

    assert len(favorite_snippets) == 2
    assert all(snippet.favorite for snippet in favorite_snippets)


def test_create_snippet(engine):
    snippet = Snippet(
        title="Test Snippet",
        code="print('Hello, World!')",
        description="A test snippet",
        favorite=True,
    )
    with Session(engine) as session:
        session.add(snippet)
        session.commit()
        session.refresh(snippet)

    assert snippet.id is not None
    assert snippet.title == "Test Snippet"
    assert snippet.code == "print('Hello, World!')"
    assert snippet.description == "A test snippet"
    assert snippet.favorite is True
    snippet.favorite = False
    assert snippet.favorite is False


def test_create_snippet_with_cls_method(engine):
    snippet = {
        "title": "Test Snippet with Class Method",
        "description": "A test snippet created using class method",
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
