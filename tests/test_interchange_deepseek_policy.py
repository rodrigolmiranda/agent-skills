import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skills" / "interchange" / "references"


class DeepSeekPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((REFERENCES / "policy.json").read_text())
        self.commands = json.loads((REFERENCES / "commands.json").read_text())

    def test_only_approved_deepseek_profiles_are_flash_high_and_max(self):
        profiles = {
            profile["id"]: profile
            for profile in self.policy["profiles"]
            if profile["id"].startswith("worker-deepseek-")
        }

        self.assertEqual(
            set(profiles),
            {"worker-deepseek-flash-high", "worker-deepseek-flash-max"},
        )
        self.assertEqual({profile["model"] for profile in profiles.values()}, {"opencode-go/deepseek-flash"})
        self.assertEqual({profile["effort"] for profile in profiles.values()}, {"high", "max"})

    def test_deepseek_commands_use_exact_flash_code_and_never_pro(self):
        profiles = {
            name: profile
            for name, profile in self.commands["profiles"].items()
            if name.startswith("worker-deepseek-")
        }

        self.assertEqual(
            set(profiles),
            {"worker-deepseek-flash-high", "worker-deepseek-flash-max"},
        )
        for profile in profiles.values():
            self.assertIn("opencode-go/deepseek-flash", profile["start"])
            self.assertIn("opencode-go/deepseek-flash", profile["resume"])
            self.assertNotIn("opencode-go/deepseek-v4-pro", profile["start"])
            self.assertNotIn("opencode-go/deepseek-v4-pro", profile["resume"])

    def test_unavailability_requires_cross_house_reroute(self):
        substitution = self.commands["substitution"]
        self.assertIn("another approved house", substitution)
        self.assertIn("forbidden fallbacks", substitution)


if __name__ == "__main__":
    unittest.main()
