from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class LRUCache(Generic[T]):
    def __init__(self, max_size: int) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._max_size = max_size
        self._items: OrderedDict[str, T] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Optional[T]:
        with self._lock:
            value = self._items.get(key)
            if value is None:
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: str, value: T) -> None:
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
            self._items[key] = value
            if len(self._items) > self._max_size:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


@dataclass(frozen=True)
class EmojiImageKey:
    path: str
    size: int


class EmojiImageCache:
    def __init__(self, max_size: int) -> None:
        self._cache: LRUCache[object] = LRUCache(max_size)

    def get(self, key: EmojiImageKey) -> Optional[object]:
        return self._cache.get(f"{key.path}:{key.size}")

    def set(self, key: EmojiImageKey, value: object) -> None:
        self._cache.set(f"{key.path}:{key.size}", value)


@dataclass(frozen=True)
class ConversionResult:
    grid: list[list[str]]
    grid_w: int
    grid_h: int
    grid_spaced: Optional[list[str]]
    preview_png: Optional[bytes]
    dataset_version: str
    warnings: list[str]


class ConversionCache:
    def __init__(self, max_size: int) -> None:
        self._cache: LRUCache[ConversionResult] = LRUCache(max_size)

    def get(self, key: str) -> Optional[ConversionResult]:
        return self._cache.get(key)

    def set(self, key: str, value: ConversionResult) -> None:
        self._cache.set(key, value)


@dataclass(frozen=True)
class FeatureCacheKey:
    lab: tuple[int, int, int]
    edge: int
    alpha: int


class FeatureMemoCache:
    def __init__(self, max_size: int) -> None:
        self._cache: LRUCache[int] = LRUCache(max_size)

    def get(self, key: FeatureCacheKey) -> Optional[int]:
        return self._cache.get(self._key_to_str(key))

    def set(self, key: FeatureCacheKey, value: int) -> None:
        self._cache.set(self._key_to_str(key), value)

    def _key_to_str(self, key: FeatureCacheKey) -> str:
        return f"{key.lab[0]}:{key.lab[1]}:{key.lab[2]}:{key.edge}:{key.alpha}"
