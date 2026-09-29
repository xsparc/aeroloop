import {test,expect} from '@playwright/test';
import {routeFixture} from '../landing-fixture.mjs';
test('landing comparison exposes both cohorts, guard chapters, commands and 3D',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await routeFixture(page);await page.goto('/landing.html');
  await expect(page.getByRole('heading',{name:'Landing after lost captures'})).toBeVisible();
  await page.getByRole('button',{name:'Guard activates'}).click();await expect(page.locator('output')).toHaveText('41.000 s');
  const guarded=page.getByRole('region',{name:'Prediction + landing guard flight',exact:true});
  await expect(guarded).toContainText('holding');await expect(guarded).toContainText('0.300 m');await expect(guarded).toContainText('1.500 m');
  await page.getByRole('button',{name:'Descent resumes'}).click();await expect(page.locator('output')).toHaveText('48.000 s');
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.locator('canvas')).toHaveCount(2);
  await page.getByRole('combobox',{name:'Cohort',exact:true}).selectOption('unseen');await expect(page.getByRole('combobox',{name:'Seed',exact:true})).toHaveValue('101');
  await page.getByRole('combobox',{name:'Seed',exact:true}).selectOption('303');await expect(page.locator('output')).toHaveText('0.000 s');
  await page.getByRole('combobox',{name:'Capture outage'}).selectOption('0');await expect(page.getByRole('button',{name:'Guard activates'})).toBeDisabled();
  await expect(page.getByText('Full-rate mission: PASSED',{exact:false})).toHaveCount(2);
  const downloaded=page.waitForEvent('download');await page.getByRole('link',{name:'Download verified full-rate study'}).click();expect((await downloaded).suggestedFilename()).toBe('landing-guard-study.json');expect(errors).toEqual([]);
});
test('landing evidence corruption fails closed; short flights retain failures',async({page})=>{
  await routeFixture(page,{corrupt:true});await page.goto('/landing.html');await expect(page.getByRole('alert')).toContainText('integrity');
  await page.unrouteAll();await routeFixture(page,{incomplete:true});await page.reload();await expect(page.getByRole('alert')).toHaveCount(2);await expect(page.getByRole('button',{name:'Descent resumes'})).toBeDisabled();
});
test('cohort changes cancel stale loads and narrow reduced-motion playback stays paused',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:390,height:844});
  await routeFixture(page,{delay:true});await page.goto('/landing.html');
  await page.getByRole('combobox',{name:'Cohort',exact:true}).selectOption('unseen');await page.getByRole('combobox',{name:'Seed',exact:true}).selectOption('303');
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeEnabled();await expect(page.locator('output')).toHaveText('0.000 s');
  await expect(page.getByRole('combobox',{name:'Seed',exact:true})).toHaveValue('303');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
