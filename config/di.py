from dishka import Provider, Scope, provide

from config.settings import Settings


class ConfigSettingsDIProvider(Provider):
    # This class provides components for the entire lifetime of the app
    scope = Scope.APP

    @provide
    def provide_settings(self) -> Settings:
        return Settings()
