from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class CineBookTestRunner(DiscoverRunner):
    def run_tests(self, test_labels, **kwargs):
        with override_settings(SECURE_SSL_REDIRECT=False):
            return super().run_tests(test_labels, **kwargs)
