# Repeated-layout audit

This bounded audit checks the existing P50 review and its complete 13-sheet timeline, then checks short windows around the repeated P5 and P24 candidates. The sample frames are references for human review; matching a reference layout establishes a plausible identity, not a real Level_Entry. No source video was rescanned across the series, no existing reviewed file was changed, and no external API was used.

## P50: magnitudes_v3

The reviewed record has ten `magnitudes_v3` intervals: p50-001 (17.25–65s), p50-002 (290–310s), p50-003 (455–465s), p50-004 (580–590s), p50-005 (725–735s), p50-006 (750–765s), p50-007 (865–875s), p50-008 (940–950s), p50-009 (1055–1070s), and p50-010 (1105–1145s). They show the same industrial subarea board: central pale square, fixed surrounding structures, green block column and purple lower blocks. That supports a plausible identity match.

The complete timeline starts with a whole-map overview, then moves among the magnitudes board, courtyards, water/beam rooms and island views. Those repeated appearances are more consistent with internal returns and camera movement within one larger connected stage/entry than with ten separate Level_Entry visits. The bounded frames do not establish a unique entry/exit transition at any candidate onset, so the count is unverified. Keep the ten observed intervals as internal-layout sightings for manual review; do not count ten visits or assert an exact merged visit count. The 14 `p50-u*` unknown records are likewise time slices, not fourteen entries. Their layouts should remain unidentified while continuity is unresolved.

Evidence: [boundary montage](evidence/repeat_p50_magnitudes_boundaries.jpg), [sheet 00](../../runs/p50/sheet_00.jpg) through [sheet 12](../../runs/p50/sheet_12.jpg), and the existing [reviewed events](../p50/reviewed.json).

## P5: mirror_4 and mirror_14

`p5-004` (103.75–130s), `p5-005` (145–155s), and `p5-006` (185–220s) show the same mirror_4 island layout. The intervening bounded samples remain on that board, with movement/state changes and no visible world/entry transition. Merge these as one likely continuous visit, boundaries uncertain, rather than three entrances.

`p5-029` (1884.5–1905s) and `p5-030` (1920–1930s) show the same mirror_14 island when camera and object state changes are accounted for. Ten 1280px frames sampled every two seconds from 1904–1922 show the same main island outline, detached left island, two mirrors, orange mechanism, and continuous character movement. No exit or re-entry is visible. Merge them as one likely sequence or retry within the same entry; keep the exact entry boundary unresolved.

Evidence: [bounded 1904–1922s frames](evidence/repeat_p5_mirror14_bounded.jpg).

Evidence: [P5 montage](evidence/repeat_p5_mirror.jpg), [sheet 00](../../runs/p5/sheet_00.jpg), [sheet 12](../../runs/p5/sheet_12.jpg).

## P24: end1

`p24-001` (63.875–213.375s) is one long sequence with internal camera/room changes; it should remain one visit. `p24-003` (615–625s) and `p24-004` (655–668.5s) show the same board with changing beam/object state and no observed exit between them in the bounded context. Merge them as one likely visit or retry, not two entries. `p24-002` (304.25–370s) and `p24-005` (955–967.125s) are much later appearances of the same or closely related layout; keep them as provisional separate returns, with entrance count unverified until transition context is reviewed.

Evidence: [P24 montage](evidence/repeat_p24_end1.jpg), [sheet 00](../../runs/p24/sheet_00.jpg), [sheet 02](../../runs/p24/sheet_02.jpg), [sheet 04](../../runs/p24/sheet_04.jpg), [sheet 06](../../runs/p24/sheet_06.jpg).

The JSON file provides every target event ID, time bounds, recommendation, and evidence path for downstream manual correction. The bounded P5 packet contains exactly ten frames and does not modify the source review. Existing `reviewed.json` files are unchanged.
