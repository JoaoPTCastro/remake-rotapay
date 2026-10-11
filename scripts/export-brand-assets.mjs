// Exportação local reproduzível dos SVGs: PNGs transparentes e favicon ICO.
import { createRequire } from "node:module";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const require = createRequire(path.join(root, "frontend/package.json"));
const { chromium } = require("playwright");
const dir = path.join(root, "frontend/public/brand");
const browser = await chromium.launch();
try {
  for (const [name, width, height] of [
    ["rotapay-logo", 1152, 320],
    ["rotapay-logo-dark", 1152, 320],
    ["rotapay-mark", 512, 512],
  ]) {
    const svg = await readFile(path.join(dir, `${name}.svg`), "utf8");
    const page = await browser.newPage({ viewport: { width, height } });
    await page.setContent(`<style>html,body{margin:0;background:transparent}svg{display:block;width:${width}px;height:${height}px}</style>${svg}`);
    await page.screenshot({ path: path.join(dir, `${name}.png`), omitBackground: true });
    if (name === "rotapay-mark") {
      await page.setViewportSize({ width: 64, height: 64 });
      await page.addStyleTag({ content: "svg{width:64px;height:64px}" });
      const png = await page.screenshot({ omitBackground: true });
      const header = Buffer.alloc(22);
      header.writeUInt16LE(1, 2); // ICO
      header.writeUInt16LE(1, 4); // Uma imagem
      header[6] = 64;
      header[7] = 64;
      header.writeUInt16LE(1, 10);
      header.writeUInt16LE(32, 12);
      header.writeUInt32LE(png.length, 14);
      header.writeUInt32LE(22, 18);
      await writeFile(path.join(root, "frontend/app/favicon.ico"), Buffer.concat([header, png]));
    }
    await page.close();
    console.log(`Exportado: ${name}.png`);
  }
} finally {
  await browser.close();
}
