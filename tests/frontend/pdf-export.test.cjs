// Exercise the real jsPDF API used by each workspace after the security update.
// Run from each frontend so its own locked dependency is tested, not a global one.
const assert = require('node:assert/strict');
const { createRequire } = require('node:module');
const path = require('node:path');
const test = require('node:test');
const localRequire = createRequire(path.join(process.cwd(), 'package.json'));
const { jsPDF } = localRequire('jspdf');

test('assessment export supports text, image, pagination, and PDF serialization', () => {
  const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  pdf.setFontSize(18);
  pdf.text('Agent Trust Platform assessment', 10, 15);
  pdf.addImage('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=', 'PNG', 10, 20, 30, 30);
  pdf.addPage();
  pdf.text('Findings and limitations', 10, 15);
  const output = pdf.output('arraybuffer');
  assert.ok(output.byteLength > 500);
  assert.ok(Buffer.from(output).toString('latin1').startsWith('%PDF-'));
  assert.equal(pdf.getNumberOfPages(), 2);
});
