import { describe, expect, it } from 'vitest';
import { terrainSummary, inDemoRegion, addComparison } from './assessment';
describe('resident assessment', () => {
  it('does not describe missing terrain as low susceptibility', () => {
    expect(terrainSummary()).toContain('not available');
    expect(terrainSummary({ status: 'outside_coverage', score: 0 })).toContain('not available');
  });
  it('keeps lower terrain scores distinct from safety', () => {
    expect(terrainSummary({ status: 'available', score: 0 })).toContain('does not mean');
    expect(terrainSummary({ status: 'available', score: 80 })).toContain('accumulation');
  });
  it('preserves the backend category when the displayed score was rounded', () => {
    expect(terrainSummary({ status: 'available', score: 67, label: 'moderate relative terrain susceptibility' })).toContain('Some terrain');
  });
  it('bounds the regional viewport without pretending to check national borders', () => {
    expect(inDemoRegion(13.08, 80.27)).toBe(true);
    expect(inDemoRegion(51.5, -0.1)).toBe(false);
    expect(inDemoRegion(NaN, 80)).toBe(false);
  });
  it('keeps two distinct snapshots and replaces the same analysis', () => {
    expect(addComparison([{ id: 'a' }, { id: 'b' }], { id: 'c' })).toEqual([{ id: 'b' }, { id: 'c' }]);
    expect(addComparison([{ id: 'a', value: 1 }], { id: 'a', value: 2 })).toEqual([{ id: 'a', value: 2 }]);
  });
});
