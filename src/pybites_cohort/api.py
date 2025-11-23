from typing import Generator, List, Optional

from decouple import config
from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, create_engine, select

from pybites_cohort.exceptions import SnippetNotFoundError
from pybites_cohort.models import Language, Snippet, Tag
from pybites_cohort.repo import DBSnippetRepo
from pybites_cohort.schemas import SnippetCreate, SnippetRead

DB_USER = config("DB_USER")
DB_PASS = config("DB_PASS")
DB_HOST = config("DB_HOST")
DB_PORT = config("DB_PORT")
DB_NAME = config("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, echo=False)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


app = FastAPI()


@app.get("/snippets/", response_model=List[SnippetRead])
def list_snippets(session: Session = Depends(get_session)):
    statement = select(Snippet)
    snippets = session.exec(statement).all()
    return snippets


@app.post("/snippets/", status_code=201)
def add_snippet(snippet_data: SnippetCreate, session: Session = Depends(get_session)):
    # Snippet erzeugen und ID erzeugen
    snippet = Snippet(
        title=snippet_data.title,
        code=snippet_data.code,
        description=snippet_data.description,
        favorite=snippet_data.favorite,
        language=Language(snippet_data.language),
    )
    session.add(snippet)
    session.flush()  # wichtig für snippet.id

    managed_tags = []
    for tag_name in snippet_data.tags:
        tag = session.exec(select(Tag).where(Tag.name == tag_name)).first()
        if not tag:
            tag = Tag(name=tag_name)
            session.add(tag)
            session.commit()
        managed_tags.append(tag)

    snippet.tags = managed_tags
    session.commit()
    session.refresh(snippet)

    return snippet


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
