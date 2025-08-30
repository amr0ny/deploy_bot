
from src.provider.interfaces import AsyncTask
from src.provider.tasks import TaskBrowserType, TaskBrowserVideo
from src.abstract import BaseFactory


class TaskBrowserFactory(BaseFactory[TaskBrowserType, AsyncTask]):
    pass


TaskBrowserFactory.register(TaskBrowserType.VIDEO, TaskBrowserVideo)
