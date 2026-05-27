"""Load tests — verify the API handles >= 1000 requests per minute."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from src.client import APIClient
from src.config import settings
from tests.helpers import unique_name


@pytest.mark.load
class TestLoadCapacity:

    TARGET_RPM = settings.load_test_target_rpm
    TEST_DURATION_SECONDS = 30
    NUM_WORKERS = 20

    def test_api_handles_target_rpm(self, user1_client: APIClient, integration_factory):
        integration = integration_factory(user1_client, unique_name("loadint"))

        success_count = 0
        error_count = 0
        start = time.monotonic()
        deadline = start + self.TEST_DURATION_SECONDS

        def make_request() -> bool:
            try:
                resp = user1_client.list_integrations()
                return resp.status_code == 200
            except Exception:
                return False

        with ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as pool:
            futures = []
            while time.monotonic() < deadline:
                futures.append(pool.submit(make_request))
                if len(futures) >= self.TARGET_RPM:
                    break

            for future in as_completed(futures):
                if future.result():
                    success_count += 1
                else:
                    error_count += 1

        elapsed = time.monotonic() - start
        rpm = (success_count / elapsed) * 60 if elapsed > 0 else 0

        assert rpm >= self.TARGET_RPM, (
            f"API throughput {rpm:.0f} RPM is below target of {self.TARGET_RPM} RPM "
            f"({success_count} successes, {error_count} errors in {elapsed:.1f}s)"
        )

    def test_api_stable_under_sustained_load(self, user1_client: APIClient, integration_factory):
        integration_factory(user1_client, unique_name("sustained"))

        errors_5xx = 0
        total = 0
        start = time.monotonic()
        deadline = start + min(self.TEST_DURATION_SECONDS, 15)

        def make_request() -> int:
            try:
                resp = user1_client.list_integrations()
                return resp.status_code
            except Exception:
                return 0

        with ThreadPoolExecutor(max_workers=self.NUM_WORKERS) as pool:
            futures = []
            while time.monotonic() < deadline:
                futures.append(pool.submit(make_request))

            for future in as_completed(futures):
                total += 1
                status = future.result()
                if 500 <= status < 600:
                    errors_5xx += 1

        error_rate = errors_5xx / total if total else 0
        assert error_rate < 0.01, (
            f"API error rate {error_rate:.1%} exceeds 1% threshold "
            f"({errors_5xx} / {total} requests returned 5xx)"
        )
