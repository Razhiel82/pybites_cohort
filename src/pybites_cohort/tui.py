from textual import on
from textual.app import App, ComposeResult
from textual.reactive import reactive
from textual.widgets import Button, Input, Label, Static

# from pybites_cohort.repo import InMemorySnippetRepo
# from pybites_cohort.models import Snippet, Language


class Snipster(App):
    show_add_inputs = reactive(False)

    def compose(self) -> ComposeResult:
        yield Label("Welcome to Snipster TUI!")
        yield Button("Add Snippet", id="add")
        yield Button("Delete Snippet", id="delete")
        yield Button("Exit", id="exit", variant="error")
        yield Static("", id="status")

    @on(Button.Pressed, "#add")
    def add_snippet(self) -> None:
        self.show_add_inputs = not self.show_add_inputs
        if self.show_add_inputs:
            self.mount(Input(placeholder="Title", id="title"))
            self.mount(Input(placeholder="Code", id="code"))
            self.mount(Button("Submit", id="submit"))
        else:
            self.query_one("#title").remove()
            self.query_one("#code").remove()
            self.query_one("#submit").remove()


if __name__ == "__main__":
    app = Snipster()
    app.run()
