# Working agreement

The goal is to finish video-to-level notes with an agent and a few local tools.
Do not build a general automatic recognition platform, server, or review app.

- Read README.md and docs/workflow.md before processing another video.
- Use cached scans, contact sheets, and bounded high-resolution frame requests.
- Never upload video or invoke paid APIs. Agent judgment happens in Codex; Luna may inspect bounded evidence packets when useful.
- Keep every identity, time bound, and overworld check backed by explicit evidence. Candidate ranks are not probabilities. Unknown is valid.
- Only Level_Entry markers on the Overworld are target levels. Preserve duplicate entries and all coordinates.
- Preserve machine candidates separately from reviewed events. Reruns must never overwrite reviewed notes.
- Keep raw videos, reference downloads, and frame caches out of Git. Results with provenance belong in results/.
- Run pytest and ruff for meaningful code changes. Commit runnable milestones locally. Never change unrelated repositories or remotes.
