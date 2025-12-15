from pathlib import Path

import pytest
from decouple import Config, RepositoryEnv
from sqlmodel import Session, SQLModel, create_engine, text
from sqlmodel.pool import StaticPool

from snipster_tui.models import Language, Snippet
from snipster_tui.tui import DBSnippetRepo, Snipster

TEST_PROJECT_HOME = Path.home() / ".test_snipster_tui"
TEST_DB_PATH = TEST_PROJECT_HOME / "test_snipster_tui.sqlite"
TEST_ENV_PATH = TEST_PROJECT_HOME / ".env"


TEST_PROJECT_HOME = Path.home() / ".test_snipster_tui"
TEST_DB_PATH = TEST_PROJECT_HOME / "test_snipster_tui.sqlite"
TEST_ENV_PATH = TEST_PROJECT_HOME / ".env"


@pytest.fixture(scope="session", params=["memory", "file"])
def engine(request):
    if request.param == "memory":
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:
        TEST_PROJECT_HOME.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            f"sqlite:///{TEST_DB_PATH}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def tui_config(request, monkeypatch, engine):
    """Isolierte TUI-Config pro Testfunktion, aber shared engine."""
    # Engine-Typ bestimmen
    url = str(engine.url)
    if ":memory:" in url:
        db_url = "sqlite:///:memory:"
    else:
        db_url = f"sqlite:///{TEST_DB_PATH}"

    TEST_PROJECT_HOME.mkdir(parents=True, exist_ok=True)
    TEST_ENV_PATH.write_text(f"DATABASE_URL={db_url}\n")

    def mock_get_session():
        return Session(engine, expire_on_commit=False)

    def mock_ensure_env_file():
        return Config(RepositoryEnv(TEST_ENV_PATH)), None

    monkeypatch.setattr("snipster_tui.tui.ENV_PATH", TEST_ENV_PATH)
    monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
    monkeypatch.setattr("snipster_tui.tui.ensure_env_file", mock_ensure_env_file)
    monkeypatch.setattr("snipster_tui.tui.DATABASE_URL_MOD", db_url)

    import importlib

    import snipster_tui.tui

    importlib.reload(snipster_tui.tui)

    yield

    importlib.reload(snipster_tui.tui)


@pytest.fixture(scope="session")
def session(engine):
    """Session mit gleichem Scope wie engine"""
    with Session(engine, expire_on_commit=False) as session:
        if "test_sqlite.db" in str(engine.url):
            # IGNORE-Error if tables missing
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
            code="def main():\n    print('Hello, World!')",
            description="A simple Python hello world snippet",
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
            title="Hello World of Java",
            code='function main() {\n\tconsole.log("Hello, World!");\n}',
            description="A simple Java hello world snippet",
            language=Language.javascript,
        ),
        Snippet(
            title="Hello World of PowerShell",
            code='Write-Output "Hello, World!"',
            description="A simple PowerShell hello world snippet",
            language=Language.powershell,
        ),
        Snippet(
            title="Hello World of Bash",
            code='echo "Hello, World!"',
            description="A simple Bash hello world snippet",
            language=Language.bash,
        ),
        Snippet(
            title="Hello World of SQL",
            code='SELECT * FROM snippets WHERE title = "Hello World";',
            description="A simple SQL hello world snippet",
            language=Language.sql,
        ),
        Snippet(
            title="Hello World of Other",
            code='cout << "Hello, World!" << endl;',
            description="A simple hello world snippet in some other language",
            language=Language.other,
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


@pytest.mark.parametrize("engine", ["memory", "file"], indirect=True)
def test_add_and_list_snippets(engine, repo, example_snippets, tui_config):
    """Snippets hinzufügen und listen"""
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
def test_list_snippets_ui(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_code_view_py(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_code_view_rust(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_code_view_go(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_code_view_javascript(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_code_view_powershell(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_code_view_bash(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_code_view_sql(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_code_view_other(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_code_view_copy(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_delete(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("d")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_list_favorite(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("f")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_list_snippets_ui_list_edit(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    """List Snippets → DataTable mit Testdaten (SVG-Snapshot!)"""

    def mock_get_session():
        return repo.session

    async def click_list(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("e")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_list)


def test_add_snippet_ui(snap_compare):
    async def click_add(pilot):
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_add)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_delete_snippet_ui(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    def mock_get_session():
        return repo.session

    async def click_delete(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("5")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_delete)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_delete_invalid_snippet_ui(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    def mock_get_session():
        return repo.session

    async def click_delete(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_delete)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_delete_snippet_ui_fields(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    def mock_get_session():
        return repo.session

    async def click_delete_fields(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")

        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_delete_fields)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_init_snippet_ui_fields(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    def mock_get_session():
        return repo.session

    async def click_init_fields(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_init_fields)


@pytest.mark.parametrize("engine", ["memory"], indirect=True)
def test_init_snippet_ui_default(
    engine, repo, example_snippets, snap_compare, monkeypatch, tui_config
):
    def mock_get_session():
        return repo.session

    async def click_init_defaults(pilot):
        monkeypatch.setattr("snipster_tui.tui.get_session", mock_get_session)
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.pause()

    assert snap_compare(Snipster(), run_before=click_init_defaults)
