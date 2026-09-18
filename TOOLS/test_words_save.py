"""Save integration tests use only isolated temporary repositories."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import words_save as save


def payload():
    return {
        "headword": "measure", "username": "qtu",
        "content": {
            "forms": [{"ref": "base", "form": "measure", "role": "base"},
                      {"ref": "plural", "form": "measures", "role": "plural"}],
            "meanings": [{"ref": "meaning", "form_id": "@base", "pos": "noun",
                          "meaning": "biện pháp", "usage": "take measures", "tier": "core"}],
            "phrases": [{"ref": "phrase", "form_id": "@base", "meaning_id": "@meaning",
                         "phrase": "take measures", "meaning": "thực hiện các biện pháp",
                         "type": "collocation", "tier": "core", "words": "2", "status": "active"}],
            "examples": [{"ref": "example", "form_id": "@plural", "phrase_id": "@phrase",
                          "sentence": "We must take measures to protect customer data.",
                          "vi_meaning": "Chúng ta phải thực hiện các biện pháp để bảo vệ dữ liệu khách hàng.",
                          "source": "test"}],
            "tests": [{"ref": "test", "form_id": "@plural", "phrase_id": "@phrase",
                       "example_id": "@example", "question": "We must ___ ___ to protect customer data.",
                       "vi_context": "Chúng ta phải thực hiện các biện pháp để bảo vệ dữ liệu khách hàng.",
                       "correct_answer": "take; measures", "test_type": "fb", "status": "active"}],
        },
        "events": [{"test_id": "@test", "attempts": [
            {"answer": "measure", "grade": "incorrect"},
            {"answer": "take measures", "grade": "correct"}],
            "mistake_note": "Missing take and plural -s."}],
    }


class SaveTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "WORDS").mkdir()
        (self.root / "WORDS/WORDS-INDEX.csv").write_bytes(save.render([], "index"))

    def read(self, kind):
        path = self.root / save.paths("measure", "qtu")[kind]
        return save.parse(path.read_bytes(), kind)

    def test_cold_save_and_exact_retry(self):
        plan = save.prepare(self.root, payload())
        self.assertEqual(list((self.root / "WORDS").iterdir()), [self.root / "WORDS/WORDS-INDEX.csv"])
        self.assertEqual(save.apply(self.root, plan), 8)
        self.assertEqual(save.apply(self.root, json.loads(json.dumps(plan))), 0)
        event = self.read("history")[0]
        self.assertEqual(event["result"], "incorrect_corrected")
        self.assertEqual(event["attempts"], "2")
        self.assertEqual(self.read("stats")[0]["value"], "1")

    def test_matching_content_reused_for_new_round(self):
        first = save.prepare(self.root, payload())
        save.apply(self.root, first)
        before = {k: self.read(k) for k in save.PREFIX}
        again = payload()
        again["events"][0]["attempts"] = [{"answer": "take measures", "grade": "correct"}]
        second = save.prepare(self.root, again)
        save.apply(self.root, second)
        for k in save.PREFIX:
            self.assertEqual(self.read(k), before[k])
        self.assertEqual(len(self.read("history")), 2)
        self.assertEqual(self.read("index")[0]["updated_at"],
                         save.parse(first["files"]["index"]["after"].encode("utf-8"), "index")[0]["updated_at"])

    def test_partial_write_retry_uses_same_ids(self):
        plan = save.prepare(self.root, payload())
        original_replace = save.os.replace
        calls = 0

        def interrupted(src, dest):
            nonlocal calls
            calls += 1
            if calls == 4:
                raise OSError("simulated interruption")
            return original_replace(src, dest)

        with patch.object(save.os, "replace", interrupted):
            with self.assertRaises(OSError):
                save.apply(self.root, plan)
        self.assertGreater(save.apply(self.root, plan), 0)
        self.assertEqual(len(self.read("history")), 1)
        self.assertEqual(save.apply(self.root, plan), 0)

    def test_concurrent_change_rejected_before_any_write(self):
        plan = save.prepare(self.root, payload())
        index = self.root / "WORDS/WORDS-INDEX.csv"
        index.write_text("external edit\n")
        with self.assertRaisesRegex(ValueError, "Concurrent change"):
            save.apply(self.root, plan)
        self.assertFalse((self.root / "WORDS/mea").exists())

    def test_unfinished_question_rejected(self):
        item = payload()
        item["events"][0]["attempts"].pop()
        with self.assertRaisesRegex(ValueError, "Unfinished"):
            save.prepare(self.root, item)
        self.assertFalse((self.root / "WORDS/mea").exists())

    def test_invalid_references_and_blanks_rejected(self):
        for field, value in [("phrase_id", "@missing"), ("correct_answer", "take")]:
            with self.subTest(field=field):
                item = payload()
                item["content"]["tests"][0][field] = value
                with self.assertRaises(ValueError):
                    save.prepare(self.root, item)
        self.assertFalse((self.root / "WORDS/mea").exists())

    def test_existing_test_reference(self):
        save.apply(self.root, save.prepare(self.root, payload()))
        test_id = self.read("tests")[0]["id"]
        item = {"headword": "measure", "username": "qtu",
                "content": {"tests": [{"ref": "old", "id": test_id}]},
                "events": [{"test_id": "@old", "attempts": [
                    {"answer": "take measure", "grade": "partial"},
                    {"answer": "take measures", "grade": "correct"}]}]}
        save.apply(self.root, save.prepare(self.root, item))
        self.assertEqual(len(self.read("tests")), 1)
        self.assertEqual(self.read("history")[-1]["result"], "partial_corrected")

    def test_alternative_then_original_round_trip(self):
        item = payload()
        item["content"]["tests"][0]["correct_answer"] = "take; measures | adopt; measures"
        item["events"][0]["attempts"] = [
            {"answer": "adopt measures", "grade": "partial"},
            {"answer": "take measures", "grade": "correct"}]
        item["events"][0]["mistake_note"] = 'Valid alternative, "adopt measures"; original recalled.'
        plan = save.prepare(self.root, item)
        save.apply(self.root, plan)
        self.assertEqual(self.read("tests")[0]["correct_answer"], "take; measures | adopt; measures")
        event = self.read("history")[0]
        self.assertEqual((event["result"], event["attempts"], event["first_try"]),
                         ("partial_corrected", "2", "FALSE"))
        self.assertEqual(event["mistake_note"], item["events"][0]["mistake_note"])
        self.assertEqual(save.apply(self.root, plan), 0)

    def test_invalid_alternative_lists_rejected(self):
        for answer in ("take; measures |", "| take; measures",
                       "take; measures | adopt", "take; measures | adopt;",
                       "take; measures | TAKE ; measures",
                       "adopt; measures | take; measures"):
            with self.subTest(answer=answer):
                item = payload()
                item["content"]["tests"][0]["correct_answer"] = answer
                with self.assertRaises(ValueError):
                    save.prepare(self.root, item)
        self.assertFalse((self.root / "WORDS/mea").exists())

    def test_alternative_without_original_stays_unfinished(self):
        item = payload()
        item["content"]["tests"][0]["correct_answer"] = "take; measures | adopt; measures"
        item["events"][0]["attempts"] = [{"answer": "adopt measures", "grade": "partial"}]
        with self.assertRaisesRegex(ValueError, "Unfinished"):
            save.prepare(self.root, item)

    def test_extended_answer_list_preserves_historical_test(self):
        save.apply(self.root, save.prepare(self.root, payload()))
        old_test, old_history = self.read("tests")[0], self.read("history")[0]
        item = payload()
        item["content"]["tests"][0]["correct_answer"] = "take; measures | adopt; measures"
        save.apply(self.root, save.prepare(self.root, item))
        self.assertEqual(self.read("tests")[0], old_test)
        self.assertEqual(self.read("history")[0], old_history)
        self.assertEqual(len(self.read("tests")), 2)
        self.assertNotEqual(self.read("history")[-1]["test_id"], old_test["id"])

    def test_path_escape_and_symlink_rejected(self):
        item = payload()
        item["headword"] = "../../escape"
        with self.assertRaises(ValueError):
            save.prepare(self.root, item)
        (self.root / "WORDS/mea").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            save.prepare(self.root, payload())

    def test_plan_cannot_write_arbitrary_file(self):
        plan = save.prepare(self.root, payload())
        plan["files"]["forms"]["path"] = "AGENTS.md"
        with self.assertRaisesRegex(ValueError, "Invalid plan path"):
            save.apply(self.root, plan)
        self.assertFalse((self.root / "AGENTS.md").exists())

    def test_incomplete_bundle_requires_reconciliation(self):
        folder = self.root / "WORDS/mea/measure"
        folder.mkdir(parents=True)
        (folder / "measure.csv").write_bytes(save.render([], "forms"))
        with self.assertRaisesRegex(ValueError, "Incomplete existing bundle"):
            save.prepare(self.root, payload())

    def test_a_failed_plan_can_be_retried_after_full_save(self):
        plan = save.prepare(self.root, payload())
        save.apply(self.root, plan)
        # Simulate interrupted process after files were saved but before success was reported.
        self.assertEqual(save.apply(self.root, copy.deepcopy(plan)), 0)


if __name__ == "__main__":
    unittest.main()

