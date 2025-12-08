from abc import ABC, abstractmethod

# from pathlib import Path
from typing import Dict, List, Optional, Sequence

from sqlmodel import select

from snipster_tui.exceptions import SnippetNotFoundError
from snipster_tui.models import Language, Snippet


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
    def list_favorites(self) -> Sequence[Snippet]:
        pass

    @abstractmethod
    def update(self, snippet: Snippet) -> None:
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

    def list_favorites(self) -> Sequence[Snippet]:
        return [snippet for snippet in self._data.values() if snippet.favorite]

    def update(self, snippet: Snippet) -> None:
        """Update bestehendes Snippet (ID unverändert!)"""
        if snippet.id not in self._data:
            raise SnippetNotFoundError(f"Snippet {snippet.id} not found")

        existing = self._data[snippet.id]
        for key, value in snippet.model_dump(exclude={"id"}).items():
            setattr(existing, key, value)


class DBSnippetRepo(SnippetRepository):
    def __init__(self, session) -> None:
        self.session = session

    def add(self, snippet: Snippet) -> None:
        self.session.add(snippet)
        self.session.commit()

    def list(self, favorite: bool | None = None):
        query = select(Snippet)
        if favorite:
            query = query.where(Snippet.favorite)
        result = self.session.exec(query)
        return result.unique().all()

    def get(self, snippet_id: int) -> Snippet | None:
        stmt = select(Snippet).where(Snippet.id == snippet_id)
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

    def list_favorites(self) -> Sequence[Snippet]:
        statement = select(Snippet).where(Snippet.favorite)
        return self.session.exec(statement).all()

    def update(self, snippet: Snippet) -> None:
        """Update bestehendes Snippet (SQLAlchemy-sicher!)"""
        existing = self.session.get(Snippet, snippet.id)
        if not existing:
            raise SnippetNotFoundError(f"Snippet {snippet.id} not found")

        for key, value in snippet.model_dump(exclude={"id"}).items():
            setattr(existing, key, value)

        self.session.add(existing)
        self.session.commit()
