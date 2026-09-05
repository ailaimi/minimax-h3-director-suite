# H3 Drama Director Playbook

Read this when creating or revising a director spec, choosing references, or reviewing generated footage. It combines local beat01–09 evidence with transferable production principles from Higgsfield's public storyboard, consistency, camera-control, and failure-analysis materials. It does not depend on Higgsfield-specific controls.

## 1. Plan the audience takeaway first

For each dramatic beat, write one sentence describing what the audience must understand or feel by its end. Only then choose shots. Every shot needs a purpose such as geography, action, evidence, reaction, escalation, or transition. Remove attractive shots that do not advance that purpose.

Do not split by round durations. Author the editorial shots first, assign durations, then pack consecutive shots that form one indivisible dramatic beat.

- Dialogue or subtle performance: 2–4 seconds.
- Mixed narrative action: 1.5–3 seconds.
- High-dynamic action: 0.4–1.5 seconds.
- Important spatial establishment: 2–4 seconds.
- Evidence, phone, hand, or prop insert: 0.5–2 seconds.
- Reaction after dialogue: retain 1–2 seconds of emotional aftereffect.
- Prefer a 4–10 second generation unit. Use 10–15 seconds only when splitting would break one continuous performance, exchange, action, or transition. Merge compatible material shorter than the H3 four-second minimum; never pad or slow it to reach a round number.

The compiler requires each shot to begin with `{dialogue}`, `{mixed}`, `{action}`, `{establish}`, `{insert}`, or `{reaction}` and validates its duration range. In `storyboard.json`, use a numeric `duration`, or `"auto"` plus `shot_durations`; a mismatch is an error.

## 2. Define a production-ready shot

Give every shot only the details that change production decisions:

- purpose and audience takeaway;
- shot size and camera position;
- camera movement, including direction and speed, or explicitly locked-off;
- subject, action, performance change, and target of attention;
- location anchor and visible landmarks;
- lighting continuity when it matters;
- dialogue or sound cue;
- entry state, physical trigger, and exit state for any change.

Prefer literal, physically testable language over adjectives such as “cinematic,” “dramatic,” or “natural.” Use technical lens or focal-length language only when it creates a meaningful visual difference; camera vocabulary is not decoration.

Reuse one concise visual scene key in every shot of a beat. Keep local shot prompts focused on action, camera, performance, and sound instead of redescribing the entire reference.

## 3. Anchor identity and location together

A coherent scene needs both an identity anchor and a location anchor. A good person reference may be a multi-view identity sheet. A scene reference must show one continuous physical space; never use a contact sheet or montage combining lobby, entrance, corridor, and room.

For location anchors, prefer an establishing image that clearly shows geography, walkable routes, light direction, doors, furniture, fixed landmarks, and the exact work zone required by the action.

Bind at most one location reference to a beat. Add a separate prop reference only when its exact design is narratively essential and it does not introduce a competing environment. When a generated frame successfully combines character and location, preserve the strongest frame as a possible continuity anchor for a later beat; do not replace canonical references without human approval.

Before binding a generic identity or location image, compare its visible details with the authored beat state. Shoes, straight trouser cuffs, standing posture, an empty basin, or unrelated black handheld objects are not neutral when the beat requires bare feet, rolled cuffs, low service posture, visible water, or a specific phone orientation. Create one clean beat-specific complete-composition anchor containing the correct people, posture, location, waterline, and prop state. Remove lookalike props such as remote controls instead of relying on negative prompting.

Ref2VA may leak the requested ending state into earlier frames. After that failure, never ask another Ref2VA generation unit to prove the same two opposite rigid-object states. Prefer a literal first/last-frame workflow with compatible compositions. If that route is unavailable or the motion remains unreliable, generate state A and state B separately and cut at a fully obscuring hand, foreground wipe, impact, blink, or other motivated transition. Preserve camera side, object footprint, landmarks, body positions, lighting, and sound continuity across the edit.

Literal first/last frames also control secondary performance. Every person or prop expected to move must have a small, physically compatible endpoint delta: hand position, fabric fold, gaze, breathing posture, water ripple, or another visible state change. If a secondary character has identical pose and prop geometry in both frames, expect FL2VA to freeze that character even when the prompt requests continuing action. Keep the endpoint delta restrained enough to interpolate without teleporting or changing blocking.

An audit warning about a possible seam requires visual inspection. A real door frame or wall edge can trigger a false positive; record that judgment rather than blindly accepting or rejecting it.

## 4. Lock spatial continuity before camera variety

For every multi-shot beat declare one location or permitted route, fixed landmarks and screen positions, each character's starting side/distance/facing/body elevation, the 180-degree axis, permitted displacement, and the final position inherited by the next beat.

