import {test,expect} from '@playwright/test';
import {routeFixture} from '../friction-fixture.mjs';
test('contact review supports 3D, windows, reports, links and narrow screens',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));await routeFixture(page);await page.goto('/friction.html');await expect(page.getByRole('heading',{name:'02 / Inspect a landing'})).toBeVisible();
  await page.getByRole('button',{name:'Show 3D',exact:true}).click();await expect(page.locator('canvas')).toHaveCount(1);await expect.poll(()=>page.evaluate(()=>{const c=document.querySelector('canvas').getBoundingClientRect(),p=document.querySelector('.friction-scene').getBoundingClientRect();return c.top>=p.top&&c.bottom<=p.bottom&&c.left>=p.left&&c.right<=p.right;})).toBe(true);
  await page.getByRole('button',{name:'Final support',exact:true}).click();await expect(page.getByLabel('Window start')).toHaveValue('48');await page.getByRole('button',{name:'Create review link'}).click();expect(page.url()).toContain('start=48');
  for(const name of ['Download interval CSV','Download review JSON']){const d=page.waitForEvent('download');await page.getByRole('button',{name}).click();expect((await d).suggestedFilename()).toContain('fixed-intact-s401');}
  await page.reload();await expect(page.getByLabel('Window start')).toHaveValue('48');
  await page.setViewportSize({width:320,height:844});await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth)).toBe(320);expect(errors).toEqual([]);
});
test('corrupt contact trace cannot be replayed',async({page})=>{await routeFixture(page,{corrupt:true});await page.goto('/friction.html');await expect(page.getByRole('alert')).toContainText('integrity');await expect(page.getByRole('button',{name:'Show 3D'})).toHaveCount(0);});
test('live contact reports stale captures and does not retain unavailable data',async({page})=>{
  await page.route('**/api/contact',r=>r.fulfill({json:{schema_version:1,seed:401,time_s:42,normal_n:[0,0,9.81],friction_n:[-.4,0,0],anchors:2,age_s:3,stale:true}}));await page.goto('/friction-live.html');await expect(page.getByRole('heading',{name:'Stale / stopped capture'})).toBeVisible();await page.unrouteAll();await page.route('**/api/contact',r=>r.fulfill({status:503,json:{state:'unavailable'}}));await expect(page.getByRole('alert')).toContainText('unavailable');await expect(page.getByText('Friction anchors')).toHaveCount(0);
});

test('rejected timestep stays visible without a verified replay',async({page})=>{await routeFixture(page,{rejected:true});await page.goto('/friction.html');await expect(page.getByRole('heading',{name:'Unverified timestep capture'})).toBeVisible();await expect(page.getByText('No verified force/work metrics or replay',{exact:false})).toBeVisible();await expect(page.getByRole('button',{name:'ideal-intact-s301-dt1250',exact:true})).toHaveCount(0);});
