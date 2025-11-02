import pytest

from pybites_cohort.exceptions import SnippetNotFoundError
from pybites_cohort.models import Language, Snippet
from pybites_cohort.repo import InMemorySnippetRepo


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
