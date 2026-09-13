import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "skills" / "interchange" / "references" / "policy.json"


class CognitiveRoutingTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text())

    def test_only_approved_profiles_receive_interpretive_authority(self):
        cognitive = self.policy["cognitive_roles"]
        brains = {
            *cognitive["default_brain"],
            *cognitive["large_cross_workstream_brain"],
            *cognitive["product_ideation_brain"],
            *cognitive["semantic_review_brain"],
        }

        self.assertEqual(
            brains,
            {
                "dm-sol-high",
                "lead-sol-high",
                "dm-astra-medium",
                "lead-astra-medium",
                "brainstorm-fable-medium",
                "brainstorm-astra-medium",
                "reviewer-sol-high",
                "reviewer-astra-medium",
            },
        )
        self.assertIn("remains a mechanical leaf", cognitive["rule"])

    def test_sol_high_is_default_and_astra_is_large_ambiguity_escalation(self):
        cognitive = self.policy["cognitive_roles"]

        self.assertEqual(cognitive["default_brain"], ["dm-sol-high", "lead-sol-high"])
        self.assertEqual(
            cognitive["large_cross_workstream_brain"],
            ["dm-astra-medium", "lead-astra-medium"],
        )

    def test_semantic_acceptance_excludes_fable_and_mechanical_profiles(self):
        cognitive = self.policy["cognitive_roles"]

        self.assertEqual(
            cognitive["semantic_review_brain"],
            ["reviewer-sol-high", "reviewer-astra-medium"],
        )
        self.assertIn("Product-ideation brains", cognitive["semantic_acceptance_rule"])
        self.assertIn("cannot", cognitive["semantic_acceptance_rule"])

    def test_muse_owns_light_mechanical_read_seek_lane(self):
        route = next(
            route
            for route in self.policy["routing"]
            if route["task"] == "Light mechanical and read/seek task"
        )

        self.assertEqual(route["first"], "worker-muse-xhigh")
        self.assertIn("no interpretation", route["reason"])

    def test_novel_public_contract_is_settled_before_deepseek_max(self):
        route = next(
            route
            for route in self.policy["routing"]
            if route["task"] == "Novel public contract implementation"
        )

        self.assertIn("lead-sol-high settles shape", route["first"])
        self.assertIn("does not choose", route["reason"])

    def test_parallelism_requires_objective_packets_and_fixed_ownership(self):
        rules = "\n".join(self.policy["selection_rules"])

        self.assertIn("objectively testable packets", rules)
        self.assertIn("write ownership", rules)
        self.assertIn("overhead would erase", rules)

    def test_codex_mechanical_dispatch_defaults_to_zero_and_one_at_a_time(self):
        capacity = self.policy["codex_capacity"]

        self.assertIn("zero", capacity["default_codex_mechanical_allowance"])
        self.assertIn("one Codex mechanical worker", capacity["concurrency"])
        self.assertIn("explicit owner authorization", capacity["concurrency"])

    def test_codex_capacity_is_reserved_for_brain_integration_and_review(self):
        capacity = self.policy["codex_capacity"]

        self.assertIn("judgment", capacity["purpose"])
        self.assertIn("integration", capacity["purpose"])
        self.assertIn("semantic/risk acceptance", capacity["purpose"])
        self.assertIn("Claude, Grok or OpenCode", capacity["mechanical_route"])

    def test_codex_usage_has_early_freeze_controls(self):
        capacity = self.policy["codex_capacity"]
        monitoring = {item["rule"]: item for item in self.policy["monitoring"]}

        self.assertIn("Freeze new Codex mechanical dispatch", capacity["early_checkpoint"])
        self.assertEqual(monitoring["Codex mechanical concurrency"]["value"], "At most 1 active by default")
        self.assertIn("Freeze", monitoring["Codex early burn checkpoint"]["meaning"])

    def test_owner_can_set_codex_delegation_and_leading_to_zero(self):
        capacity = self.policy["codex_capacity"]
        monitoring = {item["rule"]: item for item in self.policy["monitoring"]}

        self.assertIn("mechanical and lead allocation to zero", capacity["override"])
        self.assertIn("allowance to zero", monitoring["Owner zero-Codex override"]["meaning"])
        self.assertIn("explicitly requested brain/review", monitoring["Owner zero-Codex override"]["meaning"])

    def test_demanding_mechanical_work_routes_external_before_codex(self):
        route = next(
            route
            for route in self.policy["routing"]
            if route["task"] == "Demanding but well-defined implementation"
        )

        self.assertEqual(route["first"], "worker-deepseek-flash-high; worker-opus-high")
        self.assertIn("recorded Codex mechanical allowance", route["fallback"])


if __name__ == "__main__":
    unittest.main()
