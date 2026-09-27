import {test,expect} from '@playwright/test';
import {routeFixture} from '../evaluation-fixture.mjs';

test('guided paired replay, gate matrix, playback and download',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await routeFixture(page);await page.goto('/evaluation.html');
  await expect(page.getByText('9 / 9 passed')).toBeVisible();
  await expect(page.getByRole('button',{name:'Seed 2, 800 Hz'})).toBeVisible();
  await page.getByRole('button',{name:'Enable paired 3D'}).click();
  await expect(page.locator('canvas')).toHaveCount(2);
  await page.getByRole('button',{name:'Landing gust'}).click();
  await expect(page.locator('output')).toHaveText('40.000 s');
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await expect(page.locator('output')).not.toHaveText('40.000 s');
  await page.getByRole('button',{name:'Pause',exact:true}).click();
  await page.getByRole('slider').focus();await page.keyboard.press('ArrowRight');
  await page.getByRole('button',{name:'Seed 2, 800 Hz'}).click();
  await expect(page.locator('output')).toHaveText('0.000 s');
  await expect(page.getByRole('combobox',{name:'Wind seed'})).toHaveValue('2');
  await expect(page.getByRole('combobox',{name:'Candidate physics'})).toHaveValue('0.00125');
  await expect(page.locator('canvas')).toHaveCount(0);
  await expect(page.getByRole('row').filter({hasText:'Position RMSE'}).last()).toContainText('0.5 m');
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download evaluation JSON'}).click();
  expect((await download).suggestedFilename()).toBe('flight-evaluation.json');
  expect(errors).toEqual([]);
});

test('failed and truncated trials remain visible without invented pair metrics',async({page})=>{
  await routeFixture(page,{incomplete:true});await page.goto('/evaluation.html');
  await expect(page.getByText('8 / 9 passed')).toBeVisible();
  await expect(page.getByText('Not accepted',{exact:true})).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('Incomplete recording');
  await expect(page.getByText('Incomplete pair; no sensitivity metrics are claimed.')).toBeVisible();
  await expect(page.getByRole('button',{name:'Candidate touchdown'})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Landing gust'})).toBeDisabled();
  await expect(page.getByRole('table').last()).toContainText('not measured');
});

test('corrupt recordings fail closed while retaining the verified study matrix',async({page})=>{
  await routeFixture(page,{corrupt:true});await page.goto('/evaluation.html');
  await expect(page.getByRole('alert')).toContainText('could not be verified');
  await expect(page.getByRole('slider')).toHaveCount(0);
  await expect(page.getByText('9 / 9 passed')).toBeVisible();
});

test('rapid selection, reduced motion, narrow layout and WebGL fallback',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:390,height:844});
  await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return kind.includes('webgl')?null:get.call(this,kind,...args);};});
  await routeFixture(page,{delay:'isaac-ground-mission-wind-0'});await page.goto('/evaluation.html');
  await page.getByRole('combobox',{name:'Wind seed'}).selectOption('1');
  await page.getByRole('combobox',{name:'Wind seed'}).selectOption('2');
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Enable paired 3D'}).click();
  await expect(page.getByText(/3D unavailable; recorded trajectory/)).toBeVisible();
  await page.getByRole('button',{name:'Landing gust'}).click();
  await expect(page.locator('output')).toHaveText('40.000 s');
  await page.getByText('Selected recording provenance').click();
  await expect(page.getByText(/Run isaac-ground-mission-wind-2-/)).toHaveCount(2);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test('playback pauses when the comparison leaves the viewport',async({page})=>{
  await routeFixture(page);await page.goto('/evaluation.html');
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await expect(page.getByRole('button',{name:'Pause',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Download evaluation JSON'}).scrollIntoViewIfNeeded();
  await expect(page.getByRole('button',{name:'Play',exact:true})).toHaveCount(1);
});


test('observation matrix replays paired truth and holds feedback snapshots between display points',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await routeFixture(page,{observed:true});await page.goto('/evaluation.html');
  await expect(page.getByText('12 / 12 passed')).toBeVisible();
  await expect(page.getByText('9 / 9 passed')).toBeVisible();
  await expect(page.getByRole('button',{name:'Seed 2, noise-delay',exact:true})).toBeVisible();
  await expect(page.getByRole('combobox',{name:'Candidate observations'})).toHaveValue('noise-delay');
  await page.getByRole('button',{name:'Enable paired 3D'}).click();await expect(page.locator('canvas')).toHaveCount(2);
  await page.getByRole('button',{name:'Landing gust'}).click();
  const right=page.getByRole('region',{name:'Candidate recording'});
  await expect(right.getByRole('region',{name:'Delivered feedback'})).toContainText('40 ms');
  await expect(right.getByRole('region',{name:'Delivered feedback'})).toContainText('39.960 s');
  await page.getByRole('slider').focus();await page.keyboard.press('ArrowRight');
  await expect(page.locator('output')).toHaveText('40.005 s');
  await expect(right.getByRole('region',{name:'Delivered feedback'})).toContainText('Snapshot 40.000 s');
  await page.getByRole('button',{name:'Seed 2, noise',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'Candidate observations'})).toHaveValue('noise');
  await expect(page.locator('output')).toHaveText('0.000 s');
  await expect(right.getByRole('region',{name:'Delivered feedback'})).toContainText('0 ms');
  await page.getByRole('button',{name:'Settled support'}).click();await expect(page.locator('output')).toHaveText('48.000 s');
  const download=page.waitForEvent('download');await page.getByRole('button',{name:'Download evaluation JSON'}).click();
  expect((await download).suggestedFilename()).toBe('observation-evaluation.json');
  expect(errors).toEqual([]);
});

test('incomplete observation flights and corrupt feedback do not claim successful playback',async({page})=>{
  await routeFixture(page,{observed:true,incomplete:true});await page.goto('/evaluation.html');
  await expect(page.getByText('11 / 12 passed')).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('Incomplete recording');
  await expect(page.getByRole('button',{name:'Landing gust'})).toBeDisabled();
  await routeFixture(page,{observed:true,corrupt:true});await page.reload();
  await expect(page.getByRole('alert')).toContainText('could not be verified');
  await expect(page.getByRole('slider')).toHaveCount(0);
});


test('observation replay retains narrow-screen controls, reduced motion and WebGL fallback',async({page})=>{
  await page.emulateMedia({reducedMotion:'reduce'});await page.setViewportSize({width:390,height:844});
  await page.addInitScript(()=>{const get=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(kind,...args){return kind.includes('webgl')?null:get.call(this,kind,...args);};});
  await routeFixture(page,{observed:true});await page.goto('/evaluation.html');
  await page.getByRole('combobox',{name:'Candidate observations'}).selectOption('delay');
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Enable paired 3D'}).click();
  await expect(page.getByText(/3D unavailable; recorded trajectory/)).toBeVisible();
  await page.getByRole('button',{name:'Landing gust'}).click();
  await expect(page.locator('output')).toHaveText('40.000 s');
  await expect(page.getByRole('region',{name:'Candidate recording'}).getByRole('region',{name:'Delivered feedback'})).toContainText('40 ms');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
