import {test,expect} from '@playwright/test';
import {routeFixture} from '../quality-fixture.mjs';

test('quality comparison selects noise and delay with paired 3D and full gates',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await routeFixture(page);await page.goto('/quality.html');
  await expect(page.getByRole('heading',{name:'How much feedback quality is enough?'})).toBeVisible();
  await page.getByRole('button',{name:'Landing outage'}).click();await expect(page.locator('output')).toHaveText('40.000 s');
  await expect(page.getByRole('region',{name:'Noise + 40 ms delay flight',exact:true})).toContainText('horizontal-noise-delay');
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.locator('canvas')).toHaveCount(2);
  for(const quality of ['noise','delay','noise-delay']) {
    await page.getByRole('combobox',{name:'Channel quality'}).selectOption(quality);
    await expect(page.getByRole('button',{name:'Play',exact:true})).toBeEnabled();
    await expect(page.locator('output')).toHaveText('0.000 s');
  }
  await page.getByRole('combobox',{name:'Seed',exact:true}).selectOption('2');
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeEnabled();
  const download=page.waitForEvent('download');await page.getByRole('link',{name:'Download verified full-rate study'}).click();
  expect((await download).suggestedFilename()).toBe('horizontal-quality-study.json');expect(errors).toEqual([]);
});
test('quality evidence rejects corruption and retains incomplete flights',async({page})=>{
  await routeFixture(page,{corrupt:true});await page.goto('/quality.html');await expect(page.getByRole('alert')).toContainText('integrity');
  await page.unrouteAll();await routeFixture(page,{incomplete:true});await page.reload();await expect(page.getByRole('alert')).toHaveCount(2);
});
test('quality selections cancel stale loads and fit narrow screens',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:320,height:844});
  await routeFixture(page,{delay:true});await page.goto('/quality.html');
  await page.getByRole('combobox',{name:'Channel quality'}).selectOption('noise');
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeEnabled();
  await expect(page.getByRole('region',{name:'Noise only flight',exact:true})).toBeVisible();
  for(const width of [320,390]) {
    await page.setViewportSize({width,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  }
});
