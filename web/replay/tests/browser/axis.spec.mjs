import {test,expect} from '@playwright/test';
import {routeFixture} from '../axis-fixture.mjs';
test('axis comparison switches channels and cohorts with paired 3D and full gates',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await routeFixture(page);await page.goto('/axis.html');
  await expect(page.getByRole('heading',{name:'Which feedback keeps landing stable?'})).toBeVisible();
  await page.getByRole('button',{name:'Landing outage'}).click();await expect(page.locator('output')).toHaveText('40.000 s');
  await expect(page.getByRole('region',{name:'Fresh altitude flight',exact:true})).toContainText('vertical-fresh');
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.locator('canvas')).toHaveCount(2);
  await page.getByRole('combobox',{name:'Fresh channel'}).selectOption('horizontal');
  await expect(page.getByRole('region',{name:'Fresh horizontal flight',exact:true})).toContainText('horizontal-fresh');
  await page.getByRole('combobox',{name:'Cohort',exact:true}).selectOption('prior-validation');
  await page.getByRole('combobox',{name:'Seed',exact:true}).selectOption('303');
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeEnabled();
  const download=page.waitForEvent('download');await page.getByRole('link',{name:'Download verified full-rate study'}).click();
  expect((await download).suggestedFilename()).toBe('axis-availability-study.json');expect(errors).toEqual([]);
});
test('axis evidence fails closed and preserves incomplete recordings',async({page})=>{
  await routeFixture(page,{corrupt:true});await page.goto('/axis.html');await expect(page.getByRole('alert')).toContainText('integrity');
  await page.unrouteAll();await routeFixture(page,{incomplete:true});await page.reload();await expect(page.getByRole('alert')).toHaveCount(2);
});
test('axis selections cancel stale requests and remain usable on narrow screens',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:390,height:844});
  await routeFixture(page,{delay:true});await page.goto('/axis.html');
  await page.getByRole('combobox',{name:'Fresh channel'}).selectOption('horizontal');
  await page.getByRole('combobox',{name:'Cohort',exact:true}).selectOption('prior-validation');
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeEnabled();await expect(page.locator('output')).toHaveText('0.000 s');
  await expect(page.getByRole('region',{name:'Fresh horizontal flight',exact:true})).toBeVisible();
  for(const width of [320,390]) {
    await page.setViewportSize({width,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  }
});
