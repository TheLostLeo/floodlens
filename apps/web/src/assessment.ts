export function inDemoRegion(latitude: number, longitude: number) {
  // Regional navigation bounds include neighbouring countries; this is not a border dataset.
  return Number.isFinite(latitude) && Number.isFinite(longitude) && latitude >= 6 && latitude <= 38 && longitude >= 68 && longitude <= 98;
}

export function terrainSummary(terrain?: { status: string; score?: number; label?: string }) {
  if (terrain?.status !== 'available' || terrain.score == null) return 'Terrain information is not available here. Missing information does not mean low susceptibility.';
  const level = terrain.label?.split(' ')[0] ?? (terrain.score >= 67 ? 'higher' : terrain.score >= 34 ? 'moderate' : 'lower');
  if (level === 'higher') return 'The terrain has several features that can favour water accumulation. This does not establish whether this neighbourhood will flood.';
  if (level === 'moderate') return 'Some terrain features may favour water accumulation. Drainage and local conditions are not fully represented.';
  return 'The terrain shows fewer of the features measured by this assessment. This does not mean the neighbourhood is safe from flooding.';
}

export function addComparison<T extends { id: string }>(saved: T[], next: T): T[] {
  return [...saved.filter(item => item.id !== next.id), next].slice(-2);
}
