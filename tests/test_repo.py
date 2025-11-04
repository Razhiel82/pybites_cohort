import pytest

from pybites_cohort.exceptions import SnippetNotFoundError
from pybites_cohort.models import Language, Snippet
from pybites_cohort.repo import InMemorySnippetRepo

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
    for snippet in example_snippets:
        repo.add(snippet)
    return snippet


@pytest.fixture(scope="function")
def repo():
    return InMemorySnippetRepo()


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
        code="print('Hello, World! 2')",
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

    assert 3 in repo._data


def test_list_retuns_inserted_snippets(add_snippet, add_second_snippet, repo):
    snippets = repo.list()
    assert snippets[0] == add_snippet
    assert snippets[1] == add_second_snippet


def test_add_snippet(add_snippet, repo):
    assert repo._data[1] == add_snippet


def test_list_one_snippet(add_snippet, repo):
    assert len(repo.list()) == 1


def test_list_two_snippets(add_snippet, add_second_snippet, repo):
    assert len(repo.list()) == 2


def test_get_snippet(add_snippet, repo):
    assert repo.get(1) == add_snippet


def test_get_snippet_not_found(add_snippet, repo):
    assert repo.get(99) is None


def test_delete_snippet(add_snippet, repo):
    repo.delete(1)
    assert repo._data.get(1) is None


def test_delete_non_existing_snippet(repo):
    with pytest.raises(SnippetNotFoundError):
        repo.delete(99)


def test_favorite_snippet_on(add_snippet, repo):
    snippet = repo.list()
    assert repo._data[1] == add_snippet
    assert len(snippet) == 1
    repo.favorite_on(1)
    assert snippet[0].favorite is True


def test_favorite_snippet_off(add_favorite_snippet, repo):
    snippet = repo.list()
    assert repo._data[1] == add_favorite_snippet
    assert len(snippet) == 1
    repo.favorite_off(1)
    assert snippet[0].favorite is False


def test_search_snippets(add_snippets, repo):
    assert len(repo.search("Hello python")) == 1
    assert len(repo.search("hello pytHON")) == 1
    assert len(repo.search("Hello rust")) == 1
    assert len(repo.search("notfound")) == 0
    assert len(repo.search("Hello")) == 3
    # assert len(repo.search("Hello", language=Language.python)) == 1


def test_add_snippets(add_snippets, repo):
    assert len(repo.list()) == 4
