from pathlib import Path

from decouple import Config, RepositoryEnv
from rich.syntax import Syntax
from sqlmodel import Session, create_engine
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, OptionList, Static, TextArea
from textual.widgets.option_list import Option

from snipster_tui.exceptions import NoMatches, SnippetNotFoundError
from snipster_tui.models import Language, Snippet
from snipster_tui.repo import DBSnippetRepo

DEFAULT_PROJECT_HOME = Path.home() / ".snipster_tui"
DEFAULT_DB_PATH = DEFAULT_PROJECT_HOME / "snipster_tui.sqlite"
ENV_PATH = DEFAULT_PROJECT_HOME / ".env"


def ensure_env_file() -> tuple[Config, str | None]:
    if not ENV_PATH.exists():
        print(f"[yellow]⚠️  No .env found at {ENV_PATH}")
        DEFAULT_PROJECT_HOME.mkdir(parents=True, exist_ok=True)
        # Datei anlegen, damit open nicht crasht
        ENV_PATH.touch(exist_ok=True)
        fallback_url = f"sqlite:///{DEFAULT_DB_PATH}"
        return Config(RepositoryEnv(ENV_PATH)), fallback_url
    return Config(RepositoryEnv(ENV_PATH)), None


# EINMALIGE Config-Ladung
config_modul, fallback_url = ensure_env_file()
DATABASE_URL_MOD = fallback_url or f"sqlite:///{DEFAULT_DB_PATH}"

DB_USER_MOD = config_modul("DB_USER", default="")
DB_PASS_MOD = config_modul("DB_PASS", default="")
DB_HOST_MOD = config_modul("DB_HOST", default="localhost")
DB_PORT_MOD = config_modul("DB_PORT", default="5432")
DB_NAME_MOD = config_modul("DB_NAME", default="snipster")

# PostgreSQL URL if Postgres-config exists
if DB_USER_MOD and all([DB_PASS_MOD, DB_HOST_MOD, DB_PORT_MOD, DB_NAME_MOD]):
    DATABASE_URL_MOD = f"postgresql://{DB_USER_MOD}:{DB_PASS_MOD}@{DB_HOST_MOD}:{DB_PORT_MOD}/{DB_NAME_MOD}"


def get_session():
    return Session(create_engine(DATABASE_URL_MOD, echo=False))


class CodeViewScreen(ModalScreen[None]):
    BINDINGS = [("escape", "close_modal", "Close")]

    def action_close_modal(self) -> None:
        self.dismiss()

    DEFAULT_CSS = """
    CodeViewScreen {
        align: center middle;
    }
    CodeViewScreen > VerticalScroll {
        width: 90;
        height: 70%;
        border: round solid #444;
        background: $panel;
    }
    #code_view {
        height: 1fr;
        padding: 1;
        background: $background;
    }
    #buttons {
        height: auto;
        margin-top: 1;
    }
    Button {
        margin: 0 1;
    }
    """

    def __init__(self, snippet_id: int, code: str, title: str, language: str):
        super().__init__()  # ← ZUERST super()!
        self.snippet_id = snippet_id
        self.code = code
        self.title = title
        self.language = language or "text"

    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Static(
                f"[bold cyan]Snippet '{self.title}' (ID: {self.snippet_id})[/]",
                id="title",
            ),
            Static(
                Syntax(self.code, self.language, theme="monokai", line_numbers=True),
                id="code_view",
                expand=True,
            ),
            Horizontal(
                Button("📋 Copy Code", id="copy_btn", variant="primary"),
                Button("❌ Close", id="close_btn", variant="error"),
                id="buttons",
            ),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy_btn":
            self.app.copy_to_clipboard(self.code)
            self.notify(f"Code copied! ({len(self.code)} chars)", severity="success")
        elif event.button.id == "close_btn":
            self.dismiss()


