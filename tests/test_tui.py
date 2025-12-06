import pytest
from sqlmodel import Session, SQLModel, create_engine, text
from sqlmodel.pool import StaticPool

from snipster_tui.models import Language, Snippet
from snipster_tui.tui import DBSnippetRepo, Snipster


@pytest.fixture(params=["memory", "file"], scope="session")
def engine(request):  # ← EINZIGE engine Fixture!
    if request.param == "memory":
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:  # file
        engine = create_engine(
            "sqlite:///test_sqlite.db",
            connect_args={"check_same_thread": False},
            echo=False,
        )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")  # ← scope="session" statt "function"!
def session(engine):
    """Session mit gleichem Scope wie engine"""
    with Session(engine, expire_on_commit=False) as session:
        if "test_sqlite.db" in str(engine.url):
            # IGNORE-Fehler bei fehlenden Tabellen
            try:
                session.exec(text("DELETE FROM snippet_tags"))
            except Exception:
                pass
            try:
                session.exec(text("DELETE FROM tag"))
            except Exception:
                pass
            try:
                session.exec(text("DELETE FROM snippet"))
            except Exception:
                pass
        yield session


@pytest.fixture(scope="session")
def repo(session):
    yield DBSnippetRepo(session=session)


@pytest.fixture
def example_snippets():
    """Test-Snippets nach Metadata-Setup erstellen"""
    return [
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


def test_main_menu(snap_compare):
    assert snap_compare(Snipster())


@pytest.mark.parametrize("engine", ["memory", "file"], indirect=["engine"])
def test_add_and_list_snippets(engine, repo, example_snippets):
    for snippet in example_snippets:
        repo.add(snippet)
    repo.session.commit()

    listed = repo.list()
    titles = {s.title for s in listed}
    for example in example_snippets:
        assert example.title in titles
    favorite_titles = {s.title for s in listed if s.favorite}
    assert "Favorite Snippet" in favorite_titles


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui(engine, repo, example_snippets, snap_compare, monkeypatch):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    for snippet in example_snippets:
        repo.add(snippet)
    repo.session.commit()

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


def test_add_snippet_ui(snap_compare):
    async def click_add(pilot):
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_add)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_delete_snippet_ui(engine, repo, example_snippets, snap_compare, monkeypatch):
    for snippet in example_snippets:
        repo.add(snippet)
    repo.session.commit()

    def mock_get_session():
        return repo.session

    async def click_delete(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("1")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_delete)
