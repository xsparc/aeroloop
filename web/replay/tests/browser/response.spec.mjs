import {test,expect} from '@playwright/test';
import {routeFixture} from '../approach-fixture.mjs';
test('four-flight replay, matched phases, diagnostics, review links and numeric exports',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));await routeFixture(page);await page.goto('/response.html');
  await expect(page.getByTestId('response-selected')).toHaveText('02 / stress · seed 401');
  await page.getByRole('button',{name:'Enable four-flight 3D'}).click();await expect(page.locator('canvas')).toHaveCount(4);
  await page.getByRole('button',{name:'All pre-contact',exact:true}).click();await expect(page.getByLabel('Window end',{exact:true})).toHaveValue('41.195');
  await page.getByRole('button',{name:'All disarmed',exact:true}).click();await expect(page.getByLabel('Window start',{exact:true})).toHaveValue('41.25');
  await page.getByRole('button',{name:'Landing gust',exact:true}).click();await page.getByRole('button',{name:'Next interval',exact:true}).click();await expect(page.getByTestId('response-cursor')).toHaveText('40.005 s');
  await page.getByLabel('Diagnostic flight',{exact:true}).selectOption('0');await expect(page.getByRole('img',{name:'Radial phase portrait',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Share response review',exact:true}).click();await page.reload();await expect(page.getByTestId('response-cursor')).toHaveText('40.005 s');await expect(page.getByLabel('Window end',{exact:true})).toHaveValue('42');
  for(const [button,name] of [['Export response JSON','stress-s401-response.json'],['Export interval CSV','stress-s401-response.csv']]){const pending=page.waitForEvent('download');await page.getByRole('button',{name:button,exact:true}).click();expect((await pending).suggestedFilename()).toBe(name);}
  await page.getByRole('button',{name:'Play four flights ½×',exact:true}).click();await expect(page.getByTestId('response-cursor')).not.toHaveText('40.005 s');await page.getByRole('button',{name:'Pause',exact:true}).click();expect(errors).toEqual([]);
});
test('nine-seed table uses common window and stale loads cannot replace selection',async({page})=>{
  await routeFixture(page,{delay:'regression-p0-s0.json'});await page.goto('/response.html');await expect(page.getByTestId('response-selected')).toContainText('401');
  await page.getByRole('button',{name:'regression · seed 0',exact:true}).click();await page.getByRole('button',{name:'additional · seed 907',exact:true}).click();await expect(page.getByTestId('response-selected')).toContainText('907');await page.waitForTimeout(800);await expect(page.getByTestId('response-selected')).toContainText('907');
  await page.getByRole('button',{name:'Compare nine seeds',exact:true}).click();await expect(page.getByRole('table',{name:'Seed response comparison'}).locator('tbody tr')).toHaveCount(9);await page.getByLabel('Sort seed comparison',{exact:true}).selectOption('interaction');
  await page.getByLabel('Window end',{exact:true}).fill('44');await expect(page.getByRole('table',{name:'Seed response comparison'})).toHaveCount(0);
  for(const width of [320,390]){
    await page.setViewportSize({width,height:844});
    await expect.poll(()=>page.evaluate(()=>({
      width:innerWidth,scroll:document.documentElement.scrollWidth,
      overflow:[...document.querySelectorAll('main > *, label, select, input')]
        .filter(e=>e.getBoundingClientRect().right>innerWidth+.5)
        .map(e=>e.tagName+':'+e.className),
    }))).toMatchObject({width,scroll:width,overflow:[]});
  }
});
test('incomplete and corrupt evidence keep missing results explicit',async({page})=>{
  await routeFixture(page,{incomplete:true});await page.goto('/response.html');await expect(page.getByRole('alert')).toContainText('not fully recorded');await expect(page.getByRole('button',{name:'Play four flights ½×',exact:true})).toBeDisabled();await expect(page.getByRole('button',{name:'All disarmed',exact:true})).toBeDisabled();
  await page.unrouteAll();await routeFixture(page,{corrupt:true});await page.goto('/response.html');await expect(page.getByRole('alert')).toContainText('integrity');await expect(page.getByRole('region',{name:'fixed-intact',exact:true})).toHaveCount(0);
});
test('renderer failure leaves interval diagnostics usable',async({page})=>{
  await page.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(name,...args){if(name==='webgl'||name==='webgl2')return null;return original.call(this,name,...args);};});
  await routeFixture(page);await page.goto('/response.html');await page.getByRole('button',{name:'Enable four-flight 3D'}).click();await expect(page.getByText('3D unavailable. Numeric diagnostics remain available.')).toHaveCount(4);await expect(page.getByRole('table',{name:'Four-flight window metrics'})).toBeVisible();
});
