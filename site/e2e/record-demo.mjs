// Records the README demo GIF from the live playground. Usage: npm i --no-save playwright@1.65.1; node site/e2e/record-demo.mjs; then ffmpeg (see docs/assets/README note). Not part of CI.
import {chromium} from 'playwright';
const b = await chromium.launch();
const ctx = await b.newContext({viewport:{width:1100,height:700}, recordVideo:{dir:'vid',size:{width:1100,height:700}}});
const p = await ctx.newPage();
await p.goto('https://jmmana.github.io/sqltoviz/#play', {waitUntil:'networkidle'});
await p.waitForSelector('#example option',{state:'attached'});
const opts = await p.$$eval('#example option', o => o.map(x => x.value));
console.log(opts);
await p.locator('#play').scrollIntoViewIfNeeded();
await p.waitForTimeout(1200);
for (const v of opts.slice(0,3)) {
  await p.selectOption('#example', v); await p.click('#load'); await p.waitForTimeout(900);
  await p.click('#run'); await p.waitForTimeout(2200);
}
await ctx.close(); await b.close();
