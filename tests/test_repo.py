import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from pybites_cohort.exceptions import SnippetNotFoundError
from pybites_cohort.models import Language, Snippet
from pybites_cohort.repo import DBSnippetRepo, InMemorySnippetRepo

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
    elif repo_class is InMemorySnippetRepo:
        yield InMemorySnippetRepo()
    else:
        raise ValueError(f"Unknown repo class: {repo_class}")


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
def add_second_snippet(repo):
    snippet = Snippet(
        title="Hello World",
        code='fn main() { \n\tprintln!("Hello World!");\n}  ',
        description="A simple hello world snippet",
        language=Language.rust,
    )
    repo.add(snippet)
    return snippet


@pytest.fixture(scope="function")
def add_third_snippet(repo):
    snippet = Snippet(
        title="Hello World",
        code="print('Hello, World! 3')",
        description="A simple hello world snippet",
        language=Language.rust,
    )
    repo.add(snippet)
    return snippet


@pytest.fixture(scope="function")
def add_favorite_snippet(repo):
    snippet = Snippet(
        title="Favorite Snippet",
        code="print('Hello, Favorit World!')",
        description="Favorit hello world snippet!!",
        language=Language.python,
        favorite=True,
    )
    repo.add(snippet)
    return snippet


@pytest.fixture(scope="function")
def delete_first_snippet(repo):
    repo.delete(1)


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_and_assign_incremeting_ids(
    add_snippet, add_second_snippet, delete_first_snippet, add_third_snippet, repo
):
    snippet3 = Snippet(
        title="Hello World",
        code="print('Hello, World! 3')",
        description="A simple hello world snippet",
        language=Language.golang,
    )
    repo.add(snippet3)

    snippets = repo.list()
    assert len(snippets) == 3
    ids = [s.id for s in snippets]
    assert snippet3.id in ids


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_list_retuns_inserted_snippets(add_snippet, add_second_snippet, repo):
    snippets = repo.list()
    if isinstance(repo, InMemorySnippetRepo):
        assert snippets[0] == add_snippet
        assert snippets[1] == add_second_snippet
    elif isinstance(repo, DBSnippetRepo):
        assert snippets[0] == add_snippet
        assert snippets[1] == add_second_snippet


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_add_snippet(add_snippet, repo):
    if isinstance(repo, InMemorySnippetRepo):
        assert repo._data[1] == add_snippet
    elif isinstance(repo, DBSnippetRepo):
        snippet = repo.get(1)
        assert snippet == add_snippet


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_list_one_snippet(add_snippet, repo):
    assert len(repo.list()) == 1


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_list_two_snippets(add_snippet, add_second_snippet, repo):
    assert len(repo.list()) == 2


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_get_snippet(add_snippet, repo):
    assert repo.get(1) == add_snippet


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_get_snippet_not_found(add_snippet, repo):
    assert repo.get(99) is None


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_delete_snippet(add_snippet, repo):
    repo.delete(1)
    if isinstance(repo, InMemorySnippetRepo):
        assert repo._data.get(1) is None
    elif isinstance(repo, DBSnippetRepo):
        assert repo.get(1) is None


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_delete_non_existing_snippet(repo):
    with pytest.raises(SnippetNotFoundError):
        repo.delete(99)


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_favorite_snippet_on(add_snippet, repo):
    snippet = repo.list()
    if isinstance(repo, InMemorySnippetRepo):
        assert repo._data[1] == add_snippet
        assert len(snippet) == 1
        repo.favorite_on(1)
        assert snippet[0].favorite is True
    elif isinstance(repo, DBSnippetRepo):
        assert repo.get(1) == add_snippet
        assert len(snippet) == 1
        repo.favorite_on(1)
        assert snippet[0].favorite is True


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_favorite_snippet_off(add_favorite_snippet, repo):
    snippet = repo.list()
    if isinstance(repo, InMemorySnippetRepo):
        assert repo._data[1] == add_favorite_snippet
        assert len(snippet) == 1
        repo.favorite_off(1)
        assert snippet[0].favorite is False
    elif isinstance(repo, DBSnippetRepo):
        assert repo.get(1) == add_favorite_snippet
        assert len(snippet) == 1
        repo.favorite_off(1)
        assert snippet[0].favorite is False


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_favorite_snippet_on_non_existing(repo):
    if isinstance(repo, InMemorySnippetRepo):
        with pytest.raises(SnippetNotFoundError):
            repo.favorite_on(99)
    elif isinstance(repo, DBSnippetRepo):
        with pytest.raises(SnippetNotFoundError):
            repo.favorite_on(99)


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_favorite_snippet_off_non_existing(repo):
    with pytest.raises(SnippetNotFoundError):
        repo.favorite_off(99)


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_search_snippets(add_snippets, repo):
    assert len(repo.search("Hello python")) == 1
    assert len(repo.search("hello pytHON")) == 1
    assert len(repo.search("Hello rust")) == 1
    assert len(repo.search("notfound")) == 0
    assert len(repo.search("Hello")) == 3
    assert len(repo.search("Hello", language=Language.python)) == 1


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_add_snippets(add_snippets, repo):
    snippets_in_repo = repo.list()
    assert len(snippets_in_repo) == len(add_snippets)


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_tag_snippet(add_snippets, repo):
    repo.tag(1, "test1", "test2")
    snippet = repo.get(1)
    assert snippet is not None
    assert snippet.tag_list == ["test1", "test2"]
    repo.tag(1, "test1", remove=True)
    snippet = repo.get(1)
    assert snippet.tag_list == ["test2"]
    repo.tag(1, "test2", "test3", "test4")
    snippet = repo.get(1)
    assert snippet.tag_list == ["test2", "test3", "test4"]
    snippet = repo.get(1)
    repo.tag(1, "test2", "test3", "test3", remove=True)
    snippet = repo.get(1)
    assert snippet.tag_list == ["test4"]
    with pytest.raises(SnippetNotFoundError):
        repo.tag(99, "nonexistent", remove=True)
    repo.tag(1, "test5", "test4", "test3", sort=True)
    snippet = repo.get(1)
    assert snippet.tag_list == ["test3", "test4", "test5"]
    # Add multiple tags and sort


@pytest.mark.parametrize("repo", [InMemorySnippetRepo, DBSnippetRepo], indirect=True)
def test_list_favorite_snippets(repo, add_snippets):
    favorite_snippets = repo.list_favorites()
    expected_favorites = [s for s in add_snippets if getattr(s, "favorite", False)]
    assert len(favorite_snippets) == len(expected_favorites)
    assert all(s.favorite for s in favorite_snippets)
