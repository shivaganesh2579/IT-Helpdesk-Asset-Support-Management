import os
import tempfile
import unittest
from pathlib import Path

from app import app, init_db


class HelpdeskAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test_helpdesk.db"
        app.config.update(TESTING=True, DATABASE=str(db_path), SECRET_KEY="unit-test-secret")
        # The application constant is also used by init_db, so direct seed invocation is redirected.
        import app as app_module
        self.original_database_path = app_module.DATABASE_PATH
        app_module.DATABASE_PATH = db_path
        init_db(reset=True)
        self.client = app.test_client()

    def tearDown(self):
        import app as app_module
        app_module.DATABASE_PATH = self.original_database_path
        self.temp_dir.cleanup()

    def test_dashboard_renders_and_database_is_connected(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Ticket activity", response.data)
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertIn(b'"database":"connected"', health.data)

    def test_ticket_list_and_reports_render(self):
        self.assertEqual(self.client.get("/tickets").status_code, 200)
        reports = self.client.get("/reports")
        self.assertEqual(reports.status_code, 200)
        self.assertIn(b"Warranty expiry watch", reports.data)

    def test_create_ticket_persists_a_ticket_and_status_history(self):
        response = self.client.post("/tickets/new", data={
            "title": "Test request from unit test",
            "description": "Unit test validates ticket creation flow.",
            "ticket_type": "Incident",
            "requester_id": "2",
            "ticket_category_id": "1",
            "priority_id": "3",
            "asset_id": "1",
            "impact": "Moderate",
            "urgency": "Low",
            "affected_service": "Unit test",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"was created successfully", response.data)
        self.assertIn(b"Test request from unit test", response.data)

    def test_asset_unique_tag_is_enforced(self):
        response = self.client.post("/assets/new", data={
            "asset_tag": "AST-1001", "asset_name": "Duplicate asset",
            "asset_category_id": "1", "department_id": "1", "manufacturer": "Test",
            "model_number": "Test Model", "purchase_date": "2026-01-01", "asset_status": "In Use",
            "location": "Lab", "assigned_user_id": "",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Could not register asset", response.data)

    def test_invalid_status_transition_is_rejected(self):
        # Seeded ticket 1 is In Progress. Direct transition to Open is intentionally not in its allowed set.
        response = self.client.post("/tickets/1/status", data={"status": "Open", "note": "test"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Status transition", response.data)

    def test_csv_export(self):
        response = self.client.get("/reports/export.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Ticket Number,Type,Title,Status", response.data)


if __name__ == "__main__":
    unittest.main()