Screen side is insufficient. Also state standing, seated, crouched, or kneeling; above or below another character's shoulder line; and beside, in front of, or behind the relevant landmark. Avoid alternatives such as “stands or sits.”

In constrained two-person scenes, prefer recurring same-side master coverage. Return to the named master after close-ups, reactions, and inserts. Use a reverse angle only when it materially improves the beat and the blocking can tolerate regeneration risk. After each cut compare screen side, relative distance, facing, body height, and landmark position.

Cutaways and prop inserts are temporal pickups from the same geometry. Reject teleports, spatial resets, invented rooms, relocated entrances, reversed travel direction, or backgrounds that cannot coexist.

## 5. Direct dialogue as interaction

Assign stable H3 speaker IDs `(S1)`, `(S2)`, and so on. Put only spoken words inside `<d>[Language] ...</d>`; never include a character name, colon, or “voice-over” label inside the tag.

Before speech, establish who addresses whom, reciprocal eyelines, body orientation, and a stable axis. Each reply must visibly target the preceding speaker. Preserve the listener's reaction and one to two seconds of aftereffect when the drama depends on it. Reject a line delivered toward camera or an unrelated direction even if the audio is correct.

Do not ask the model to render subtitles unless intentionally required. Use explicit constraints against subtitles, captions, transcript text, or readable wall text when unwanted typography has appeared before.

## 6. Direct props through causality and geometry

For every important prop interaction specify its initial state, exact physical trigger, final state, hand grip/contact point/viewing orientation, and what the camera may see.

- Phone notification: standby black → one generic lock-screen banner wakes the display → character reads it → side lock button pressed → black screen. Do not substitute a feed, profile, chat list, portrait, or readable message.
- Reading a phone: display faces the character; camera sees it only from a plausible over-shoulder or oblique angle.
- Replacing tea with water: preserve cup locations, hand contact, and table geography before and after the swap.
- Service worker beside a basin: lock the low working zone and prohibit standing behind the side table or beneath the television.

Reject a result when the object is visible but the interaction is physically impossible.

## 7. Use camera movement selectively

- Use locked or nearly locked frames for restrained dialogue and deadpan comedy.
- Use a slow push-in for recognition, suspicion, or emotional pressure.
- Use measured tracking for purposeful travel through established space.
- Use inserts for evidence and causal triggers.
- Use brief reaction close-ups for emotional reversals.

Avoid stacking pan, zoom, orbit, rack focus, and actor movement in one short shot. If a move changes the established axis or obscures landmarks, simplify it. Test movement and pacing at low resolution before a final render.

## 8. QC and recovery matrix

| Dimension | Pass condition | Typical repair |
|---|---|---|
| Story | Intended takeaway is readable | Remove or reorder shots; strengthen reaction |
| Identity | Face, hair, wardrobe remain stable | Improve or reuse identity anchor |
| Location | Same geography and landmarks persist | Replace collage with one location image |
| Blocking | Side, depth, height, facing remain logical | Return to same-side master; lock landmarks |
| Interaction | Eyeline, grip, contact, and target are plausible | Write explicit state and geometry |
| Dialogue | Exact line, speaker order, addressee, and timing pass | Correct speaker tags and interaction staging |
| Text | No accidental subtitles or readable gibberish | Add explicit no-text constraints |
| Rhythm | Shot duration matches dramatic function | Repack authored shots; do not pad |

When only one dimension fails, preserve the rest and revise that beat only. After two similar failures, change the structure or anchor rather than rolling another random seed.

## Sources behind the transferable principles

- Higgsfield, “How to Turn a Script into an AI Storyboard and Shot List”: https://higgsfield.ai/blog/script-to-ai-storyboard-shot-list
- Higgsfield, “How to Keep Characters and Locations Consistent Across AI Shots”: https://higgsfield.ai/blog/consistent-characters-locations
- Higgsfield, “How to Control Camera Movement, Angles, and Lens in AI Video”: https://higgsfield.ai/blog/ai-video-camera-control
- Higgsfield Academy, “The prompt-builder skill and first Seedance run”: https://higgsfield.ai/academy/courses/santiago-cinematic/prompt-builder-skill-first-run
- Higgsfield, “Why AI Video Generations Fail And How to Fix Every Common Error”: https://higgsfield.ai/blog/why-ai-video-generations-fail

These sources support previsualization, explicit shot purpose, dual character/location anchoring, literal prompts, camera specificity, low-cost iteration, and failure classification. H3 timing ranges, speaker markup, ComfyUI submission behavior, and the concrete geometry rules come from this local workflow and observed tests.
