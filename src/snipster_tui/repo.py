from abc import ABC, abstractmethod

# from pathlib import Path
from typing import Dict, List, Optional, Sequence

from sqlalchemy import event
from sqlalchemy.orm import selectinload, subqueryload
from sqlmodel import Session, select

from snipster_tui.exceptions import SnippetNotFoundError
from snipster_tui.models import Language, Snippet, Tag


@event.listens_for(Session, "after_flush")
def delete_orphan_tags(session, flush_context):
    session.query(Tag).filter(~Tag.snippets.any()).delete(synchronize_session=False)


class SnippetRepository(ABC):  # pragma : no cover
    @abstractmethod
    def add(self, snippet: Snippet) -> None:
        pass

    @abstractmethod
    def list(self) -> Sequence[Snippet]:
        pass

    @abstractmethod
    def get(self, snippet_id: int) -> Snippet | None:
        pass

    @abstractmethod
    def delete(self, snippet_id: int) -> None:
        pass

    @abstractmethod
    def search(
        self, snippet_title: str, language: Optional[Language] = None
    ) -> Sequence[Snippet]:
        pass

    @abstractmethod
    def favorite_on(self, snippet_id: int) -> None:
        pass

    @abstractmethod
    def favorite_off(self, snippet_id: int) -> None:
        pass

    @abstractmethod
    def tag(
        self, snippet_id: int, *tags: str, remove: bool = False, sort: bool = True
    ) -> None:
        pass

    @abstractmethod
    def list_favorites(self) -> Sequence[Snippet]:
        pass


class InMemorySnippetRepo(SnippetRepository):
    def __init__(self):
        self._data: Dict[int, Snippet] = {}
        self._next_id = 1

    def add(self, snippet: Snippet) -> None:
        snippet.id = self._next_id
        self._data[self._next_id] = snippet
        self._next_id += 1

    def list(self, favorite: bool | None = None) -> Sequence[Snippet]:
        if favorite is True:
            return [
                snippet
                for snippet in self._data.values()
                if snippet.favorite == favorite
            ]
        return list(self._data.values())

    def get(self, snippet_id: int) -> Snippet | None:
        return self._data.get(snippet_id)

    def add_all(self, snippet: Snippet) -> None:
        for snip in snippet:
            self.add(snip)

    def delete(self, snippet_id: int) -> None:
        if snippet_id not in self._data:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")
        self._data.pop(snippet_id, None)

    def search(
        self, snippet_title: str, language: Language | None = None
    ) -> Sequence[Snippet]:
        return [
            snippet
            for snippet in self._data.values()
            if snippet_title.lower() in snippet.title.lower()
            and (language is None or language == snippet.language)
        ]

    def favorite_on(self, snippet_id: int) -> None:
        snippet = self.get(snippet_id)
        if snippet_id not in self._data:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")
        elif snippet.favorite is False:
            snippet.favorite = True

    def favorite_off(self, snippet_id: int) -> None:
        snippet = self.get(snippet_id)
        if snippet_id not in self._data:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")
        elif snippet.favorite is True:
            snippet.favorite = False

    def tag(
        self, snippet_id: int, *tags: str, remove: bool = False, sort: bool = True
    ) -> None:
        snippet = self.get(snippet_id)
        if snippet_id not in self._data:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")
        if not hasattr(snippet, "tags"):
            snippet.tags = []
        tag_objs = [Tag(name=tag_name) for tag_name in tags]
        if remove:
            snippet.tags = [tag for tag in snippet.tags if tag.name not in tags]
        else:
            existing_tag_names = {tag.name for tag in snippet.tags}
            for tag_obj in tag_objs:
                if tag_obj.name not in existing_tag_names:
                    snippet.tags.append(tag_obj)
                    existing_tag_names.add(tag_obj.name)

        if sort:
            snippet.tags = sorted(snippet.tags, key=lambda tag: tag.name)

    def list_favorites(self) -> Sequence[Snippet]:
        return [snippet for snippet in self._data.values() if snippet.favorite]


class DBSnippetRepo(SnippetRepository):
    def __init__(self, session) -> None:
        self.session = session

    def add(self, snippet: Snippet) -> None:
        self.session.add(snippet)
        self.session.commit()

    def list(self, favorite: bool | None = None):
        query = select(Snippet).options(subqueryload(Snippet.tags))
        if favorite:
            query = query.where(Snippet.favorite)
        result = self.session.exec(query)
        return result.unique().all()

    def get(self, snippet_id: int) -> Snippet | None:
        stmt = (
            select(Snippet)
            .where(Snippet.id == snippet_id)
            .options(selectinload(Snippet.tags))
        )
        return self.session.exec(stmt).first()

    def delete(self, snippet_id: int) -> None:
        snippet = self.session.get(Snippet, snippet_id)
        if not snippet:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")
        self.session.delete(snippet)
        self.session.commit()

    def search(
        self, snippet_title: str, language: Optional[Language] = None
    ) -> List[Snippet]:
        statement = select(Snippet).where(Snippet.title.ilike(f"%{snippet_title}%"))
        if language:
            statement = statement.where(Snippet.language == language)
        result = self.session.exec(statement)
        return result.all()

    def favorite_on(self, snippet_id: int) -> None:
        snippet = self.session.get(Snippet, snippet_id)
        if not snippet:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")
        snippet.favorite = True
        self.session.add(snippet)
        self.session.commit()

    def favorite_off(self, snippet_id: int) -> None:
        snippet = self.session.get(Snippet, snippet_id)
        if not snippet:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")
        snippet.favorite = False
        self.session.add(snippet)
        self.session.commit()

    def tag(self, snippet_id: int, *tags: str, remove: bool = False, sort: bool = True):
        snippet = self.get(snippet_id)
        if not snippet:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")

        if remove:
            for tag in [t for t in snippet.tags if t.name in tags]:
                snippet.tags.remove(tag)

        else:
            existing_tag_names = {tag.name for tag in snippet.tags}
            for tag_name in tags:
                if tag_name not in existing_tag_names:
                    existing_tag = self.session.exec(
                        select(Tag).where(Tag.name == tag_name)
                    ).first()
                    if existing_tag:
                        snippet.tags.append(existing_tag)
                    else:
                        new_tag = Tag(name=tag_name)
                        snippet.tags.append(new_tag)

        if sort:
            snippet.tags.sort(key=lambda tag: tag.name)

        self.session.add(snippet)
        self.session.commit()

    def list_favorites(self) -> Sequence[Snippet]:
        statement = select(Snippet).where(Snippet.favorite)
        return self.session.exec(statement).all()
