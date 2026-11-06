import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import app  # noqa: E402


class YamlFormatterTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def validate(self, content, filename="test.yaml"):
        return self.client.post("/api/validate", json={"content": content, "filename": filename})

    def test_formats_valid_yaml(self):
        r = self.validate("a:   1\nb:\n    - x\n    - y\n")
        data = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(data["valid"])
        self.assertEqual(data["formatted"], "a: 1\nb:\n- x\n- y")
        self.assertEqual(data["lines"], 4)

    def test_reports_syntax_error_with_position(self):
        data = self.validate("a: [1, 2\nb: 3").get_json()
        self.assertFalse(data["valid"])
        self.assertIsNotNone(data["line"])
        self.assertIn("Line", data["error"])

    def test_multi_document_yaml(self):
        content = "apiVersion: v1\nkind: Service\n---\napiVersion: apps/v1\nkind: Deployment\n"
        data = self.validate(content).get_json()
        self.assertTrue(data["valid"], data.get("error"))
        self.assertEqual(data["documents"], 2)
        self.assertEqual(data["formatted"].count("---"), 2)
        self.assertIn("kind: Deployment", data["formatted"])

    def test_duplicate_keys_are_reported(self):
        data = self.validate("name: a\nimage: x\nname: b\n").get_json()
        self.assertTrue(data["valid"])
        dupes = [w for w in data["warnings"] if w["type"] == "duplicate-key"]
        self.assertEqual(len(dupes), 1)
        self.assertIn("'name' on line 3", dupes[0]["message"])

    def test_nested_duplicate_keys(self):
        data = self.validate("spec:\n  replicas: 1\n  replicas: 2\n").get_json()
        self.assertEqual(sum(w["type"] == "duplicate-key" for w in data["warnings"]), 1)

    def test_no_false_duplicates(self):
        data = self.validate("a:\n  x: 1\nb:\n  x: 2\n").get_json()
        self.assertEqual(data["warnings"], [])

    def test_unsafe_tags_are_rejected(self):
        data = self.validate("!!python/object/apply:os.system ['echo hi']").get_json()
        self.assertFalse(data["valid"])

    def test_empty_content(self):
        r = self.validate("   ")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.get_json()["valid"])

    def test_non_json_body(self):
        r = self.client.post("/api/validate", data="not json", content_type="text/plain")
        self.assertEqual(r.status_code, 400)

    def test_batch_validate(self):
        r = self.client.post("/api/batch-validate", json={"files": [
            {"filename": "ok.yaml", "content": "a: 1"},
            {"filename": "bad.yaml", "content": "a: [1"},
        ]})
        results = r.get_json()["results"]
        self.assertEqual([x["valid"] for x in results], [True, False])

    def test_batch_requires_list(self):
        self.assertEqual(self.client.post("/api/batch-validate", json={"files": "nope"}).status_code, 400)

    def test_index_is_served(self):
        with self.client.get("/") as r:
            self.assertEqual(r.status_code, 200)
            self.assertIn(b"<html", r.data.lower())

    def test_health(self):
        self.assertEqual(self.client.get("/health").get_json(), {"status": "healthy"})

    def test_debug_is_off(self):
        self.assertFalse(app.debug)


if __name__ == "__main__":
    unittest.main()
