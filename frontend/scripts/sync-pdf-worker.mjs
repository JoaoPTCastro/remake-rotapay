import { readFile, mkdir, copyFile } from 'node:fs/promises';
const packageUrl = new URL('../node_modules/pdfjs-dist/package.json', import.meta.url);
const { version } = JSON.parse(await readFile(packageUrl, 'utf8'));
if (version !== '6.3.289') throw new Error('Versão inesperada de PDF.js; revise o worker antes de atualizar.');
const destino = new URL(`../public/pdfjs/${version}/`, import.meta.url);
await mkdir(destino, { recursive: true });
await copyFile(new URL('../node_modules/pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url), new URL('pdf.worker.min.mjs', destino));
