let data;
let syncingScroll = false;
const $ = id => document.getElementById(id);
const fmt = value => value == null ? '—' : Number(value).toFixed(3);
const modelLabel = name => name === 'unet' ? 'Deep U-Net' : 'Extra Trees';
const classifierLabel = name => name === 'lstm' ? 'Rainfall LSTM' : 'Spatial gradient baseline';

function eventNames() {
  return [...new Set(data.samples.map(sample => sample.event_name))];
}

function eventSamples() {
  const samples = data.samples.filter(sample => sample.event_name === $('event').value);
  return ViewerLogic.sortSamples(samples, $('focus-model').value, $('sort').value);
}

function fillEvents() {
  $('event').innerHTML = eventNames().map(name => `<option>${name}</option>`).join('');
  fillChips();
}

function fillChips(preferred) {
  const samples = eventSamples();
  $('chip').innerHTML = samples.map(sample => `<option value="${sample.sample_id}">${sample.sample_id}</option>`).join('');
  const selection = preferred && samples.some(sample => sample.sample_id === preferred)
    ? preferred
    : samples[0]?.sample_id;
  if (selection) $('chip').value = selection;
  render();
}

function eventMetric(model, eventName) {
  return data.models[model].events.find(event => event.event_name === eventName);
}

function comparisonTable(sample) {
  const tree = sample.models.extra_trees.metrics;
  const unet = sample.models.unet.metrics;
  const treeEvent = eventMetric('extra_trees', sample.event_name);
  const unetEvent = eventMetric('unet', sample.event_name);
  return `<h2>Model comparison</h2><table><thead><tr><th>Scope</th><th>Extra Trees</th><th>U-Net</th></tr></thead><tbody>
    <tr><td>Chip IoU</td><td>${fmt(tree.iou)}</td><td>${fmt(unet.iou)}</td></tr>
    <tr><td>${sample.event_name} IoU</td><td>${fmt(treeEvent.iou)}</td><td>${fmt(unetEvent.iou)}</td></tr>
    <tr><td>Held-out IoU</td><td>${fmt(data.models.extra_trees.test.iou)}</td><td>${fmt(data.models.unet.test.iou)}</td></tr>
    <tr><td>Held-out F1</td><td>${fmt(data.models.extra_trees.test.f1)}</td><td>${fmt(data.models.unet.test.f1)}</td></tr>
    <tr><td>Threshold</td><td>${data.models.extra_trees.threshold.toFixed(2)}</td><td>${data.models.unet.threshold.toFixed(2)}</td></tr>
  </tbody></table>`;
}

function runDetails() {
  const run = data.run;
  $('run-details').innerHTML = `<dl>
    <dt>Experiment</dt><dd>${run.artifact_id || 'prototype'}</dd>
    <dt>Image grid</dt><dd>${run.native_resolution} × ${run.native_resolution}</dd>
    <dt>U-Net tiles</dt><dd>${run.tile_size} px, ${run.overlap} px overlap</dd>
    <dt>Best epoch</dt><dd>${run.best_epoch} of ${run.epochs_trained}</dd>
    <dt>Seed</dt><dd>${run.seed}</dd>
  </dl><p class="method">${run.checkpoint_selection}. ${run.threshold_selection}.</p>`;
  $('experiment-history').innerHTML = `<table><thead><tr><th>Run</th><th>Grid</th><th>Tree F1</th><th>U-Net F1</th></tr></thead><tbody>${data.experiments.map(experiment => `<tr><td>${experiment.artifact_id}</td><td>${experiment.resolution}px</td><td>${fmt(experiment.models.extra_trees?.f1)}</td><td>${fmt(experiment.models.unet?.f1)}</td></tr>`).join('')}</tbody></table>`;
}

function classificationResults(sample) {
  $('classification-results').innerHTML = ['baseline', 'lstm'].map(name => {
    const result = sample.classifiers[name];
    const model = data.classifiers[name];
    return `<article><div><strong>${classifierLabel(name)}</strong><span>${ViewerLogic.classificationStatus(result)}</span></div><b>${(result.probability * 100).toFixed(1)}%</b><small>model score · threshold ${(model.threshold * 100).toFixed(0)}% · held-out F1 ${fmt(model.test.f1)}</small></article>`;
  }).join('');
}

function render() {
  const sample = data.samples.find(item => item.sample_id === $('chip').value);
  if (!sample) return;
  const focus = $('focus-model').value;
  $('sar').src = sample.sar;
  $('label').src = sample.label;
  $('tree-prediction').src = sample.models.extra_trees.prediction;
  $('unet-prediction').src = sample.models.unet.prediction;
  $('tree-errors').src = sample.models.extra_trees.errors;
  $('unet-errors').src = sample.models.unet.errors;
  $('overlay-sar').src = sample.sar;
  $('overlay-mask').src = sample.models[focus].prediction;
  $('overlay-caption').textContent = modelLabel(focus);
  $('tree-chip-score').textContent = `IoU ${fmt(sample.models.extra_trees.metrics.iou)}`;
  $('unet-chip-score').textContent = `IoU ${fmt(sample.models.unet.metrics.iou)}`;
  $('context').innerHTML = `<strong>${sample.event_name}</strong><span>${sample.event_date}</span><span>${sample.latitude.toFixed(3)}, ${sample.longitude.toFixed(3)}</span><span>Native 512 × 512 grid</span>`;
  $('summary').innerHTML = comparisonTable(sample);
  classificationResults(sample);
  applyZoom();
}

function applyZoom() {
  const zoom = Number($('zoom').value);
  $('zoom-value').textContent = `${zoom.toFixed(2).replace(/0$/, '')}×`;
  document.querySelectorAll('.zoom-image').forEach(image => image.style.width = `${zoom * 100}%`);
  document.querySelector('.overlay-content').style.width = `${zoom * 100}%`;
}

function applyOpacity() {
  const opacity = Number($('opacity').value);
  $('opacity-value').textContent = `${opacity}%`;
  $('overlay-mask').style.opacity = opacity / 100;
}

function syncViewports(source) {
  if (syncingScroll) return;
  syncingScroll = true;
  document.querySelectorAll('.viewport').forEach(viewport => {
    if (viewport !== source) {
      viewport.scrollLeft = source.scrollLeft;
      viewport.scrollTop = source.scrollTop;
    }
  });
  requestAnimationFrame(() => { syncingScroll = false; });
}

fetch('data/viewer-data.json')
  .then(response => {
    if (!response.ok) throw Error('Missing exported viewer data');
    return response.json();
  })
  .then(payload => {
    data = payload;
    $('disclaimer').textContent = data.disclaimer;
    runDetails();
    fillEvents();
    applyOpacity();
    $('event').onchange = () => fillChips();
    $('chip').onchange = render;
    $('sort').onchange = () => fillChips();
    $('focus-model').onchange = () => fillChips();
    $('zoom').oninput = applyZoom;
    $('opacity').oninput = applyOpacity;
    document.querySelectorAll('.viewport').forEach(viewport => viewport.addEventListener('scroll', () => syncViewports(viewport)));
  })
  .catch(error => {
    $('disclaimer').textContent = `${error.message} — run the training and export scripts first.`;
  });
