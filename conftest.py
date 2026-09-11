import pytest


@pytest.fixture(autouse=True)
def _disable_ssl_redirect(settings):
    # CI гоняет тесты с DEBUG=False (как в проде), чтобы ловить реальные
    # прод-баги, но тогда включается SECURE_SSL_REDIRECT — Django
    # заворачивает любой запрос без HTTPS в 301, а test.Client всегда
    # ходит по HTTP. Отключаем только здесь, сама настройка в
    # tickethub/settings.py остаётся как есть для реального деплоя.
    settings.SECURE_SSL_REDIRECT = False
