/* Coordinate-based label grouping stays stable when the map zoom changes. */
globalThis.AtlasUI = {
  parseEditorial(data, levelIds, regionKeys) {
    if (!data || ![1,2].includes(data.version) || !data.levels || typeof data.levels !== 'object' || Array.isArray(data.levels)) throw Error('不是有效的标注文件');
    const levels = Object.create(null), regions = Object.create(null);
    for (const [id,v] of Object.entries(data.levels)) {
      if (!levelIds.has(id) || !v || typeof v !== 'object' || Array.isArray(v)) continue;
      const r = {};
      for (const k of ['big_star','multi_save']) if (typeof v[k] === 'boolean') r[k] = v[k];
      if (typeof v.notes === 'string') r.notes = v.notes.slice(0,200);
      levels[id] = r;
    }
    if (data.regions && typeof data.regions === 'object' && !Array.isArray(data.regions)) {
      for (const [id,v] of Object.entries(data.regions)) {
        if (regionKeys.has(id) && typeof v?.title === 'string' && v.title.trim()) regions[id] = {title:v.title.trim().slice(0,80)};
      }
    }
    return {levels,regions};
  },
  markerRadius(big, scale, zoom) {
    return Math.max((big ? 6.75 : 4.5) * scale, Math.min(42, (big ? 9 : 6) * scale * 2 ** (zoom - 2.75)));
  },
  markerLabels(levels, selectedPart, regions, displayPart = p => p) {
    const result = new Map(), groups = new Map();
    for (const level of levels) {
      const visit = level.shown[0], region = regions.get(level.region_ids[0]);
      const mixed = !selectedPart && region?.parts.length > 1;
      result.set(level.level_id, {text: String(visit.ordinal), part: visit.part, mixed});
      if (mixed) {
        const key = `${region.id}:${visit.part}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(level);
      }
    }
    for (const group of groups.values()) {
      group.sort((a,b) => a.shown[0].ordinal - b.shown[0].ordinal);
      const unseen = new Set(group);
      for (const first of group) {
        if (!unseen.delete(first)) continue;
        const item = result.get(first.level_id);
        item.text = `${displayPart(item.part)}·${first.shown[0].ordinal}`;
        const queue = [first];
        while (queue.length) {
          const current = queue.shift();
          for (const candidate of unseen) {
            // Only nearby entrances in a continuous ordinal run share a prefix.
            const sequential = Math.abs(current.shown[0].ordinal - candidate.shown[0].ordinal) <= 2;
            const near = current.entries.some(a => candidate.entries.some(b =>
              Math.hypot(a.coordinates[0]-b.coordinates[0], a.coordinates[1]-b.coordinates[1]) <= 3.2));
            if (sequential && near) { unseen.delete(candidate); queue.push(candidate); }
          }
        }
      }
    }
    return result;
  }
};
