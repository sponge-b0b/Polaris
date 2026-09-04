from dishka import Provider, Scope

from integration.clients.di import IntegrationClientsDIProvider
from integration.providers.di import IntegrationProvidersDIProvider


class IntegrationDIProvider(Provider):
    scope = Scope.APP

    def __init__(self):
        super().__init__()

        self.from_context(
            IntegrationClientsDIProvider(),
            scope=Scope.APP,
        )
        self.from_context(
            IntegrationProvidersDIProvider(),
            scope=Scope.APP,
        )
