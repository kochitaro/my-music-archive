#!/usr/bin/env node
'use strict';
// Explicit publication boundary: never discover files using a glob or recursion.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'dist');
// This branch is a Preview authentication test page only, regardless of environment variables.
const files = ['index.html', '404.html'];

function statIfPresent(file) {
  try { return fs.lstatSync(file); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

function regularFile(name) {
  const stat = fs.lstatSync(path.join(root, name));
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error('Expected regular file: ' + name);
}

// Remove stale output first, including when validation subsequently fails.
// Never follow a dist symlink or delete anything outside this fixed directory.
const previous = statIfPresent(out);
if (previous) {
  const stat = previous;
  if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error('dist must be a real directory');
  fs.rmSync(out, { recursive: true });
}
try {
  files.forEach(regularFile);
  const allowed = new Set(files);
  function checkReference(ref, owner) {
    if (!ref || /^(?:[a-z][a-z0-9+.-]*:|#)/i.test(ref)) return;
    if (ref.startsWith('/')) throw new Error('Use relative local paths: ' + owner + ' -> ' + ref);
    const name = path.posix.normalize(ref.split(/[?#]/)[0]);
    if (name && name !== '.' && name !== './' && !allowed.has(name)) {
      throw new Error('Local dependency missing from publication list: ' + owner + ' -> ' + ref);
    }
  }
  for (const file of files) {
    const text = fs.readFileSync(path.join(root, file), 'utf8');
    if (file.endsWith('.html')) {
      for (const match of text.matchAll(/\b(?:src|href)\s*=\s*["']([^"']*)["']/gi)) checkReference(match[1], file);
    }
    if (file.endsWith('.css')) {
      for (const match of text.matchAll(/url\(\s*["']?([^"')\s]+)["']?\s*\)/gi)) checkReference(match[1], file);
    }
  }
  fs.mkdirSync(out);
  for (const file of files) fs.copyFileSync(path.join(root, file), path.join(out, file));
  // Enables direct static publishing with GitHub Pages as well as artifact workflows.
  fs.writeFileSync(path.join(out, '.nojekyll'), '');
  console.log('Static files in dist (' + (files.length + 1) + '):\n' + [...files, '.nojekyll'].sort().join('\n'));
} catch (error) {
  fs.rmSync(out, { recursive: true, force: true });
  console.error(error.message);
  process.exitCode = 1;
}
