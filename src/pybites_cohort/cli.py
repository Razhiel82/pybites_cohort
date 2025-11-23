from typing import List, Optional

import typer
from decouple import config
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from sqlmodel import Session, create_engine

from pybites_cohort.exceptions import SnippetNotFoundError
from pybites_cohort.models import Language, Snippet, Tag
from pybites_cohort.repo import DBSnippetRepo

app = typer.Typer()

DB_USER = config("DB_USER")
DB_PASS = config("DB_PASS")
DB_HOST = config("DB_HOST")
DB_PORT = config("DB_PORT")
DB_NAME = config("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_session():
    engine = create_engine(DATABASE_URL, echo=True)
    return Session(engine)


def comma_separated_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@app.command()
def add(
    title: str,
    code: str,
    description: str = "",
    language: Language = Language.python,
    favorite: bool = False,
    tags: Optional[str] = typer.Option(
        None, callback=comma_separated_list, help="Comma separated list of tags"
    ),
):
    session = get_session()
    repo = DBSnippetRepo(session)
    tags_list = tags or []
    tag_objs = [Tag(name=tag) for tag in tags_list]
    snippet = Snippet(
        title=title,
        code=code,
        description=description,
        language=language,
        favorite=favorite,
        tags=tag_objs,
    )
    repo.add(snippet)
    typer.echo(f"Snippet added: {title}")


@app.command()
def list(favorite: bool = False):
    session = get_session()
    repo = DBSnippetRepo(session)
    snippets = repo.list(favorite=favorite)
    star_emoji = "⭐"
    table = Table(title="Snippet", show_lines=True)
    table.add_column("ID", style="red", no_wrap=True)
    table.add_column("Title")
    table.add_column(
        "Code",
    )
    table.add_column("Description")
    table.add_column("Language")
    table.add_column("Tags")
    table.add_column("Favorite")
    for snippet in snippets:
        syntax = Syntax(
            snippet.code, snippet.language.name, theme="monokai", line_numbers=True
        )
        tag_list = ", ".join(snippet.tag_list)
        table.add_row(
            str(snippet.id),
            snippet.title,
            syntax,
            snippet.description,
            snippet.language.name,
            tag_list,
            star_emoji if snippet.favorite else "",
        )
    console = Console()
    console.print(table, justify="left")


@app.command()
def get(snippet_id: int):
    session = get_session()
    repo = DBSnippetRepo(session)
    snippet = repo.get(snippet_id)
    if snippet:
        tag_list = ", ".join(snippet.tag_list)
        table = Table(title="Snippet")
        table.add_column("ID", style="red", no_wrap=True)
        table.add_column("Title")
        table.add_column("Code")
        table.add_column("Description")
        table.add_column("Language")
        table.add_column("Tags")
        table.add_column("Favorite")
        table.add_row(
            str(snippet.id),
            snippet.title,
            snippet.code,
            snippet.description,
            snippet.language.name,
            tag_list,
            "⭐" if snippet.favorite else "",
        )
        console = Console()
        console.print(table, justify="left")
        # typer.echo(
        #     f"Snippet {snippet.id}: {snippet.title}\nCode:\n{snippet.code}\nDescription: {snippet.description}\nLanguage: {snippet.language.name}\nFavorite: {snippet.favorite}\nTags: {', '.join(snippet.tag_list)}"
        # )
    else:
        raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")


@app.command()
def delete(snippet_id: int):
    session = get_session()
    repo = DBSnippetRepo(session)
    try:
        repo.delete(snippet_id)
        typer.echo(f"Snippet with id {snippet_id} deleted.")
    except Exception as e:
        typer.echo(str(e))


@app.command()
def search(snippet_title: str, language: Optional[Language] = None):
    session = get_session()
    repo = DBSnippetRepo(session)
    snippets = repo.search(snippet_title, language)
    for snippet in snippets:
        typer.echo(
            f"{snippet.id}: {snippet.title} ({snippet.language.name}) - Favorite: {snippet.favorite}"
        )


@app.command()
def fav_on(snippet_id: int):
    session = get_session()
    repo = DBSnippetRepo(session)
    try:
        repo.favorite_on(snippet_id)
        typer.echo(f"Snippet with id {snippet_id} marked as favorite.")
    except Exception as e:
        typer.echo(str(e))


@app.command()
def fav_off(snippet_id: int):
    session = get_session()
    repo = DBSnippetRepo(session)
    try:
        repo.favorite_off(snippet_id)
        typer.echo(f"Snippet with id {snippet_id} unmarked as favorite.")
    except Exception as e:
        typer.echo(str(e))


@app.command()
def tag(
    snippet_id: int,
    tags: List[str] = typer.Option(..., help="List of tags to add or remove"),
    remove: bool = typer.Option(False, help="Remove tags if set, otherwise add"),
):
    """
    tag --tags "['tag1','tag2']"
    """
    if not tags:
        typer.echo("Error: At least one tag must be provided.")
        raise typer.Exit(code=1)
    session = get_session()
    repo = DBSnippetRepo(session)
    try:
        repo.tag(snippet_id, *tags, remove=remove)
        action = "Removed" if remove else "Added"
        typer.echo(f"{action} tags {tags} for snippet with id {snippet_id}.")
    except Exception as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover
    app()
