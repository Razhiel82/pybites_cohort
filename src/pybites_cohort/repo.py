from abc import ABC, abstractmethod

# from pathlib import Path
from typing import Sequence

# from sqlmodel import Session, select
from .exceptions import SnippetNotFoundError
from .models import Snippet


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
    def search(self, snippet_title: str) -> None:
        pass

    @abstractmethod
    def favorite_on(self, snippet_id: int) -> None:
        pass

    @abstractmethod
    def favorite_off(self, snippet_id: int) -> None:
        pass

    # @abstractmethod
    # def tag(self, snippet_id: int, *tags: str, remove: bool = False, sort: bool = True) -> None:
    #     pass


class InMemorySnippetRepo(SnippetRepository):
    def __init__(self):
        self._data = {}

    def add(self, snippet: Snippet) -> None:
        next_id = max(self._data.keys(), default=0) + 1
        self._data[next_id] = snippet

    def list(self) -> Sequence[Snippet]:
        return list(self._data.values())

    def get(self, snippet_id: int) -> Snippet | None:
        return self._data.get(snippet_id)

    def delete(self, snippet_id: int) -> None:
        if snippet_id not in self._data:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")
        self._data.pop(snippet_id, None)

    def search(self, snippet_title: str) -> Sequence[Snippet]:
        return [
            snippet
            for snippet in self._data.values()
            if snippet_title.lower() in snippet.title.lower()
        ]
        # return [snippet for snippet in self._data.values() if snippet_title.lower() in snippet.title.lower() and language.lower() == snippet.language]

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


class DBSnippetRepo(SnippetRepository):
    def __init__(self, session) -> None:
        self.session = session

    def add(self, snippet: Snippet):
        self.session.add(snippet)
        self.session.commit()

    def list(self) -> Sequence[Snippet]:
        return self.session.query(self.model).all

    def get(self, snippet_id: int) -> Snippet | None:
        return self.session.query(self.model).get(snippet_id)

    def delete(self, snippet_id: int) -> None:
        snippet = self.session.get(Snippet, snippet_id)
        if not snippet:
            raise SnippetNotFoundError(f"Snippet with id {snippet_id} not found")
        self.session.delete(snippet)
        self.session.commit()
