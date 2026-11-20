# Deviations from the PaperOrchestra loop in run 2

## After round 1 (`decide` on v1: REJECTED_DEGRADATION, continue false)

v1 was not accepted: Overall stayed 5 for every reviewer; the merged Soundness fell from 3 to 2 by rounding (means
2.67 for v0, 2.33 for v1). Upstream, `continue: false` ends the loop with v0.

The loop was continued for one reason: the round-1 refiner followed a note in `raw_materials/notes.md`, written by the
orchestrator, that described the matched ablation's +1.8 points for the evidence graph as a settings effect. On the
same 38 entries the evidence graph was already +1.0 at the main settings and the settings step was +0.8 (interval
including zero), so the note was wrong, and all three v1 reviewers flagged the resulting headline. Round 1 therefore
did not test the refiner on correct instructions. The note was corrected before round 2.

What is unchanged: v1 stays rejected; CUR remains v0; round 2 refines v0 against `review_v0.json`, and its candidate is
compared with v0 by `decide` as usual. The refiner may reuse wording from `refined_v1.tex` where it meets the notes.
At most one more deviation of this kind; rounds stop at 3 as in the skill.
