import re
from typing import List, Optional

import typer
from decouple import config
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from sqlmodel import Session, create_engine

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
    engine = create_engine(DATABASE_URL, echo=False)
    return Session(engine)


@app.command()
def add(
    title: str,
    code: str,
    description: str = "",
    language: Language = Language.python,
    favorite: bool = False,
    tags: Optional[list[str]] = typer.Option(None),
):
    session = get_session()
    repo = DBSnippetRepo(session)
    tag_objs = [Tag(name=tag) for tag in (tags or [])]
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
    snippets = repo.list()
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
        all_tags = []
        syntax = Syntax(
            snippet.code, snippet.language.name, theme="monokai", line_numbers=True
        )
        for tag_str in snippet.tag_list:
            tags = re.findall(r"\[(.*?)\]", tag_str)
            for tag_group in tags:
                all_tags.extend([t.strip() for t in tag_group.split(",")])
        tag_list = ", ".join(all_tags)
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
    # typer.echo(
    #     f"No: {snippet.id}, Title: {snippet.title}, Language: ({snippet.language.name}), Favorite: {snippet.favorite} Tags: {', '.join(snippet.tag_list)}"
    # )


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
        table.add_row(
            str(snippet.id),
            snippet.title,
            snippet.code,
            snippet.description,
            snippet.language.name,
            tag_list,
        )
        console = Console()
        console.print(table, justify="left")
        # typer.echo(
        #     f"Snippet {snippet.id}: {snippet.title}\nCode:\n{snippet.code}\nDescription: {snippet.description}\nLanguage: {snippet.language.name}\nFavorite: {snippet.favorite}\nTags: {', '.join(snippet.tag_list)}"
        # )
    else:
        typer.echo(f"Snippet with id {snippet_id} not found.")


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


if __name__ == "__main__":
    app()
