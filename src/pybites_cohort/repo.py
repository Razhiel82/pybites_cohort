from abc import ABC, abstractmethod

# from pathlib import Path
from typing import Sequence

# from sqlmodel import Session, select
from .exceptions import SnippetNotFoundError
from .models import Language, Snippet, Tag


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

    @abstractmethod
    def tag(
        self, snippet_id: int, *tags: str, remove: bool = False, sort: bool = True
    ) -> None:
        pass


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
