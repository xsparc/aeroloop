import {test,expect} from '@playwright/test';
import {routeFixture} from '../diagnosis-fixture.mjs';
test('diagnosis exposes ten tools, paired 3D, precise events, playback and CSV',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));await routeFixture(page);await page.goto('/diagnosis.html');
  await expect(page.getByRole('heading',{name:'10 / Export this window'})).toBeVisible();
  await expect(page.getByRole('region',{name:'Selected flight',exact:true})).toContainText('FAILED');
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.locator('canvas')).toHaveCount(2);
  expect(await page.locator('.dg-scene').evaluateAll(cards=>cards.every(card=>{const a=card.getBoundingClientRect(),b=card.querySelector('canvas').getBoundingClientRect();return b.width>100&&b.height>100&&b.left>=a.left&&b.right<=a.right&&b.top>=a.top&&b.bottom<=a.bottom;}))).toBe(true);
  await page.getByRole('button',{name:'touchdown 41.225 s',exact:true}).click();await expect(page.getByRole('status',{name:'Recorded time'})).toHaveText('41.225 s');
  await page.getByRole('button',{name:'Play',exact:true}).click();await expect(page.getByRole('status',{name:'Recorded time'})).not.toHaveText('41.225 s');await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.getByLabel('Raw capture',{exact:true}).uncheck();await expect(page.getByLabel('Raw capture',{exact:true})).not.toBeChecked();
  await page.getByRole('button',{name:'Landing window',exact:true}).click();
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download window CSV'}).click();expect((await download).suggestedFilename()).toBe('q3-p1-s0-40.000-43.000.csv');
  await page.getByText('Inspect source, hashes and runtime',{exact:true}).click();await expect(page.getByText('source dirty',{exact:true})).toBeVisible();expect(errors).toEqual([]);
});
test('matrix filters preserve failure, sort by margin and identify self comparisons',async({page})=>{
  const fixture=await routeFixture(page);await page.goto('/diagnosis.html');await expect(page.getByRole('button',{name:'Download window CSV'})).toBeVisible();
  await page.getByLabel('Mission outcome',{exact:true}).selectOption('failed');await expect(page.getByRole('button',{pressed:true})).toHaveCount(1);await expect(page.getByText(fixture.index.cases.filter(c=>c.status==='failed').length+' of 24 cases · seed 0 / 1 / 2',{exact:true})).toBeVisible();
  await page.getByLabel('Mission outcome',{exact:true}).selectOption('all');await page.getByLabel('Sort cases',{exact:true}).selectOption('support');
  await page.getByLabel('Profile',{exact:true}).selectOption('sample-hold');await page.getByLabel('Flight cases').getByRole('button').first().click();
  await expect(page.getByText(/Reference-to-self:/)).toBeVisible();await expect(page.getByText('Not applicable to the no-outage reference. Self-comparison is not a recovery pass.')).toBeVisible();
});
test('corrupt evidence fails closed; truncated and stale loads remain honest',async({page})=>{
  await routeFixture(page,{corrupt:true});await page.goto('/diagnosis.html');await expect(page.getByRole('alert')).toContainText('integrity');await expect(page.getByRole('button',{name:'Download window CSV'})).toHaveCount(0);
  await page.unrouteAll();await routeFixture(page,{incomplete:true,delay:true});await page.reload();
  await page.getByLabel('Flight cases').getByRole('button').first().click();await expect(page.getByText(/Reference-to-self:/)).toBeVisible();
  await page.getByLabel('Flight cases').getByRole('button').filter({hasText:'Noise + delay · seed 0'}).filter({hasText:'2 s outages'}).click();
  await expect(page.getByRole('alert')).toContainText('Incomplete recording');await expect(page.getByText('0 / 400 samples · incomplete coverage. Empty states remain unmeasured.')).toBeVisible();
});
test('diagnosis stays keyboard accessible and fits narrow screens',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:320,height:844});await routeFixture(page);await page.goto('/diagnosis.html');
  await expect(page.getByRole('button',{name:'Download window CSV'})).toBeVisible();
  const slider=page.getByRole('slider',{name:'Recorded time'});await slider.focus();await slider.press('ArrowRight');await expect(page.getByRole('status',{name:'Recorded time'})).toHaveText('40.005 s');
  for(const width of [320,390]){await page.setViewportSize({width,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeVisible();
});
