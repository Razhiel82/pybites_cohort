from typing import List, Optional

from decouple import config
from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, create_engine, select

from pybites_cohort.exceptions import SnippetNotFoundError
from pybites_cohort.models import Language, Snippet, Tag
from pybites_cohort.repo import DBSnippetRepo

DB_USER = config("DB_USER")
DB_PASS = config("DB_PASS")
DB_HOST = config("DB_HOST")
DB_PORT = config("DB_PORT")
DB_NAME = config("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_session():
    engine = create_engine(DATABASE_URL, echo=False)
    return Session(engine)


app = FastAPI()


@app.get("/snippets/", response_model=List[Snippet])
def list_snippets(session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    return repo.list()


@app.post("/snippets/")
def add_snippet(snippet_data: Snippet, session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)

    # Tags neu oder bereits vorhanden verknüpfen
    managed_tags = []
    for tag in snippet_data.tags:
        existing_tag = session.exec(select(Tag).where(Tag.name == tag.name)).first()
        if existing_tag:
            managed_tags.append(existing_tag)
        else:
            managed_tags.append(tag)  # Neue Tags werden hinzugefügt

    snippet_data.tags = managed_tags

    repo.add(snippet_data)
    return {"message": f"Snippet '{snippet_data.title}' added with tags."}


@app.delete("/snippets/{snippet_id}")
def delete_snippets(snippet_id: int, session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    snippet = repo.delete(snippet_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return snippet


@app.get("/snippets/search")
def search_snippets(
    title: str,
    language: Optional[Language] = None,
    session: Session = Depends(get_session),
):
    repo = DBSnippetRepo(session)
    snippets = repo.search(title, language)
    if not snippets:
        raise HTTPException(status_code=404, detail="No snippets found")
    return snippets


@app.get("/snippets/{snippet_id}")
def get_snippets(snippet_id: int, session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    snippet = repo.get(snippet_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return snippet


@app.post("/snippets/{snippet_id}/fav_on")
def select_favorite(snippet_id: int, session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    snippet = repo.favorite_on(snippet_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return {"message": f"Snippet {snippet_id} is a favorite now."}


@app.post("/snippets/{snippet_id}/fav_off")
def deselect_favorite(snippet_id: int, session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    snippet = repo.favorite_off(snippet_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return {"message": f"Snippet {snippet_id} is no favorite anymore."}


@app.post("/snippets/{snippet_id}/tags")
def tagging(
    snippet_id: int,
    tags: List[str],
    remove: bool = False,
    session: Session = Depends(get_session),
):
    repo = DBSnippetRepo(session)
    try:
        repo.tag(snippet_id, *tags, remove=remove)
    except SnippetNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "message": f"{'Removed' if remove else 'Added'} tags {tags} for snippet with id {snippet_id}."
    }
