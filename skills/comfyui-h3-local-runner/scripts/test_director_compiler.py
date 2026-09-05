import tempfile
import unittest
from pathlib import Path

import director_compiler as dc


class CreativeIntentTests(unittest.TestCase):
    def test_single_information_bearing_shot_is_allowed(self):
        shots = [{"directorKind": "establish", "length": 96}]
        dc.validate_director_density(shots, 4.0, 24)

    def test_v2_accepts_reaction_inside_dialogue_shot(self):
        segment = {
            "dialogue": ["周远：走。"],
            "creative_intent": {
                "state_before": "Zhou hides his reaction.",
                "trigger": "Zhao asks whether they should leave.",
                "state_after": "Zhou commits to entering.",
                "audience_takeaway": "He chooses performance over disclosure.",
                "shot_intents": [{
                    "new_information": "Zhou answers only after rebuilding his smile.",
                    "narrative_subject": "Zhou's controlled reply",
                    "contains_reaction": True,
                }],
                "continuity_handoff": {
                    "positions": "Both face the entrance.",
                    "emotion": "Zhou is guarded.",
                    "props": "Phone remains locked.",
                    "audio": "Night ambience continues.",
                },
            },
        }
        creative, warnings = dc.validate_creative_intent(segment, [{}], True)
        self.assertEqual([], warnings)
        self.assertEqual("Zhou hides his reaction.", creative["state_before"])

    def test_v2_rejects_cut_without_new_information(self):
        segment = {
            "creative_intent": {
                "state_before": "before", "trigger": "trigger", "state_after": "after",
                "audience_takeaway": "takeaway",
                "shot_intents": [{"new_information": "", "narrative_subject": "Zhou"}],
                "continuity_handoff": {
                    "positions": "same", "emotion": "same", "props": "none", "audio": "room tone"
                },
            }
        }
        with self.assertRaisesRegex(ValueError, "new_information"):
            dc.validate_creative_intent(segment, [{}], True)


class ReferenceRoleTests(unittest.TestCase):
    def test_explicit_image_roles_are_resolved(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            segment = {"reference_assets": [
                {"path": "person.png", "role": "identity_subject", "label": "Subject 1"},
                {"path": "room.png", "role": "location_subject", "label": "Subject 2"},
            ]}
            assets, warnings = dc.resolve_reference_assets(project, segment, True)
            self.assertEqual([], warnings)
            self.assertEqual(["identity_subject", "location_subject"], [x["role"] for x in assets])

    def test_unwired_audio_role_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            segment = {"reference_assets": [
                {"path": "voice.wav", "role": "audio_reference", "label": "Audio 1"}
            ]}
            with self.assertRaisesRegex(ValueError, "not yet supported"):
                dc.resolve_reference_assets(Path(folder), segment, True)


if __name__ == "__main__":
    unittest.main()
