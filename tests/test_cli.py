import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from pybites_cohort.cli import DBSnippetRepo

# from pybites_cohort.exceptions import SnippetNotFoundError
from pybites_cohort.models import Language, Snippet

example_snippets = [
    Snippet(
        title="Hello python",
        code="print('Hello, World! 1')",
        description="A simple hello world snippet",
        language=Language.python,
    ),
    Snippet(
        title="Hello rust",
        code='fn main() { \n\tprintln!("Hello World!");\n}  ',
        description="A simple Rust hello world snippet",
        language=Language.rust,
    ),
    Snippet(
        title="Hello World of golang",
        code='package main\n\nimport "fmt"\n\nfunc main() {\n\tfmt.Println("Hello World!")\n}',
        description="A simple Go hello world snippet",
        language=Language.golang,
    ),
    Snippet(
        title="Favorite Snippet",
        code="print('Hello, Favorit World!')",
        description="Favorit hello world snippet!!",
        language=Language.python,
        favorite=True,
    ),
]


@pytest.fixture(scope="function")
def add_snippet(repo):
    snippet = Snippet(
        title="Hello World",
        code="print('Hello, World! 1')",
        description="A simple hello world snippet",
        language=Language.python,
    )
    repo.add(snippet)
    return snippet


@pytest.fixture(scope="function")
def add_snippets(repo):
    added = []
    for snippet in example_snippets:
        repo.add(snippet)
        added.append(snippet)
    return added


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture(scope="function")
def repo(request, session):
    repo_class = request.param
    if repo_class is DBSnippetRepo:
        yield DBSnippetRepo(session=session)
    else:
        raise ValueError(f"Unknown repo class: {repo_class}")


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def add(repo):
    added = []
    for snippet in example_snippets:
        repo.add(snippet)
        added.append(snippet)
    assert len(added) == len(example_snippets)
    return added


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def list_snippets(repo, add_snippets):
    snippets = repo.list()
    assert len(snippets) == len(add_snippets) + 1
    return snippets


@pytest.fixture(scope="function")
def get(repo, add_snippet, DBSnippetRepo):
    snippet = add_snippet[1]
    assert snippet is not None
    fetched = repo.get(snippet.id)
    assert fetched.id == snippet.id
    return fetched
