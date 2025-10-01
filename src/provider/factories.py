from src.provider.interfaces import AsyncTask
from src.provider.tasks import AsyncTaskType, AsyncTaskBrowserVideo, AsyncTaskVideo
from src.abstract import BaseFactory


class AsyncTaskFactory(BaseFactory[AsyncTaskType, AsyncTask]):
    pass


AsyncTaskFactory.register(AsyncTaskType.VIDEO, AsyncTaskVideo)
