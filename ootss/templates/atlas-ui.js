/* Prefixes stay outside the ordinal box so the ordinal anchor never moves. */
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
  markerLabels(levels, selectedPart, displayPart = p => p) {
    return new Map(levels.map(level => {
      const visit = level.shown[0], ordinal = String(visit.ordinal), prefix = selectedPart ? '' : `${displayPart(visit.part)}·`;
      return [level.level_id, {text:prefix + ordinal, ordinal, prefix, part:visit.part, withPart:!selectedPart}];
    }));
  }
};
