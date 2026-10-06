import {test,expect} from '@playwright/test';
import {routeFixture} from '../approach-fixture.mjs';
test('gain workspace renders paired 3D, gust chapters, gate regressions, links and export',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));await routeFixture(page);await page.goto('/approach.html');
  await expect(page.getByTestId('selected-case')).toContainText('stress · seed 401');
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.locator('canvas')).toHaveCount(2);
  await page.getByRole('region',{name:'candidate',exact:true}).getByRole('button',{name:'Jump to contact'}).click();await expect(page.getByTestId('cursor')).toHaveText('41.200 s simulation time');
  await page.getByRole('checkbox',{name:'Gust-relative time'}).check();await expect(page.getByTestId('cursor')).toHaveText('1.200 s from gust');
  await page.getByRole('button',{name:'Share review'}).click();await page.reload();await expect(page.getByTestId('cursor')).toHaveText('1.200 s from gust');
  const event=page.waitForEvent('download');await page.getByRole('button',{name:'Export review JSON'}).click();expect((await event).suggestedFilename()).toBe('stress-p0-s401-approach.json');
  await page.getByRole('button',{name:'Play ½×'}).click();await expect(page.getByTestId('cursor')).not.toHaveText('1.200 s from gust');await page.getByRole('button',{name:'Pause',exact:true}).click();expect(errors).toEqual([]);
});
test('cohort and regression filters, narrow layout and stale selections work',async({page})=>{
  await routeFixture(page,{delay:'regression-p0-s0.json'});await page.goto('/approach.html');await expect(page.getByTestId('selected-case')).toContainText('401');
  await page.getByLabel('Outcome filter',{exact:true}).selectOption('regressed');await expect(page.locator('.ag-cases button')).toHaveCount(6);
  await page.getByLabel('Cohort',{exact:true}).selectOption('stress');await expect(page.locator('.ag-cases button')).toHaveCount(0);await expect(page.getByTestId('selected-case')).toContainText('401');
  await page.getByLabel('Cohort',{exact:true}).selectOption('regression');await page.locator('.ag-cases button').first().click();await page.locator('.ag-cases button').last().click();await expect(page.getByTestId('selected-case')).toContainText('seed 2');await page.waitForTimeout(900);await expect(page.getByTestId('selected-case')).toContainText('seed 2');
  for(const width of [320,390]){await page.setViewportSize({width,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
});
test('missing landing samples and corrupt payloads fail closed',async({page})=>{
  await routeFixture(page,{incomplete:true});await page.goto('/approach.html');await page.locator('.ag-cases button').filter({hasText:'stress · 401 · 2 s outages'}).click();await expect(page.getByRole('region',{name:'candidate',exact:true})).toContainText('No landing samples');await expect(page.getByRole('button',{name:'Play ½×'})).toBeDisabled();
  await page.unrouteAll();await routeFixture(page,{corrupt:true});await page.goto('/approach.html');await expect(page.getByRole('alert')).toContainText('integrity');await expect(page.getByRole('region',{name:'candidate',exact:true})).toHaveCount(0);
});
