# Director Schema V2

Use schema V2 for new projects whose story meaning and H3 reference jobs must be compiler-validated. Legacy projects remain readable under schema V1.

Enable strict validation in `storyboard.json`:

```json
{
  "meta": {
    "director_schema_version": 2
  }
}
```

Each segment must include `creative_intent` and `reference_assets`.

```json
{
  "id": 1,
  "title": "Notification breaks the mask",
  "duration": "auto",
  "shot_durations": [1.2, 1.3, 1.5],
  "creative_intent": {
    "state_before": "Zhou appears relaxed and socially composed.",
    "trigger": "A notification wakes the phone and exposes the former partner's update.",
    "state_after": "Zhou hides the evidence and rebuilds a visibly manufactured smile.",
    "audience_takeaway": "His cheerful exterior is deliberate emotional protection.",
    "shot_intents": [
      {
        "new_information": "The phone wakes because a notification arrives.",
        "narrative_subject": "phone notification",
        "contains_reaction": false
      },
      {
        "new_information": "Zhou's breath stops before he acts.",
        "narrative_subject": "Zhou's involuntary reaction",
        "contains_reaction": true
      },
      {
        "new_information": "He locks the phone and consciously rebuilds the smile.",
        "narrative_subject": "Zhou's protective performance",
        "contains_reaction": true
      }
    ],
    "continuity_handoff": {
      "positions": "Zhou remains outside the entrance; Zhao approaches from screen-right.",
      "emotion": "Zhou is outwardly bright but internally unsettled.",
      "props": "The phone is locked black and held screen-in toward Zhou.",
      "audio": "Notification sound has ended; exterior night ambience continues."
    }
  },
  "reference_assets": [
    {
      "path": "refs/zhou_master.png",
      "role": "identity_subject",
      "label": "Subject 1"
    },
    {
      "path": "refs/entrance_single.png",
      "role": "location_subject",
      "label": "Subject 2"
    }
  ]
}
```

## Creative intent rules

- `state_before`, `trigger`, `state_after`, and `audience_takeaway` must be observable and non-empty.
- `shot_intents` must match the compiled shot count exactly.
- Every shot declares `new_information`; a cut without new information should be removed or replaced by camera motion.
- `narrative_subject` names the story-bearing person, reaction, object, state, or spatial fact.
- Dialogue beats require at least one `contains_reaction: true`. The reaction may occur inside a continuous dialogue shot; a separate reaction cut is not mandatory.
- `continuity_handoff` passes positions, emotion, props, and audio to the next beat.

## H3 reference roles

| Role | H3 label | Current runner support | Purpose |
|---|---|---|---|
| `identity_subject` | `Subject N` | yes | person identity and wardrobe |
| `location_subject` | `Subject N` | yes | one coherent physical space |
| `prop_subject` | `Subject N` | yes | narratively essential object design |
| `composition_picture` | `Picture N` | schema only | concrete first/key/last-frame composition |
| `motion_video` | `Video N` | schema only | movement, camera, cuts, or temporal structure |
| `audio_reference` | `Audio N` | schema only | voice, rhythm, ambience, or reused audio |

The compiler rejects schema-only roles until the local ComfyUI Director node and runner can bind those media types correctly. This prevents a prompt from citing a reference that never reaches H3.

Do not enable schema V2 on an existing production until its segments have been deliberately migrated and reviewed. Never fill the new fields with generic placeholders merely to satisfy validation.
