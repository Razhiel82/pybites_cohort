import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from pybites_cohort.cli import DBSnippetRepo
from pybites_cohort.exceptions import SnippetNotFoundError

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
def test_add(repo):
    added = []
    for snippet in example_snippets:
        repo.add(snippet)
        added.append(snippet)
    assert len(added) == len(example_snippets)


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_list_snippets(repo, add_snippets):
    snippets = repo.list("--favorite")
    assert len(snippets) == 1


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_list_snippets_favorites(repo, add_snippets):
    snippets = repo.list()
    assert len(snippets) == len(add_snippets)


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_get(repo, add_snippet):
    snippet = add_snippet
    print(snippet)
    assert snippet is not None
    fetched = repo.get(snippet.id)
    assert fetched.id == snippet.id


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_get_non_existing(repo):
    not_existing_id = 99
    snippet = repo.get(99)
    with pytest.raises(SnippetNotFoundError):
        if snippet is None:
            raise SnippetNotFoundError(f"Snippet with id {not_existing_id} not found")


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_delete(repo, add_snippet):
    snippet = add_snippet
    assert snippet is not None
    repo.delete(snippet.id)
    assert repo.get(snippet.id) is None


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_delete_non_existing(repo):
    not_existing_id = 99
    with pytest.raises(SnippetNotFoundError):
        repo.delete(not_existing_id)


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_search(repo, add_snippets):
    snippets = repo.search("Hello")
    assert len(snippets) == 3
    snippets_python = repo.search("Hello", language=Language.python)
    assert len(snippets_python) == 1
    snippets_rust = repo.search("hello", language=Language.rust)
    assert len(snippets_rust) == 1
    snippets_golang = repo.search("Hello", language=Language.golang)
    assert len(snippets_golang) == 1


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_fav_on_off(repo, add_snippet):
    snippet = add_snippet
    assert snippet is not None
    repo.favorite_on(snippet.id)
    fetched = repo.get(snippet.id)
    assert fetched.favorite is True
    repo.favorite_off(snippet.id)
    fetched = repo.get(snippet.id)
    assert fetched.favorite is False


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_fav_on_non_existing(repo):
    not_existing_id = 99
    with pytest.raises(SnippetNotFoundError):
        repo.favorite_on(not_existing_id)


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_fav_off_non_existing(repo):
    not_existing_id = 99
    with pytest.raises(SnippetNotFoundError):
        repo.favorite_off(not_existing_id)


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_tag_add_remove(repo, add_snippet):
    snippet = add_snippet
    assert snippet is not None
    repo.tag(snippet.id, "tag1", "tag2")
    fetched = repo.get(snippet.id)
    assert sorted(tag.name for tag in fetched.tags) == ["tag1", "tag2"]
    repo.tag(snippet.id, "tag1", remove=True)
    fetched = repo.get(snippet.id)
    assert sorted(tag.name for tag in fetched.tags) == ["tag2"]


@pytest.mark.parametrize("repo", [DBSnippetRepo], indirect=True)
def test_tag_non_existing(repo):
    not_existing_id = 99
    with pytest.raises(SnippetNotFoundError):
        repo.tag(not_existing_id, "tag1")
