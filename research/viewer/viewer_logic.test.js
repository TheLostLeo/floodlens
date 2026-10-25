const test = require('node:test');
const assert = require('node:assert/strict');
const logic = require('./viewer_logic.js');

test('sortSamples ranks missed water by false negatives', () => {
  const samples = [
    {sample_id:'a', models:{unet:{metrics:{fn:2, fp:9, iou:.4}}}},
    {sample_id:'b', models:{unet:{metrics:{fn:7, fp:1, iou:.6}}}},
  ];
  assert.deepEqual(logic.sortSamples(samples, 'unet', 'missed').map(x=>x.sample_id), ['b','a']);
});

test('sortSamples ranks worst overlap with undefined values last', () => {
  const samples = [
    {sample_id:'a', models:{unet:{metrics:{iou:null}}}},
    {sample_id:'b', models:{unet:{metrics:{iou:.2}}}},
    {sample_id:'c', models:{unet:{metrics:{iou:.7}}}},
  ];
  assert.deepEqual(logic.sortSamples(samples, 'unet', 'worst').map(x=>x.sample_id), ['b','c','a']);
});

test('classificationStatus explains correct and incorrect chip predictions', () => {
  assert.equal(logic.classificationStatus({prediction:1, verified:1}), 'Correct · observed water present');
  assert.equal(logic.classificationStatus({prediction:0, verified:1}), 'Missed · observed water present');
  assert.equal(logic.classificationStatus({prediction:1, verified:0}), 'False alert · observed water absent');
  assert.equal(logic.classificationStatus({prediction:0, verified:0}), 'Correct · observed water absent');
});
