from typing import List, Optional

from decouple import config
from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, create_engine

from pybites_cohort.exceptions import SnippetNotFoundError
from pybites_cohort.models import Language
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


@app.get("/")
def root():
    return {"message": "Snipster API is alive!"}


@app.get("/snippets/")
def list(session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    return repo.list()


@app.delete("/snippets/{snippet_id}")
def delete(snippet_id: int, session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    snippet = repo.delete(snippet_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return snippet


@app.get("/snippets/search")
def search(
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
def get(snippet_id: int, session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    snippet = repo.get(snippet_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return snippet


@app.post("/snippets/{snippet_id}/fav_on")
def fav_on(snippet_id: int, session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    snippet = repo.favorite_on(snippet_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return {"message": f"Snippet {snippet_id} is a favorite now."}


@app.post("/snippets/{snippet_id}/fav_off")
def fav_off(snippet_id: int, session: Session = Depends(get_session)):
    repo = DBSnippetRepo(session)
    snippet = repo.favorite_off(snippet_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return {"message": f"Snippet {snippet_id} is no favorite anymore."}


@app.post("/snippets/{snippet_id}/tags")
def tag(
    snippet_id: int,
    tags: List[str],
    remove: Optional[bool] = False,
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
