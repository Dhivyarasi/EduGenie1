import unittest

from fastapi.testclient import TestClient

from main import app


class AssistantApiTests(unittest.TestCase):
    def setUp(self):
        self.client_context = TestClient(app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)

    def test_health_reports_offline_provider(self):
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["provider"], "offline")
        self.assertTrue(response.json()["ready"])

    def test_offline_ocean_answer(self):
        response = self.client.post("/api/assistant", json={"mode": "answer", "prompt": "Which is the largest ocean?"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Pacific Ocean", response.json()["content"])
        self.assertEqual(response.json()["source"], "offline")

    def test_explains_pythagorean_theorem_with_an_example(self):
        response = self.client.post("/api/assistant", json={"mode": "explain", "prompt": "The Pythagorean theorem"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("3 and 4", response.json()["content"])

    def test_offline_quiz_is_interactive_and_has_valid_answers(self):
        response = self.client.post("/api/assistant", json={"mode": "quiz", "prompt": "The Pythagorean theorem"})

        self.assertEqual(response.status_code, 200)
        quiz = response.json()["quiz"]
        self.assertEqual(len(quiz), 3)
        for question in quiz:
            self.assertGreaterEqual(question["answer_index"], 0)
            self.assertLess(question["answer_index"], len(question["choices"]))

    def test_offline_summary_uses_supplied_passage(self):
        passage = "Oceans cover most of Earth. Rivers carry fresh water. Both support life."
        response = self.client.post("/api/assistant", json={"mode": "summarize", "prompt": passage})

        self.assertEqual(response.status_code, 200)
        self.assertIn("Oceans cover most of Earth.", response.json()["content"])
        self.assertNotIn("Both support life.", response.json()["content"])

    def test_sql_path_has_timeline_practice_and_project(self):
        response = self.client.post("/api/assistant", json={"mode": "path", "prompt": "Learn SQL"})

        self.assertEqual(response.status_code, 200)
        for detail in ("Weeks 1–2", "Practice:", "Project:"):
            self.assertIn(detail, response.json()["content"])

    def test_offline_recommendation_gives_a_practical_next_step(self):
        response = self.client.post("/api/assistant", json={"mode": "recommend", "prompt": "I know basic SQL SELECT"})

        self.assertEqual(response.status_code, 200)
        self.assertIn("join two tables", response.json()["content"])

    def test_prompt_validation_rejects_blank_and_oversize_input(self):
        blank = self.client.post("/api/assistant", json={"mode": "answer", "prompt": " "})
        long = self.client.post("/api/assistant", json={"mode": "answer", "prompt": "a" * 12001})

        self.assertEqual(blank.status_code, 422)
        self.assertEqual(long.status_code, 422)

    def test_static_dashboard_loads(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("EduGenie", response.text)
        self.assertEqual(self.client.get("/app.js").status_code, 200)
        self.assertEqual(self.client.get("/styles.css").status_code, 200)


if __name__ == "__main__":
    unittest.main()