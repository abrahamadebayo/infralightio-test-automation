"""Locust load test definition for standalone load testing.

Run with:  locust -f locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:8080
"""

from locust import HttpUser, between, task

from src.config import settings


class APIUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.client.auth = settings.user1.auth_tuple
        resp = self.client.post(
            f"{settings.base_path}/integrations",
            json={"name": f"locust-{self.environment.runner.user_count}", "type": "AWS"},
        )
        if resp.status_code in (200, 201):
            self.integration_id = resp.json()["id"]
        else:
            self.integration_id = None

    @task(3)
    def list_integrations(self):
        self.client.get(
            f"{settings.base_path}/integrations",
            name="/api/v1/integrations [GET]",
        )

    @task(2)
    def list_assets(self):
        if self.integration_id:
            self.client.get(
                f"{settings.base_path}/assets",
                params={"integrationId": self.integration_id},
                name="/api/v1/assets [GET]",
            )

    @task(1)
    def create_and_delete_asset(self):
        if not self.integration_id:
            return
        resp = self.client.post(
            f"{settings.base_path}/assets",
            json={
                "name": "locust-asset",
                "description": "load test",
                "integration_id": self.integration_id,
            },
            name="/api/v1/assets [POST]",
        )
        if resp.status_code in (200, 201):
            asset_id = resp.json()["id"]
            self.client.delete(
                f"{settings.base_path}/assets/{asset_id}",
                name="/api/v1/assets/{id} [DELETE]",
            )
