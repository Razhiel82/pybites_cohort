from pathlib import Path

from decouple import Config, RepositoryEnv
from rich.syntax import Syntax
from sqlmodel import Session, create_engine
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Input, OptionList, Static
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


class Snipster(App):
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

    def clear_content_area(self) -> None:
        content = self.query_one("#content_area")
        # Entferne alle Widgets unterhalb des Containers, aber nicht den Container selbst
        for child in list(content.children):
            child.remove()

    async def toggle_favorite(self, snippet_id: int) -> None:
        """Toggle favorite status"""
        with get_session() as session:
            snippet = session.get(Snippet, snippet_id)
            if snippet:
                snippet.favorite = not snippet.favorite
                session.commit()

        # Tabelle refreshen
        await self.refresh_table()

        # Status ohne snippet-Zugriff
        status = self.query_one("#status", Static)
        status.update(f"✅ Snippet {snippet_id} favorite toggled!")

    async def delete_selected_snippet(self, snippet_id: int) -> None:
        with get_session() as session:
            repo = DBSnippetRepo(session)
            repo.delete(snippet_id)

        await self.refresh_table()

        status = self.query_one("#status", Static)
        status.update(f"✅ Snippet {snippet_id} deleted!")

    async def action_toggle_fav_selected(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            row_index = table.cursor_row
            snippet_id = int(table.get_cell_at(Coordinate(row_index, 0)))
            await self.toggle_favorite(snippet_id)

    async def action_delete_selected(self) -> None:
        """Delete ausgewählte Zeile"""
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            row_index = table.cursor_row
            snippet_id = int(table.get_cell_at(Coordinate(row_index, 0)))
            await self.delete_selected_snippet(snippet_id)

    async def edit_snippet(self, snippet_id: int) -> None:
        """Direktes Edit aus Kontext-Menü"""
        await self.toggle_edit_snippet()

        self.call_later(self._load_snippet_direct, snippet_id)

    async def _load_snippet_direct(self, snippet_id: int) -> None:
        """Snippet direkt laden (nach DOM-Update)"""
        edit_id_input = self.query_one("#edit_id", Input)
        if edit_id_input:
            edit_id_input.value = str(snippet_id)
            self.call_later(self.load_snippet_for_edit)

    async def action_edit_selected(self) -> None:
        """E-Taste: Edit ausgewählte Zeile"""
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            row_index = table.cursor_row
            snippet_id = int(table.get_cell_at(Coordinate(row_index, 0)))
            await self.edit_snippet(snippet_id)

    async def action_refresh_list(self) -> None:
        """Liste neu laden"""
        await self.refresh_table()

    async def refresh_table(self) -> None:
        await self.list_snippets()  # Tabelle neu rendern

    BINDINGS = [
        ("f", "toggle_fav_selected", "Toggle Favorite"),
        ("d", "delete_selected", "Delete Selected"),
        ("e", "edit_selected", "Edit Selected"),
        ("ctrl+r", "refresh_list", "Refresh List"),
    ]

    @on(OptionList.OptionSelected)
    async def language_selected(self, event: OptionList.OptionSelected) -> None:
        selected_language_text = event.option.prompt
        self.selected_language = selected_language_text
        status = self.query_one("#status", Static)
        status.update(f"Language selected: {selected_language_text}")

    @on(Button.Pressed, "#add")
    async def add_snippet(self) -> None:
        self.clear_content_area()
        content = self.query_one("#content_area")
        self.show_add_inputs = not self.show_add_inputs
        if self.show_add_inputs:
            content.mount(Input(placeholder="Title", id="title"))
            content.mount(Input(placeholder="Code", id="code"))
            content.mount(Input(placeholder="Description", id="description"))
            content.mount(
                OptionList(
                    Option("Python", id="lang_python"),
                    Option("Rust", id="lang_rust"),
                    Option("Golang", id="lang_go"),
                    Option("Javascript", id="lang_java"),
                    id="language_select",
                )
            )
            content.mount(Button("Submit", id="submit"))

    @on(Button.Pressed, "#submit")
    async def submit_snippet(self) -> None:
        title_input = self.query_one("#title", Input)
        code_input = self.query_one("#code", Input)
        description_input = self.query_one("#description", Input)
        title = title_input.value
        code = code_input.value
        description = description_input.value
        language_str = getattr(self, "selected_language", "Python")
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

        if not snippet.id:
            session.commit()  # Nur falls commit nicht schon in add() drin ist

        if snippet.id is None:
            raise RuntimeError("Snippet ID not set after add/commit")

        status = self.query_one("#status", Static)
        status.update(f"Snippet '{title}' added.")

        # Eingabefelder verstecken und entfernen
        self.show_add_inputs = False
        self.query_one("#title").remove()
        self.query_one("#code").remove()
        self.query_one("#submit").remove()
        self.query_one("#description").remove()
        self.query_one("#language_select").remove()

    @on(Button.Pressed, "#list")
    async def list_snippets(self) -> None:
        self.clear_content_area()
        content = self.query_one("#content_area")

        snippets = DBSnippetRepo(get_session()).list()
        table = DataTable()
        content.mount(table)

        # Spalten mit renderable-Support:
        table.add_columns(
            "ID", "Title", "Code", "Description", "Language", "Favorite", "Actions"
        )

        for snippet in snippets:
            favorite_icon = "⭐" if snippet.favorite else ""

            # Rich Syntax für Code (kurz gehalten für TUI):
            code_preview = Syntax(
                snippet.code[:100] + "..." if len(snippet.code) > 100 else snippet.code,
                str(snippet.language.value),  # "python", "rust", etc.
                theme="monokai",
                line_numbers=False,  # TUI: zu eng
                word_wrap=True,
                padding=(0, 1),
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
                code_preview,  # ← Rich Syntax!
                desc_short,
                snippet.language.value,
                favorite_icon,
                "⭐/🗑️/✏️",
            )

        table.cursor_type = "row"
        table.zebra_stripes = True
        table.focus()

        status = self.query_one("#status", Static)
        status.update(
            "↑↓=Nav, Enter=Action-Menu, [yellow]F=Favorite[/yellow], [red]D=Delete[/red], [orange]E=Edit[/orange], [green]Ctrl+R=Refresh[/green]"
        )

    @on(DataTable.RowSelected)
    async def on_row_action(self, event: DataTable.RowSelected) -> None:
        table = self.query_one(DataTable)
        row_index = event.cursor_row

        # ID extrahieren
        id_coord = Coordinate(row=row_index, column=0)
        snippet_id = int(table.get_cell_at(id_coord))

        # Kontext-Menü mounten
        from textual.widgets import Button, Static

        menu = Horizontal(
            Button("⭐ Toggle Favorite", id=f"fav_{snippet_id}"),
            Button("🗑️ Delete Snippet", id=f"del_{snippet_id}"),
            Button("✏️ Edit Snippet", id=f"edit_{snippet_id}"),
            Button("❌ Cancel", id="cancel_action"),
            id="action_menu",
        )

        content = self.query_one("#content_area")
        content.mount(Static(f"Actions for Snippet ID: {snippet_id}", id="menu_title"))
        content.mount(menu)
        menu.focus()

    @on(Button.Pressed, "#action_menu Button")
    async def handle_row_action(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        # Menu entfernen
        try:
            self.query_one("#action_menu", Horizontal).remove()
            self.query_one("#menu_title").remove()
        except NoMatches:
            pass

        # Actions → Auto-Refresh!
        if button_id.startswith("fav_"):
            snippet_id = int(button_id.split("_")[1])
            await self.toggle_favorite(snippet_id)

        elif button_id.startswith("del_"):
            snippet_id = int(button_id.split("_")[1])
            await self.delete_selected_snippet(snippet_id)

        elif button_id.startswith("edit_"):
            snippet_id = int(button_id.split("_")[1])
            await self.edit_snippet(snippet_id)

        elif button_id == "cancel_action":
            table = self.query_one(DataTable)
            table.focus()

    @on(Button.Pressed, "#delete")
    async def delete_snippet(self) -> None:
        content = self.query_one("#content_area")
        self.show_delete_inputs = not self.show_delete_inputs

        if self.show_delete_inputs:
            self.clear_content_area()
            await content.mount(Input(placeholder="Snippet ID", id="snippet_id"))
            await content.mount(Button("Confirm Delete", id="confirm_delete"))
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
                if snippet is None:
                    status = self.query_one("#status", Static)
                    status.update(f"Snippet with id {snippet_id} not found")
                    return
                repo.delete(snippet_id)
                status = self.query_one("#status", Static)
                status.update(f"Snippet with ID {snippet_id} deleted.")

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
        for child in list(content.children):
            await child.remove()

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

    @on(Button.Pressed, "#edit")
    async def toggle_edit_snippet(self) -> None:
        content = self.query_one("#content_area")
        self.show_edit_inputs = not self.show_edit_inputs

        if self.show_edit_inputs:
            self.clear_content_area()

            content = self.query_one("#content_area")

            content.mount(Input(placeholder="Snippet ID", id="edit_id"))
            content.mount(Button("Load Snippet", id="load_edit"))
            content.mount(Input(placeholder="Title", id="edit_title", disabled=True))
            content.mount(Input(placeholder="Code", id="edit_code", disabled=True))
            content.mount(
                Input(placeholder="Description", id="edit_desc", disabled=True)
            )

            options = [Option(lang.value, id=f"lang_{lang.name}") for lang in Language]
            lang_list = OptionList(
                *options,
                id="edit_language",
                disabled=True,
            )

            content.mount(lang_list)

            content.mount(
                Horizontal(
                    Button(
                        "Update", id="update_snippet", variant="primary", disabled=True
                    ),
                    Button("Cancel", id="cancel_edit", variant="error"),
                    id="edit_actions",  # ✅ ID hinzufügen!
                )
            )

            self.query_one("#status", Static).update("Enter ID → Load → Edit → Update")
        else:
            self.clear_content_area()
            self.show_edit_inputs = False

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

            # ✅ .value = ... statt .update()!
            self.query_one("#edit_title", Input).value = snippet.title
            self.query_one("#edit_code", Input).value = snippet.code
            self.query_one("#edit_desc", Input).value = snippet.description

            # Language: Erste passende Option finden
            lang_list = self.query_one("#edit_language", OptionList)
            for i, option in enumerate(lang_list.options):
                if option.id == f"lang_{snippet.language.name}":
                    lang_list.highlighted = i  # ✅ Index setzen!
                    break

            # Aktivieren
            for widget_id in ["edit_title", "edit_code", "edit_desc"]:
                self.query_one(f"#{widget_id}", Input).disabled = False
            self.query_one("#edit_language", OptionList).disabled = False
            self.query_one("#update_snippet", Button).disabled = False

            self.query_one("#status", Static).update(f"✅ Loaded '{snippet.title}'")

    @on(Button.Pressed, "#update_snippet")
    async def update_snippet(self) -> None:
        snippet_id = int(self.query_one("#edit_id", Input).value)
        title = self.query_one("#edit_title", Input).value
        code = self.query_one("#edit_code", Input).value
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
        self.clear_content_area()
        await self.refresh_table()

    @on(Button.Pressed, "#cancel_edit")
    async def cancel_edit(self) -> None:
        self.show_edit_inputs = False
        self.clear_content_area()

    @on(Button.Pressed, "#exit")
    async def exit_app(self) -> None:
        self.query_one("#status", Static).update("Exiting...")
        self.exit()
        if self.show_add_inputs:
            self.show_add_inputs = False
        else:
            self.query_one("#title").remove()
            self.query_one("#code").remove()
            self.query_one("#submit").remove()
            self.query_one("#description").remove()
            self.query_one("#language_select").remove()

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
        self.clear_content_area()
        content = self.query_one("#content_area")
        self.show_add_inputs = not self.show_add_inputs
        # self.disable_db_inputs(True)
        if self.show_add_inputs:
            option_list = OptionList(
                Option(
                    "Default -> SQLite DB tui.sqlite will be created in current directory",
                    id="default",
                ),
                Option("Postgres-DB", id="postgres"),
                id="db_options",
            )
            content.mount(option_list)

            content.mount(Input(placeholder="DB_USER", id="user", disabled=True))
            content.mount(Input(placeholder="DB_PASS", id="password", disabled=True))
            content.mount(Input(placeholder="DB_HOST", id="host", disabled=True))
            content.mount(Input(placeholder="DB_PORT", id="port", disabled=True))
            content.mount(Input(placeholder="DB_NAME", id="name", disabled=True))

            content.mount(Button("Save", id="save"))

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
        self.clear_content_area()


if __name__ == "__main__":
    app = Snipster()
    app.run()
