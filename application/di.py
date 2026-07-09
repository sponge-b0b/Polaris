from dishka import Provider
from dishka import Scope

from application.services.di import AppServicesDIProvider


class ApplicationDIProvider(Provider):
    scope = Scope.APP

    def __init__(self):
        super().__init__()

        self.from_context(
            AppServicesDIProvider(),
            scope=Scope.APP,
        )
