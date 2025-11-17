from typing import Optional

from decouple import config
from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, create_engine

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
