from dishka import Provider, Scope

from core.llm.di import CoreLLMsDIProvider
from core.storage.di import CoreStorageDIProvider


class CoreDIProvider(Provider):
    scope = Scope.APP

    def __init__(self):
        super().__init__()

        self.from_context(
            CoreLLMsDIProvider(),
            scope=Scope.APP,
        )
        self.from_context(
            CoreStorageDIProvider(),
            scope=Scope.APP,
        )
