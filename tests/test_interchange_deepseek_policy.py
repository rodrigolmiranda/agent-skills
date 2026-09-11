import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "skills" / "interchange" / "references"

# The one approved DeepSeek route, and the codes that look like it but are not.
FLASH = "opencode-go/deepseek-v4.1-flash"
FORBIDDEN = (
    "opencode-go/deepseek-v4-pro",
    "opencode-go/deepseek-v4-flash",
    "opencode-go/deepseek-v4-flash-vision-exp",
)


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
        self.assertEqual({profile["model"] for profile in profiles.values()}, {FLASH})
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
            for phase in ("start", "resume"):
                argv = profile[phase]
                self.assertIn(FLASH, argv)
                # The near neighbours, asserted by name. `deepseek-v4-flash` is a
                # DIFFERENT model from `deepseek-v4.1-flash`, and the two codes
                # differ by two characters, so the mistake this guards against is
                # a plausible typo rather than a hypothetical one.
                for forbidden in FORBIDDEN:
                    self.assertNotIn(forbidden, argv, f"{phase} names {forbidden}")

    def test_the_approved_code_carries_its_version(self):
        # The provider renamed this code: it was `opencode-go/deepseek-flash`,
        # which `opencode models` no longer lists. The rename is the reason the
        # version is asserted here rather than left to prose — pinning the old
        # unversioned form stops resolving, and matching on a prefix would admit
        # `deepseek-v4-flash`.
        self.assertTrue(FLASH.endswith("deepseek-v4.1-flash"), FLASH)
        for forbidden in FORBIDDEN:
            self.assertNotEqual(FLASH, forbidden)
            self.assertFalse(FLASH.startswith(forbidden), FLASH)

        blob = json.dumps(self.policy) + json.dumps(self.commands)
        self.assertNotIn('"opencode-go/deepseek-flash"', blob,
                         "the unversioned provider code is no longer offered by the provider")

    def test_unavailability_requires_cross_house_reroute(self):
        substitution = self.commands["substitution"]
        self.assertIn("another approved house", substitution)
        self.assertIn("forbidden fallbacks", substitution)


if __name__ == "__main__":
    unittest.main()
