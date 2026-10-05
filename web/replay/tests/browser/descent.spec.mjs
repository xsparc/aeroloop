import {test,expect} from '@playwright/test';
import {routeFixture} from '../descent-fixture.mjs';
test('paired descent renders 3D, plays, inspects contact, shares and exports',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));await routeFixture(page);await page.goto('/descent.html');
  await expect(page.getByRole('region',{name:'candidate',exact:true})).toContainText('Mission FAILED');
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.locator('canvas')).toHaveCount(2);
  await page.getByLabel('Alignment',{exact:true}).selectOption('touchdown');await expect(page.getByTestId('cursor')).toContainText('0.000 s from each touchdown');
  await expect(page.getByLabel('candidate contact inspector')).toContainText('0 / 50 ms');
  await page.getByRole('button',{name:'Next step',exact:true}).click();await expect(page.getByLabel('candidate contact inspector')).toContainText('5 / 50 ms');
  await page.getByRole('button',{name:'Share selection'}).click();const link=await page.getByLabel('Selection link',{exact:true}).inputValue();expect(link).toContain('mode=touchdown');
  await page.reload();await expect(page.getByTestId('cursor')).toContainText('0.005 s from each touchdown');
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Export comparison JSON'}).click();expect((await download).suggestedFilename()).toBe('regression-p1-s0-touchdown.json');
  await page.getByRole('button',{name:'Play ½×'}).click();await expect(page.getByTestId('cursor')).not.toContainText('0.005 s');await page.getByRole('button',{name:'Pause',exact:true}).click();expect(errors).toEqual([]);
});
test('all cases select, narrow layout fits, and short evidence stays incomplete',async({page})=>{
  const data=await routeFixture(page);await page.goto('/descent.html');await expect(page.getByRole('button',{name:'Export comparison JSON'})).toBeEnabled();
  for(const entry of data.index.cases){await page.getByLabel('Case',{exact:true}).selectOption(entry.id);await expect(page.getByRole('region',{name:'candidate',exact:true})).toBeVisible();}
  for(const width of [320,390]){await page.setViewportSize({width,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  await page.unrouteAll();await routeFixture(page,{incomplete:true});await page.goto('/descent.html');await expect(page.getByRole('region',{name:'candidate',exact:true})).toContainText('Incomplete recording');
  await expect(page.getByRole('option',{name:'Each flight’s touchdown'})).toHaveJSProperty('disabled',true);
});
test('invalid checksums prevent display',async({page})=>{await routeFixture(page,{corrupt:true});await page.goto('/descent.html');await expect(page.getByRole('alert')).toContainText('integrity');await expect(page.getByRole('button',{name:'Export comparison JSON'})).toBeDisabled();});
