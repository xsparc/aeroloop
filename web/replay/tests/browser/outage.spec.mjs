import {test,expect} from '@playwright/test';
import {routeFixture} from '../outage-fixture.mjs';
test('outage demo plays synchronized 3D with failed gates, chapters and downloads',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await routeFixture(page);await page.goto('/outage.html');
  await expect(page.getByText('Full-rate mission: FAILED',{exact:false})).toHaveCount(2);
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.locator('canvas')).toHaveCount(2);
  await expect(page.locator('canvas').first()).toBeVisible();
  await page.getByRole('button',{name:'First outage',exact:true}).click();await expect(page.locator('output')).toHaveText('18.000 s');
  await expect(page.getByText('predicting',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Play',exact:true}).click();await expect(page.locator('output')).not.toHaveText('18.000 s');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.getByRole('button',{name:'Capture resumes'}).click();await expect(page.locator('output')).toHaveText('20.000 s');
  await expect(page.getByText('capture',{exact:true})).toBeVisible();
  await page.getByRole('combobox',{name:'Seed',exact:true}).selectOption('2');await expect(page.locator('output')).toHaveText('0.000 s');
  await page.getByRole('combobox',{name:'Capture outage'}).selectOption('0');await expect(page.getByText('Full-rate mission: PASSED',{exact:false})).toHaveCount(2);
  await page.getByText('Inspect all acceptance gates').first().click();await expect(page.locator('.flight-card table').first()).toContainText('Position RMSE');
  const downloaded=page.waitForEvent('download');await page.getByRole('link',{name:'Download verified full-rate study'}).click();expect((await downloaded).suggestedFilename()).toBe('predictive-feedback-study.json');expect(errors).toEqual([]);
});
test('corruption fails closed and truncated evidence stays failed',async({page})=>{
  await routeFixture(page,{corrupt:true});await page.goto('/outage.html');await expect(page.getByRole('alert')).toContainText('integrity');await expect(page.getByRole('button',{name:'Play',exact:true})).toBeDisabled();
  await page.unrouteAll();await routeFixture(page,{incomplete:true});await page.reload();await expect(page.getByRole('alert')).toHaveCount(2);await expect(page.getByRole('alert').first()).toContainText('Incomplete');
});
test('rapid changes, narrow reduced motion and WebGL fallback retain numeric evidence',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:390,height:844});
  await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return kind.includes('webgl')?null:get.call(this,kind,...args);};});
  await routeFixture(page,{delay:true});await page.goto('/outage.html');
  await page.getByRole('combobox',{name:'Seed',exact:true}).selectOption('1');await page.getByRole('combobox',{name:'Seed',exact:true}).selectOption('2');
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.getByText(/3D is unavailable/)).toHaveCount(2);
  await expect(page.locator('output')).toHaveText('0.000 s');await expect(page.getByText(/Reduced motion:/)).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
test('playback pauses with hidden or offscreen comparisons',async({page})=>{
  await routeFixture(page);await page.goto('/outage.html');
  await page.getByRole('button',{name:'Play',exact:true}).click();await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible();
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));});
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeVisible();
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,value:false});document.dispatchEvent(new Event('visibilitychange'));});
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await page.evaluate(()=>{const footer=document.querySelector('footer');footer.style.height='2000px';scrollTo(0,document.body.scrollHeight);});
  await expect(page.getByRole('button',{name:'Play',exact:true})).toHaveCount(1);
});
