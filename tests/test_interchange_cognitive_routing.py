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

    def test_every_astra_and_fable_profile_is_owner_gated_per_invocation(self):
        gated_models = {"gpt-6-astra", "claude-fable-5-1"}
        gated_profiles = [
            profile for profile in self.policy["profiles"]
            if profile["model"] in gated_models
        ]

        self.assertTrue(gated_profiles)
        for profile in gated_profiles:
            gate = profile.get("invocation_authorization", "")
            self.assertIn("Fresh explicit owner authorization", gate)
            self.assertIn("start/resume/retry/follow-up", gate)
            self.assertIn("gpt-5.6-sol high cannot fit", gate)
            self.assertIn("never reuse", gate)

        policy_gate = self.policy["owner_gated_brains"]
        self.assertIn("Every model invocation", policy_gate["scope"])
        self.assertIn("Only the owner", policy_gate["authority"])
        self.assertIn("Never reuse", policy_gate["non_reuse"])
        self.assertIn("included-plan/no-extra-cost", policy_gate["fable_additional_gate"])

    def test_sol_high_is_default_for_product_ideation(self):
        route = next(
            route
            for route in self.policy["routing"]
            if route["task"] == "New product idea and brainstorming"
        )

        self.assertEqual(route["first"], "lead-sol-high or dm-sol-high")
        self.assertIn("fresh owner authorization", route["fallback"])
        self.assertIn("Sol high cannot fit", route["fallback"])

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

    def test_terra_sol_dispatch_defaults_to_zero_and_one_at_a_time(self):
        capacity = self.policy["codex_capacity"]

        self.assertIn("zero for Terra/Sol", capacity["default_codex_mechanical_allowance"])
        self.assertIn("one Terra/Sol mechanical worker", capacity["concurrency"])
        self.assertIn("explicit owner authorization", capacity["concurrency"])
        self.assertIn("Luna has no Interchange concurrency cap", capacity["concurrency"])

    def test_measured_capacity_preserves_sol_brain_integration_and_review(self):
        capacity = self.policy["codex_capacity"]

        self.assertIn("judgment", capacity["purpose"])
        self.assertIn("integration", capacity["purpose"])
        self.assertIn("semantic/risk acceptance", capacity["purpose"])
        self.assertIn("Luna, DeepSeek or Muse", capacity["mechanical_route"])

    def test_terra_sol_usage_has_early_freeze_controls(self):
        capacity = self.policy["codex_capacity"]
        monitoring = {item["rule"]: item for item in self.policy["monitoring"]}

        self.assertIn("Freeze new Terra/Sol dispatch", capacity["early_checkpoint"])
        self.assertEqual(monitoring["Terra/Sol mechanical concurrency"]["value"], "At most 1 active by default")
        self.assertIn("Freeze", monitoring["Terra/Sol early burn checkpoint"]["meaning"])

    def test_luna_deepseek_and_muse_are_unrestricted_mechanical_capacity(self):
        tiers = self.policy["capacity_tiers"]
        unrestricted = tiers["unrestricted_mechanical"]

        self.assertEqual(
            set(unrestricted["profiles"]),
            {
                "worker-luna-xhigh",
                "worker-luna-max",
                "worker-muse-xhigh",
                "worker-deepseek-flash-high",
                "worker-deepseek-flash-max",
            },
        )
        self.assertIn("an Interchange concurrency cap", unrestricted["rule"])
        self.assertIn("Three, four, five or more", unrestricted["rule"])
        self.assertIn("non-overlapping writes", unrestricted["boundaries"])

    def test_terra_sol_and_claude_code_are_moderate_and_balanced(self):
        tier = self.policy["capacity_tiers"]["moderate_balanced"]

        self.assertEqual(
            set(tier["models"]),
            {"gpt-5.6-terra", "gpt-5.6-sol", "claude-opus-5"},
        )
        self.assertIn("Use moderately", tier["rule"])
        self.assertIn("balance work between Codex and Claude Code", tier["rule"])
        self.assertIn("Do not alternate houses mechanically", tier["not_forced"])

    def test_luna_can_run_beside_sol_high_but_not_astra(self):
        exclusivity = self.policy["house_exclusivity"]
        exemptions = exclusivity["delivery_manager_exemptions"]

        self.assertEqual(len(exemptions), 1)
        self.assertEqual(
            set(exemptions[0]["profiles"]),
            {"worker-luna-xhigh", "worker-luna-max"},
        )
        self.assertIn("gpt-5.6-sol high", exemptions[0]["trigger"])
        self.assertIn("Astra global exclusivity", exemptions[0]["reason"])
        self.assertIn("except worker-luna-xhigh/max", exclusivity["manager_effect"])

        astra_trigger = next(
            trigger
            for trigger in exclusivity["global_triggers"]
            if trigger.get("model") == "gpt-6-astra"
        )
        self.assertEqual(astra_trigger["house"], "codex")
        self.assertEqual(astra_trigger["effort"], "any")

    def test_owner_can_set_codex_delegation_and_leading_to_zero(self):
        capacity = self.policy["codex_capacity"]
        monitoring = {item["rule"]: item for item in self.policy["monitoring"]}

        self.assertIn("every Codex mechanical and lead allocation to zero", capacity["override"])
        self.assertIn("including Luna, to zero", monitoring["Owner zero-Codex override"]["meaning"])
        self.assertIn("explicitly requested brain/review", monitoring["Owner zero-Codex override"]["meaning"])

    def test_demanding_mechanical_work_routes_external_before_codex(self):
        route = next(
            route
            for route in self.policy["routing"]
            if route["task"] == "Demanding but well-defined implementation"
        )

        self.assertEqual(route["first"], "worker-deepseek-flash-high; worker-opus-high")
        self.assertIn("recorded Terra/Sol mechanical allowance", route["fallback"])


if __name__ == "__main__":
    unittest.main()
