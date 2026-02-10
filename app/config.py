"""
Модуль для инициализации конфигурации сервиса
"""
from os import (_Environ,
                environ,
                path)
from typing import get_type_hints

from dotenv import load_dotenv

from .constants import Constants
from .environments import Environments
from .errors.app_config_error import AppConfigError


def __load_environments():
    if path.exists(Constants.ENV_FILE_PATH):
        load_dotenv(
            path.join(
                Constants.ENV_FILE_PATH,
                Constants.LOCAL_ENV_FILE
            )
        )


__load_environments()


class AppConfig(Environments):
    """
    Класс для инициализации конфигурации сервиса

    Map environment variables to class fields according to these rules:
      - Field won't be parsed unless it has a type annotation
      - Field will be skipped if not in all caps
      - Class field and environment variable name are the same
    """

    def __init__(self, env: _Environ):
        for field in self.__annotations__:

            # Raise AppConfigError if required field not supplied
            default_value = getattr(self, field, None)
            if default_value is None and env.get(field) is None:
                raise AppConfigError(f'The {field} field is required')

            # Cast env var value to expected type
            # and raise AppConfigError on failure
            var_type = get_type_hints(AppConfig)[field]
            try:
                if var_type == int:
                    value = int(env.get(field, default_value))
                else:
                    value = var_type(env.get(field, default_value))

                self.__setattr__(field, value)

            except AppConfigError as exception:
                raise AppConfigError(
                    f'Unable to cast value of "{env[field]}" to ' +
                    f'type "{var_type}" for "{field}" field'
                ) from exception

    def __repr__(self):
        return str(self.__dict__)


# Expose Config object for app to import
Config = AppConfig(environ)

if __name__ == '__main__':
    print(Config.LOG_LEVEL)