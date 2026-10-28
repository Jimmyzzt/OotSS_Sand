# Working agreement

The goal is to finish video-to-level notes with an agent and a few local tools.
Do not build a general automatic recognition platform, server, or review app.

- Read README.md and docs/workflow.md before processing another video.
- Use cached scans, contact sheets, and bounded high-resolution frame requests.
- For this anthology, P1–24 is phase one. Keep that snapshot. The combined atlas groups observed visits by Overworld / Sky / Underworld / Intro, including later returns to Overworld. On 2026-10-28 the owner explicitly superseded the old source-P68 exclusion for the independent Intro entries only (currently display P69). Development-gallery examples must never acquire their same-name entrances in the other worlds. Source P67/current P68 world-tour exclusions from the owner's continuity review remain excluded.
- Check full timeline continuity: large entries can contain connected internal rooms. Sparse reference hits are neither full visit bounds nor proof of a new entry on every camera pan.
- Never upload video or invoke paid APIs. Agent judgment happens in Codex; Luna may inspect bounded evidence packets when useful.
- Keep every identity, time bound, and overworld check backed by explicit evidence. Candidate ranks are not probabilities. Unknown is valid.
- Only Level_Entry markers on the physical maps are target levels. Intro comes from its independent markers_intro.json: file membership overrides height classification, and duplicated names use upstream intro- IDs. Preserve logical save IDs separately, duplicate entries and all coordinates.
- Intro completion is manual and independent until distinct game-save IDs are verified. Never inherit regular-world completion from a reused name. Empty/out-of-range map tiles must be transparent, and grid extents must use the valid grid rows rather than full image projection bounds.
- Preserve machine candidates separately from reviewed events. Reruns must never overwrite reviewed notes.
- Keep raw videos, reference downloads, and frame caches out of Git. Results with provenance belong in results/.
- Run pytest and ruff for meaningful code changes. Commit runnable milestones locally. Never change unrelated repositories or remotes.

- Entry identity must agree with initial character roles and physical-world approach, not only reused terrain. Finale internal boards can copy early-world layouts. Never count sparse reference windows as separate entrances without entry/exit evidence; keep an audit note when continuity is uncertain. Rebuild the manual difference list with scripts/audit_differences.py after identity edits.

- The owner’s continuity notes in docs/校对.md supersede weak per-frame matches. The applied plan is data/human_corrections.json. Do not split its long confirmed visits on internal room/overview changes; excluded world segments are not unknown levels. Keep superseded source events for traceability.

- Before publishing, identify the hosting plan's request, CPU, storage, file-count and file-size limits; estimate per-visit request fanout and test quota failure behavior. Public static resources must bypass Worker execution. Keep a direct backup site, preserve Access restrictions, and run the package limit check before upload. Record measured capacity and remaining headroom in docs/hosting.md; do not silently upgrade to paid plans. Apply the same capacity review to future deployment work.