class Snipster(App):
    CSS = """
    #content_area {
        height: 1fr;
    }

    #status {
        height: 1;
    }

    #main_menu {
        height: 3;
    }
    """
    show_add_inputs = reactive(False)
    show_delete_inputs = reactive(False)
    show_edit_inputs = reactive(False)

    async def _auto_init_config(self) -> None:
        """Async Auto-Config Start (Thread-sicher)"""
        await self.call_later(self.init_config_tui)

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Button("Add Snippet", id="add"),
            Button("List Snippets", id="list"),
            Button("Delete Snippet", id="delete"),
            # Button("Edit Snippet", id="edit"),
            Button("Exit", id="exit", variant="error"),
            Button(
                label="Init",
                id="init",
                variant="warning",
            ),
            id="main_menu",
        )
        yield Static("", id="status")
        yield Vertical(id="content_area")

        if not ENV_PATH.exists():
            self.set_interval(self.auto_init_config, 0.1, once=True)

    async def auto_init_config(self) -> None:
        """Autostart Config-TUI wenn no .env exists"""
        await self.init_config_tui()

    async def edit_snippet(self, snippet_id: int) -> None:
        """Direktes Edit aus Kontext-Menü"""
        await self.toggle_edit_snippet()
        self.call_later(self._load_snippet_direct, snippet_id)

    async def edit_selected(self) -> None:
        """Edit selected row from table"""
        table = self.query_one("#snippet_table", DataTable)
        if table.cursor_coordinate is None:
            self.notify("No row selected!", severity="warning")
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        snippet_id = int(row_key.value)
        await self.edit_snippet(snippet_id)

    async def _load_snippet_direct(self, snippet_id: int) -> None:
        """Snippet direkt laden (nach DOM-Update)"""
        edit_id_input = self.query_one("#edit_id", Input)
        if edit_id_input:
            edit_id_input.value = str(snippet_id)
            self.call_later(self.load_snippet_for_edit)

    @on(Button.Pressed, "#edit")
    async def toggle_edit_snippet(self) -> None:
        content = self.query_one("#content_area")
        self.show_edit_inputs = not self.show_edit_inputs

        if self.show_edit_inputs:
            content.remove_children()

            code_area = TextArea(
                id="edit_code", placeholder="Code (Enter für Zeilenumbruch)"
            )
            code_area.styles.height = 15

            # 🔥 EXAKT wie add_snippet() - *unpacked* Options!
            form = Vertical(
                Input(placeholder="Snippet ID", id="edit_id"),
                Button("Load Snippet", id="load_edit"),
                Static("Title:"),
                Input(placeholder="Title", id="edit_title", disabled=True),
                Static("Code:"),
                code_area,
                Static("Description:"),
                Input(placeholder="Description", id="edit_desc", disabled=True),
                Static("Language:"),
                OptionList(
                    *[
                        Option(lang.value, id=f"lang_{lang.name}") for lang in Language
                    ],  # ← * unpacking!
                    id="edit_language",
                    disabled=True,
                ),
                Horizontal(
                    Button(
                        "Update", id="update_snippet", variant="primary", disabled=True
                    ),
                    Button("Cancel", id="cancel_edit", variant="error"),
                    id="edit_actions",
                ),
                id="edit_form",
            )

            await content.mount(form)
            self.query_one("#edit_id", Input).focus()
            self.query_one("#status", Static).update("Enter ID → Load → Edit → Update")
        else:
            content.remove_children()
            self.show_edit_inputs = False

    async def toggle_favorite(self, snippet_id: int) -> None:
        with get_session() as session:
            snippet = session.get(Snippet, snippet_id)
            if snippet:
                snippet.favorite = not snippet.favorite
                session.commit()

        content = self.query_one("#content_area")
        content.remove_children()  # ← NEU!
        await self.list_snippets()
        self.query_one("#status", Static).update(f"⭐ Snippet {snippet_id} toggled!")

    async def toggle_fav_selected(self) -> None:
        table = self.query_one("#snippet_table", DataTable)
        if table.cursor_coordinate is None:
            self.notify("No row selected!", severity="warning")
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        snippet_id = int(row_key.value)
        await self.toggle_favorite(snippet_id)

    async def delete_selected(self) -> None:
        table = self.query_one("#snippet_table", DataTable)
        if table.cursor_coordinate is None:
            self.notify("No row selected!", severity="warning")
            return
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        snippet_id = int(row_key.value)
        await self.delete_selected_snippet(snippet_id)

    async def delete_selected_snippet(self, snippet_id: int) -> None:
        with get_session() as session:
            repo = DBSnippetRepo(session)
            repo.delete(snippet_id)

        content = self.query_one("#content_area")
        content.remove_children()  # ← NEU!
        await self.list_snippets()
        self.query_one("#status", Static).update(f"🗑️ Snippet {snippet_id} deleted!")

    async def refresh_list(self) -> None:
        """Liste neu laden (Ctrl+R)"""
        await self.refresh_table()

    async def refresh_table(self) -> None:
        await self.list_snippets()

    BINDINGS = [
        ("f", "toggle_fav_selected", "Toggle Favorite"),
        ("d", "delete_selected", "Delete Selected"),
        ("e", "edit_selected", "Edit Selected"),
        ("ctrl+r", "refresh_list", "Refresh List"),
    ]

    async def action_toggle_fav_selected(self) -> None:
        await self.toggle_fav_selected()

    async def action_delete_selected(self) -> None:
        await self.delete_selected()

    async def action_edit_selected(self) -> None:
        await self.edit_selected()

    async def action_refresh_list(self) -> None:
        await self.refresh_list()

    @on(OptionList.OptionSelected)
    async def language_selected(self, event: OptionList.OptionSelected) -> None:
        selected_language_text = event.option.prompt
        self.selected_language = selected_language_text
        status = self.query_one("#status", Static)
        status.update(f"Language selected: {selected_language_text}")

    @on(Button.Pressed, "#add")
    async def add_snippet(self) -> None:
        content = self.query_one("#content_area")
        content.remove_children()
        self.show_add_inputs = not self.show_add_inputs

        if not self.show_add_inputs:
            return

        code = TextArea(id="code", placeholder="Code (Enter für Zeilenumbruch)")
        code.styles.height = 15

        form = Vertical(
            Static("Titel:"),
            Input(placeholder="Title", id="title"),
            Static("Code:"),
            code,
            Static("Beschreibung:"),
            Input(placeholder="Description", id="description"),
            Static("Sprache:"),
            OptionList(
                Option("Python", id="lang_python"),
                Option("Rust", id="lang_rust"),
                Option("Golang", id="lang_go"),
                Option("Javascript", id="lang_java"),
                Option("Powershell", id="lang_powershell"),
                Option("Bash", id="lang_bash"),
                Option("SQL", id="lang_sql"),
                Option("Other", id="lang_other"),
                id="language_select",
            ),
            Button("Submit", id="submit"),
            id="add_form",
        )

        await content.mount(form)
        code.focus()

    @on(Button.Pressed, "#submit")
    async def submit_snippet(self) -> None:
        title_input = self.query_one("#title", Input)
        code_input = self.query_one("#code", TextArea)
        description_input = self.query_one("#description", Input)

        title = title_input.value
        code = code_input.text
        description = description_input.value

        lang_list = self.query_one("#language_select", OptionList)
        language_str = "Python"  # Fallback
        if lang_list.highlighted is not None:
            language_str = lang_list.options[lang_list.highlighted].prompt

        language_enum = Language[language_str.lower()]

        session = get_session()
        repo = DBSnippetRepo(session)
        snippet = Snippet(
            title=title,
            code=code,
            description=description,
            language=language_enum,
            favorite=False,
        )
        repo.add(snippet)

        status = self.query_one("#status", Static)
        status.update(f"✅ Snippet '{title}' added (ID: {snippet.id})")

        await self.list_snippets()  # ← Direkt Liste + Form weg!

    @on(Button.Pressed, "#list")
    async def list_snippets(self) -> None:
        all_tables = self.query(DataTable)
        for table in all_tables:
            if table.id == "snippet_table":
                await table.remove()

        content = self.query_one("#content_area")
        content.remove_children()

        # 2. Neue Tabelle
        table = DataTable(id="snippet_table")
        await content.mount(table)

        # 3. Daten laden
        snippets = DBSnippetRepo(get_session()).list()
        table.add_columns("ID", "Title", "Code", "Description", "Language", "Favorite")

        for snippet in snippets:
            favorite_icon = "⭐" if snippet.favorite else ""
            code_preview = (
                snippet.code[:100] + "..." if len(snippet.code) > 100 else snippet.code
            )
            title_short = (
                snippet.title[:25] + "..." if len(snippet.title) > 25 else snippet.title
            )
            desc_short = (
                snippet.description[:25] + "..."
                if len(snippet.description) > 25
                else snippet.description
            )

            table.add_row(
                str(snippet.id),
                title_short,
                code_preview,
                desc_short,
                snippet.language.value,
                favorite_icon,
                key=str(snippet.id),
            )

        # 4. Fokus + Status
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.focus()
        self.call_later(table.focus)

        status = self.query_one("#status", Static)
        status.update(
            "↑↓=Nav, Enter=Show Code, [yellow]F=Favorite[/], [red]D=Delete[/], [orange]E=Edit[/], [green]Ctrl+R=Refresh[/]"
        )

    @on(DataTable.RowSelected)
    async def on_row_action(self, event: DataTable.RowSelected) -> None:
        # Direkt aus Event lesen - KEIN table.query nötig!
        snippet_id = int(event.row_key.value) if event.row_key else None

        if snippet_id:
            with get_session() as session:
                snippet = session.get(Snippet, snippet_id)
            if snippet:
                await self.push_screen(
                    CodeViewScreen(
                        snippet.id, snippet.code, snippet.title, snippet.language.value
                    )
                )

    @on(Button.Pressed, "#delete")
    async def delete_snippet(self) -> None:
        content = self.query_one("#content_area")
        self.show_delete_inputs = not self.show_delete_inputs

        if self.show_delete_inputs:
            content.remove_children()

            await content.mount(Input(placeholder="Snippet ID", id="snippet_id"))
            await content.mount(Button("Confirm Delete", id="confirm_delete"))

            status = self.query_one("#status", Static)
            status.update("Enter ID → Confirm Delete")
        else:
            widgets = self.query("#snippet_id")
            if not widgets:
                status = self.query_one("#status", Static)
                status.update("Snippet ID input not found. Please try again.")
                return

            snippet_id_input = widgets[0]
            try:
                snippet_id = int(snippet_id_input.value)
            except ValueError:
                status = self.query_one("#status", Static)
                status.update("Invalid snippet ID entered. Please enter a number.")
                return

            with get_session() as session:
                repo = DBSnippetRepo(session)
                snippet = session.get(Snippet, snippet_id)
                status = self.query_one("#status", Static)

                if snippet is None:
                    status.update(f"Snippet with id {snippet_id} not found")
                    return

                repo.delete(snippet_id)
                status.update(f"Snippet with ID {snippet_id} deleted.")

            content.remove_children()
            self.show_delete_inputs = False

    @on(Button.Pressed, "#confirm_delete")
    async def confirm_delete_snippet(self) -> None:
        status = self.query_one("#status", Static)

        # 1. Input LESEN (bevor löschen!)
        try:
            snippet_id_input = self.query_one("#snippet_id", Input)
            snippet_id = int(snippet_id_input.value)
        except (NoMatches, ValueError):
            status.update("❌ Snippet ID Input not found or invalid!")
            return

        # 2. ALLES löschen
        content = self.query_one("#content_area")
        content.remove_children()  # ← Sauberer als for-loop!

        # 3. Löschen
        try:
            with get_session() as session:
                repo = DBSnippetRepo(session)
                snippet = session.get(Snippet, snippet_id)
                if snippet is None:
                    raise SnippetNotFoundError(
                        f"Snippet with ID {snippet_id} not found."
                    )
                repo.delete(snippet_id)
            status.update(f"✅ Snippet ID {snippet_id} deleted!")
        except SnippetNotFoundError as e:
            status.update(str(e))

    @on(Button.Pressed, "#load_edit")
    async def load_snippet_for_edit(self) -> None:
        """Snippet laden und Form aktivieren"""
        snippet_id_input = self.query_one("#edit_id", Input)
        try:
            snippet_id = int(snippet_id_input.value)
        except ValueError:
            self.query_one("#status", Static).update("❌ Invalid ID!")
            return

        with get_session() as session:
            repo = DBSnippetRepo(session)
            snippet = repo.get(snippet_id)
            if not snippet:
                self.query_one("#status", Static).update(
                    f"❌ Snippet {snippet_id} not found!"
                )
                return

        # 🔥 TEXTAREA.text statt Input.value!
        self.query_one("#edit_title", Input).value = snippet.title
        self.query_one("#edit_code", TextArea).text = snippet.code  # ← .text!
        self.query_one("#edit_desc", Input).value = snippet.description

        # Language setzen
        lang_list = self.query_one("#edit_language", OptionList)
        for i, option in enumerate(lang_list.options):
            if option.id == f"lang_{snippet.language.name}":
                lang_list.highlighted = i
                break

        # Aktivieren
        for widget_id in ["edit_title", "edit_code", "edit_desc"]:
            self.query_one(
                f"#{widget_id}", Input | TextArea
            ).disabled = False  # ← Auch TextArea!
        self.query_one("#edit_language", OptionList).disabled = False
        self.query_one("#update_snippet", Button).disabled = False

        self.query_one("#status", Static).update(f"✅ Loaded '{snippet.title}'")
        self.query_one("#edit_code", TextArea).focus()  # ← Code editierbar!

    @on(Button.Pressed, "#update_snippet")
    async def update_snippet(self) -> None:
        snippet_id = int(self.query_one("#edit_id", Input).value)
        title = self.query_one("#edit_title", Input).value
        code = self.query_one("#edit_code", TextArea).text  # ← .text!
        desc = self.query_one("#edit_desc", Input).value

        lang_list = self.query_one("#edit_language", OptionList)
        index = lang_list.highlighted
        lang_option = lang_list.options[index] if index is not None else None
        language = (
            Language[lang_option.id.replace("lang_", "")]
            if lang_option
            else Language.python
        )

        # Update-Snippet
        update_snippet = Snippet(
            id=snippet_id,  # ID bleibt!
            title=title,
            code=code,
            description=desc,
            language=language,
        )

        with get_session() as session:
            repo = DBSnippetRepo(session)
            repo.update(update_snippet)

        self.query_one("#status", Static).update(f"✅ Snippet {snippet_id} updated!")
        self.show_edit_inputs = False

        content = self.query_one("#content_area")
        content.remove_children()  # ← FIX! (vor refresh_table)
        await self.refresh_table()

    @on(Button.Pressed, "#cancel_edit")
    async def cancel_edit(self) -> None:
        self.show_edit_inputs = False
        content = self.query_one("#content_area")
        content.remove_children()

    @on(Button.Pressed, "#exit")
    async def exit_app(self) -> None:
        self.query_one("#status", Static).update("Exiting...")
        content = self.query_one("#content_area")
        content.remove_children()  # ← NEU!
        self.exit()

    def disable_db_inputs(self, disabled: bool) -> None:
        for field_id in ["user", "password", "host", "port", "name"]:
            try:
                inp = self.query_one(f"#{field_id}", Input)
                inp.disabled = disabled
            except NoMatches:
                continue

    @on(OptionList.OptionSelected, "#db_options")
    async def on_db_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Reagiert auf Default/Postgres Auswahl"""
        if event.option.id == "default":
            self.disable_db_inputs(True)
        elif event.option.id == "postgres":
            self.disable_db_inputs(False)

    @on(Button.Pressed, "#init")
    async def init_config_tui(self) -> None:
        content = self.query_one("#content_area")
        content.remove_children()  # ← FIX!
        self.show_add_inputs = not self.show_add_inputs

        if self.show_add_inputs:
            option_list = OptionList(
                Option(
                    "Default -> SQLite DB tui.sqlite will be created in current directory",
                    id="default",
                ),
                Option("Postgres-DB", id="postgres"),
                id="db_options",
            )
            await content.mount(option_list)  # ← await!

            await content.mount(Input(placeholder="DB_USER", id="user", disabled=True))
            await content.mount(
                Input(placeholder="DB_PASS", id="password", disabled=True)
            )
            await content.mount(Input(placeholder="DB_HOST", id="host", disabled=True))
            await content.mount(Input(placeholder="DB_PORT", id="port", disabled=True))
            await content.mount(Input(placeholder="DB_NAME", id="name", disabled=True))
            await content.mount(Button("Save", id="save"))

    def show_success_message(self) -> None:
        """Zeigt Erfolgsnachricht nach Speichern"""
        status = self.query_one("#status", Static)
        status.update(f"[green]🎉 Snipster-TUI is ready![/] Edit {ENV_PATH} anytime.")

    def schedule_close_config(self) -> None:
        """Schedule closing config form after delay"""
        self.call_later(lambda s=self: self.close_config_form(), 3.0)

    @on(Button.Pressed, "#save")
    async def save_config(self) -> None:
        """Save-Handler mit Directory-Setup + Config-Writing"""
        status = self.query_one("#status", Static)

        # 1. Project Directory erstellen
        try:
            if not DEFAULT_PROJECT_HOME.exists():
                DEFAULT_PROJECT_HOME.mkdir(parents=True)
                status.update(f"[green]Created directory: '{DEFAULT_PROJECT_HOME}'[/]")
            else:
                status.update(
                    f"[blue]Using existing directory: '{DEFAULT_PROJECT_HOME}'[/]"
                )
        except Exception as e:
            status.update(f"[red]Error creating directory: {e}[/]")
            return

        # 2. DB-URL basierend auf Auswahl
        option_list = self.query_one("#db_options", OptionList)
        highlighted_index = option_list.highlighted
        use_default_db = (highlighted_index is not None) and (highlighted_index == 0)

        if use_default_db:
            database_url = f"sqlite:///{DEFAULT_DB_PATH}"
            status.update("[green]Using Default SQLite DB[/]")
        else:
            # Postgres-Werte aus Inputs lesen
            try:
                db_user = self.query_one("#user", Input).value
                db_pass = self.query_one("#password", Input).value
                db_host = self.query_one("#host", Input).value
                db_port = self.query_one("#port", Input).value
                db_name = self.query_one("#name", Input).value

                if not all([db_user, db_pass, db_host, db_port, db_name]):
                    status.update("[red]Please fill all Postgres fields[/]")
                    return

                database_url = (
                    f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
                )
                status.update("[green]Using custom Postgres DB[/]")
            except Exception as e:
                status.update(f"[red]Error reading inputs: {e}[/]")
                return

        # 3. Config-File schreiben
        try:
            content = [f"DATABASE_URL={database_url}"]
            ENV_PATH.write_text("\n".join(content) + "\n")
            status.update(f"[green]✅ Configuration saved at: {ENV_PATH}[/]")
            from snipster_tui.models import SQLModel

            engine = create_engine(database_url, echo=False)
            SQLModel.metadata.create_all(engine)
        except Exception as e:
            status.update(f"[red]Error writing config: {e}[/]")
            return

        # 4. Erfolg-Feedback (TUI-Style)
        status.update(f"[green]✅ Configuration saved at: {ENV_PATH}[/]")
        self.call_later(self.show_success_message)

        # 5. Auto-Schließen
        self.schedule_close_config()

    async def close_config_form(self) -> None:
        """Config-Form nach Save schließen"""
        self.show_add_inputs = False
        content = self.query_one("#content_area")
        content.remove_children()


if __name__ == "__main__":
    app = Snipster()
    app.run()
