# Working agreement

The goal is to finish video-to-level notes with an agent and a few local tools.
Do not build a general automatic recognition platform, server, or review app.

- Read README.md and docs/workflow.md before processing another video.
- Use cached scans, contact sheets, and bounded high-resolution frame requests.
- For this anthology, P1–24 is phase one, according to the author's stage-start titles. Keep that phase-one snapshot. The combined atlas now covers P1–68 and groups visits by physical map (Overworld / Sky / Underworld), including later-stage returns to Overworld. Build it only from observed reviewed visits, never all map markers.
- Check full timeline continuity: large entries can contain connected internal rooms. Sparse reference hits are neither full visit bounds nor proof of a new entry on every camera pan.
- Never upload video or invoke paid APIs. Agent judgment happens in Codex; Luna may inspect bounded evidence packets when useful.
- Keep every identity, time bound, and overworld check backed by explicit evidence. Candidate ranks are not probabilities. Unknown is valid.
- Only Level_Entry markers on the three physical maps are target levels. Preserve duplicate entries and all coordinates.
- Preserve machine candidates separately from reviewed events. Reruns must never overwrite reviewed notes.
- Keep raw videos, reference downloads, and frame caches out of Git. Results with provenance belong in results/.
- Run pytest and ruff for meaningful code changes. Commit runnable milestones locally. Never change unrelated repositories or remotes.
