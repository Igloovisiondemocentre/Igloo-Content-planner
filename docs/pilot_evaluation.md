# Pilot Evaluation Review Template

Use this template during live pilot review to compare agent output with expert judgment without expanding scope into Phase 2.

## Review metadata

- Date:
- Reviewer:
- Brief source:
- Evaluation file:
- Environment notes:

## Summary

- Overall agreement level:
- Areas where the agent is trustworthy:
- Areas where the agent overstates supportability:
- Areas where the agent is too conservative:
- Rule changes proposed:

## Per-brief comparison

| Brief ID | Brief | Agent verdict | Confidence | Needs human review | Proposed build route | Expert verdict | Expert build route | Agreement | Notes |
| --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |

## Evidence review

- Did the hard evidence justify the verdict?
- Did the inference stay within the evidence boundary?
- Did the proposed build route match how an Igloo operator would realistically build the experience?
- Did the report confuse authoring tools such as PowerPoint, Canva, or web apps with true runtime surfaces?
- Were unresolved unknowns clearly stated?
- Did the sandbox wording remain explicit enough?

## False positives and overstatements

- Any case where the agent implied supportability too strongly:
- Any case where `Needs human review` should have been raised:
- Any case where `Unverified locally` should have been used:

## False negatives and missed opportunities

- Any case where the verdict was too cautious:
- Any case where the evidence retrieval missed an obvious source:

## Actions

- Retrieval improvements:
- Support-policy changes:
- Documentation gaps to capture:
- Briefs to add to `core_eval`:
- Briefs to add to `hero_eval`:
