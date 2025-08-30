from codeop import CommandCompiler
from enum import Enum
from typing import Dict, Type, Any

from src.interfaces import Command
from src.queues.implementations.inmemory import InMemoryQueue
from src.queues.interfaces import AsyncQueue, Queue

from src.queues.tasks import TaskVideo, TaskLink
from src.abstract import BaseFactory


class QueueType(Enum):
    IN_MEMORY = "in_memory"


class TaskType(Enum):
    VIDEO = "video"
    LINK = "link"


class QueueFactory(BaseFactory[QueueType, Queue]):
    pass


class TaskFactory(BaseFactory[TaskType, Command]):
    pass


QueueFactory.register(QueueType.IN_MEMORY, InMemoryQueue)
TaskFactory.register(TaskType.VIDEO, TaskVideo)
TaskFactory.register(TaskType.LINK, TaskLink)
