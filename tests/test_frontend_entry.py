# ruff: noqa: E402

import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
os.environ.setdefault("BOOK_AGENT_TRANSLATION_BACKEND", "echo")
os.environ.setdefault("BOOK_AGENT_TRANSLATION_MODEL", "echo-worker")
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from book_agent.app.main import create_app
from book_agent.core.config import get_settings


class FrontendEntryTest(unittest.TestCase):
    def tearDown(self) -> None:
        get_settings.cache_clear()
        os.environ.pop("BOOK_AGENT_CORS_ALLOW_ORIGINS", None)

    def _build_client(self) -> TestClient:
        get_settings.cache_clear()
        return TestClient(create_app())

    def test_root_returns_minimal_service_entry(self) -> None:
        with self._build_client() as client:
            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        body = response.text
        self.assertIn("Book Agent Service", body)
        self.assertIn("standalone React/Vite frontend", body)
        self.assertIn("Swagger UI", body)
        self.assertIn("/v1/docs", body)
        self.assertIn("/v1/openapi.json", body)
        self.assertIn("/v1/health", body)

    def test_cors_allowlist_enables_preflight_for_api(self) -> None:
        os.environ["BOOK_AGENT_CORS_ALLOW_ORIGINS"] = "https://workspace.example"

        with self._build_client() as client:
            response = client.options(
                "/v1/health",
                headers={
                    "Origin": "https://workspace.example",
                    "Access-Control-Request-Method": "GET",
                },
            )

        self.assertIn(response.status_code, {200, 204})
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "https://workspace.example",
        )
        self.assertEqual(
            response.headers.get("access-control-allow-credentials"),
            "true",
        )
