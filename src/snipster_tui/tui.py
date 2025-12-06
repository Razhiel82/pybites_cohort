from decouple import config
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

DB_USER = config("DB_USER")
DB_PASS = config("DB_PASS")
DB_HOST = config("DB_HOST")
DB_PORT = config("DB_PORT")
DB_NAME = config("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_session():
    engine = create_engine(DATABASE_URL, echo=False)
    return Session(engine)


class Snipster(App):
    show_add_inputs = reactive(False)
    show_delete_inputs = reactive(False)

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Button("Add Snippet", id="add"),
            Button("List Snippets", id="list"),
            Button("Delete Snippet", id="delete"),
            Button("Exit", id="exit", variant="error"),
            id="main_menu",
        )
        yield Static("", id="status")
        yield Vertical(id="content_area")

    def clear_content_area(self) -> None:
        content = self.query_one("#content_area")
        # Entferne alle Widgets unterhalb des Containers, aber nicht den Container selbst
        for child in list(content.children):
            child.remove()

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
            content.mount(Input(placeholder="Tags (comma separated)", id="tags"))
            content.mount(Button("Submit", id="submit"))

    @on(Button.Pressed, "#submit")
    async def submit_snippet(self) -> None:
        title_input = self.query_one("#title", Input)
        code_input = self.query_one("#code", Input)
        description_input = self.query_one("#description", Input)
        tags_input = self.query_one("#tags", Input)
        title = title_input.value
        code = code_input.value
        description = description_input.value
        language_str = getattr(self, "selected_language", "Python")
        language_enum = Language[language_str.lower()]
        tags_str = tags_input.value
        tags_list = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
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

        if tags_list:
            repo.tag(snippet.id, *tags_list)

        status = self.query_one("#status", Static)
        status.update(f"Snippet '{title}' added.")

        # Eingabefelder verstecken und entfernen
        self.show_add_inputs = False
        self.query_one("#title").remove()
        self.query_one("#code").remove()
        self.query_one("#submit").remove()
        self.query_one("#description").remove()
        self.query_one("#language_select").remove()
        self.query_one("#tags").remove()

    @on(Button.Pressed, "#list")
    async def list_snippets(self) -> None:
        self.clear_content_area()
        content = self.query_one("#content_area")
        session = get_session()
        repo = DBSnippetRepo(session)
        snippets = repo.list()

        table = DataTable()
        content.mount(table)
        self.mount(table, after=self.query_one("#status"))

        table.add_columns("ID", "Title", "Language", "Favorite", "Tags")

        seen = set()
        unique_snippets = []
        for snippet in snippets:
            if snippet.id not in seen:
                unique_snippets.append(snippet)
                seen.add(snippet.id)

        for snippet in unique_snippets:
            favorite_icon = "⭐" if snippet.favorite else ""
            tags = ", ".join(snippet.tag_list)
            table.add_row(
                str(snippet.id),
                snippet.title,
                snippet.language.value,
                favorite_icon,
                tags,
            )
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.focus()

    # Not working yet :( Session error while refreshing but adding and removing works via selection
    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one(DataTable)
        row_index = event.cursor_row

        id_coord = Coordinate(row=row_index, column=0)
        snippet_id_str = table.get_cell_at(id_coord)
        snippet_id = int(snippet_id_str)

        with get_session() as session:
            repo = DBSnippetRepo(session)
            snippet = session.get(Snippet, snippet_id)

            if snippet.favorite:
                repo.favorite_off(snippet_id)
            else:
                repo.favorite_on(snippet_id)

        favorite_column_index = 3
        fav_coord = Coordinate(row=row_index, column=favorite_column_index)
        fav_icon = "⭐" if snippet.favorite else ""
        table.update_cell(fav_coord, fav_icon)

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
        content = self.query_one("#content_area")
        for child in list(content.children):
            await child.remove()
        snippet_id_input = self.query_one("#snippet_id", Input)
        try:
            snippet_id = int(snippet_id_input.value)
        except ValueError:
            status = self.query_one("#status", Static)
            status.update("Ungültige ID. Bitte geben Sie eine Zahl ein.")
            return
        except NoMatches:
            widgets = self.query("#snippet_id", Input)
            if not widgets:
                status = self.query_one("#status", Static)
                status.update("Snippet ID input not found. Please try again.")
                return
            snippet_id_input = widgets[0]
            snippet_id = int(snippet_id_input.value)
        try:
            with get_session() as session:
                repo = DBSnippetRepo(session)
                snippet = session.get(Snippet, snippet_id)
                if snippet is None:
                    raise SnippetNotFoundError(
                        f"Snippet mit ID {snippet_id} nicht gefunden."
                    )
                repo.delete(snippet_id)
                status = self.query_one("#status", Static)
                status.update(f"Snippet mit ID {snippet_id} wurde gelöscht.")
                self.query_one("#snippet_id").remove()
                self.query_one("#confirm_delete").remove()
        except SnippetNotFoundError as e:
            status = self.query_one("#status", Static)
            status.update(str(e))

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
            self.query_one("#tags").remove()


if __name__ == "__main__":
    app = Snipster()
    app.run()
