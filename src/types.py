from typing import Dict, Type, Any, TypeVar, Generic
from enum import Enum

TEnum = TypeVar("TEnum", bound=Enum)
TBase = TypeVar("TBase")


class BaseFactory(Generic[TEnum, TBase]):
    _registry: Dict[TEnum, Type[TBase]] = {}

    @classmethod
    def register(cls, key: TEnum, impl: Type[TBase]) -> None:
        """Регистрирует тип"""
        cls._registry[key] = impl

    @classmethod
    def create(cls, key: TEnum, **kwargs: Any) -> TBase:
        if key not in cls._registry:
            raise ValueError(f"Unknown type: {key}")
        return cls._registry[key](**kwargs)
