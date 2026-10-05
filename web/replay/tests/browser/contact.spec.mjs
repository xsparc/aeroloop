import {test,expect} from '@playwright/test';
import {routeFixture} from '../contact-fixture.mjs';

test('landing lab renders paired 3D, audits, jumps, shares settings and exports',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));await routeFixture(page);await page.goto('/contact.html');
  const candidate=page.getByRole('region',{name:'candidate',exact:true});await expect(candidate).toContainText('Mission FAILED');await expect(candidate).toContainText('position, dwell');
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.locator('canvas')).toHaveCount(2);
  await candidate.getByRole('button',{name:'Jump to contact'}).click();await expect(page.getByTestId('cursor')).toHaveText('41.200 s');
  await page.getByRole('button',{name:'Next step',exact:true}).click();await expect(page.getByTestId('cursor')).toHaveText('41.205 s');
  await page.getByLabel('Distance from home · m',{exact:true}).fill('0.5');await expect(candidate).toContainText('First qualifying time: 41.250 s');
  await page.getByRole('button',{name:'Share review'}).click();await expect(page.getByLabel('Review link',{exact:true})).toHaveValue(/position=0.5/);
  await page.reload();await expect(page.getByTestId('cursor')).toHaveText('41.205 s');await expect(page.getByLabel('Distance from home · m',{exact:true})).toHaveValue('0.5');
  const event=page.waitForEvent('download');await page.getByRole('button',{name:'Export review JSON'}).click();expect((await event).suggestedFilename()).toBe('additional-p0-s401-contact.json');
  await page.getByRole('button',{name:'Play ½×'}).click();await expect(page.getByTestId('cursor')).not.toHaveText('41.205 s');await page.getByRole('button',{name:'Pause',exact:true}).click();expect(errors).toEqual([]);
});

test('queue filters, case selection and narrow layout work with retained failures',async({page})=>{
  await routeFixture(page);await page.goto('/contact.html');await expect(page.getByTestId('selected-case')).toContainText('seed 401');
  await page.getByLabel('Cohort',{exact:true}).selectOption('regression');await expect(page.locator('.ct-queue tbody tr')).toHaveCount(6);
  await page.getByRole('checkbox',{name:'Failed missions only'}).check();await expect(page.locator('.ct-queue tbody tr')).toHaveCount(6);
  await page.getByRole('button',{name:'regression · 1 · 2 s outage',exact:true}).click();await expect(page.getByTestId('selected-case')).toContainText('regression · seed 1');
  for(const width of [320,390]){await page.setViewportSize({width,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
});

test('short flights and corrupt evidence cannot turn missing landing data into a pass',async({page})=>{
  await routeFixture(page,{incomplete:true});await page.goto('/contact.html');await page.getByRole('button',{name:'additional · 401 · 2 s outage',exact:true}).click();
  await expect(page.getByRole('region',{name:'candidate',exact:true})).toContainText('No landing samples');await expect(page.getByRole('button',{name:'Play ½×'})).toBeDisabled();
  await page.unrouteAll();await routeFixture(page,{corrupt:true});await page.goto('/contact.html');await expect(page.getByRole('alert')).toContainText('integrity');await expect(page.getByRole('region',{name:'candidate',exact:true})).toHaveCount(0);
});

test('slow stale case never replaces the newer selection',async({page})=>{
  await routeFixture(page,{delay:'regression-p0-s0.json'});await page.goto('/contact.html');await expect(page.getByTestId('selected-case')).toContainText('seed 401');
  await page.getByRole('button',{name:'regression · 0 · no outage',exact:true}).click();await page.getByRole('button',{name:'regression · 2 · 2 s outage',exact:true}).click();
  await expect(page.getByTestId('selected-case')).toContainText('regression · seed 2');await page.waitForTimeout(900);await expect(page.getByTestId('selected-case')).toContainText('regression · seed 2');
});
