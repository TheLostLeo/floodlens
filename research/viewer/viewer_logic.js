(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.ViewerLogic = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  function metricValue(sample, model, key, fallback) {
    const value = sample.models?.[model]?.metrics?.[key];
    return value == null ? fallback : Number(value);
  }

  function sortSamples(samples, model, mode) {
    const copy = [...samples];
    if (mode === 'missed') return copy.sort((a,b) => metricValue(b,model,'fn',-1) - metricValue(a,model,'fn',-1));
    if (mode === 'false') return copy.sort((a,b) => metricValue(b,model,'fp',-1) - metricValue(a,model,'fp',-1));
    if (mode === 'worst') return copy.sort((a,b) => metricValue(a,model,'iou',Infinity) - metricValue(b,model,'iou',Infinity));
    return copy.sort((a,b) => a.sample_id.localeCompare(b.sample_id));
  }

  function classificationStatus(result) {
    const observed = Number(result.verified) === 1;
    const predicted = Number(result.prediction) === 1;
    const outcome = observed === predicted ? 'Correct' : predicted ? 'False alert' : 'Missed';
    return `${outcome} · observed water ${observed ? 'present' : 'absent'}`;
  }

  return { sortSamples, classificationStatus };
});
