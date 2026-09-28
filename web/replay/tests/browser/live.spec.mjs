import {test, expect} from '@playwright/test';

// Deliberately synthetic protocol fixtures; actual GPU validation is separate.
const frame = (state='running',sequence=1000)=>({schema_version:1,state,seed:0,physics_dt_s:.0025,paced:true,
  elapsed_s:sequence*.005,lag_s:0,max_lag_s:0,late_steps:0,age_s:0,stale:false,
  sample:{time_s:sequence*.005,sequence,position_m:[0,0,1.5],velocity_m_s:[0,0,0],quaternion_wxyz:[1,0,0,0],
    target_m:[0,0,1.5],rates_rad_s:[0,0,0],rate_setpoint_rad_s:[0,0,0],effort_normalized:[0,0,0],
    rotor_thrust_n:[2.45,2.45,2.45,2.45],allocation_scale:1,wind_velocity_m_s:[1,0,0],external_force_n:[.1,0,0],
    mission_phase:'hover',contact_normal_force_n:[0,0,0],support_clearance_m:1.45}});

test('live monitor advances 3D and distinguishes stale, failed and verified states', async({page})=>{
  let data=frame();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/live',route=>route.fulfill({json:data}));
  await page.goto('/monitor.html');
  await expect(page.getByRole('status')).toHaveText('Live · provisional');
  await page.getByRole('button',{name:'Enable 3D'}).click();
  await expect(page.locator('canvas')).toHaveCount(1);
  const heading = await page.getByRole('heading',{name:'Flight test monitor'}).boundingBox();
  const canvas = await page.locator('canvas').boundingBox();
  expect(canvas.y).toBeGreaterThan(heading.y+heading.height);
  expect(canvas.width).toBeLessThan(700);
  data=frame('running',1200);data.sample.position_m=[.1,0,1.6];
  await expect(page.getByText('0.141 m',{exact:true})).toBeVisible();
  data={...data,age_s:2,stale:true};
  await expect(page.getByRole('status')).toContainText('Stale');
  data=frame('failed',1200);
  await expect(page.getByRole('status')).toContainText('Failed');
  data=frame('completed',1200);
  await expect(page.getByRole('status')).toHaveText('Completed · recording verified');
  await page.getByRole('button',{name:'Hide 3D'}).click();
  await expect(page.locator('canvas')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('live monitor rejects bad packets and reconnects without presenting them as live',async({page})=>{
  let data={state:'waiting'}, down=false;
  await page.route('**/api/live',route=>down?route.abort():route.fulfill({json:data}));
  await page.goto('/monitor.html');
  await expect(page.getByRole('status')).toContainText('Waiting');
  data=frame();
  await expect(page.getByRole('status')).toHaveText('Live · provisional');
  data={...data,private_path:'must not render'};
  await expect(page.getByRole('status')).toContainText('Disconnected');
  await expect(page.getByText('must not render')).toHaveCount(0);
  down=true;
  await expect(page.getByRole('status')).toContainText('Disconnected');
  down=false;data=frame('running',1100);
  await expect(page.getByRole('status')).toHaveText('Live · provisional');
});


test('observation profile shows delayed feedback while 3D and scores use truth',async({page})=>{
  const data=frame('running',1000);data.schema_version=2;data.physics_dt_s=.005;data.observation_profile='noise-delay';
  data.sample.observation={profile:'noise-delay',source_sequence:992,source_time_s:4.96,age_s:.04,position_m:[.03,0,1.5],velocity_m_s:[0,.02,0]};
  await page.route('**/api/live',route=>route.fulfill({json:data}));
  await page.goto('/monitor.html');
  const observations=page.getByRole('region',{name:'Controller observations'});
  await expect(observations).toContainText('noise-delay');
  await expect(observations).toContainText('40 ms');
  await expect(observations).toContainText('0.030 m');
  await expect(page.getByText('0.000 m',{exact:true})).toBeVisible();
  await page.getByRole('button',{name:'Enable 3D'}).click();
  await expect(page.locator('canvas')).toHaveCount(1);
  await expect(page.getByText('3D pose and tracking error use physics truth.')).toBeVisible();
});


test('capture outage and resumed sensing retain truth 3D and separate telemetry freshness',async({page})=>{
  const data=frame('running',8040);data.schema_version=3;data.physics_dt_s=.005;data.observation_profile='hold-dropout';
  data.sample.observation={profile:'hold-dropout',source_sequence:7996,source_time_s:39.98,age_s:.22,position_m:[.08,0,1.5],velocity_m_s:[0,0,0]};
  await page.route('**/api/live',route=>route.fulfill({json:data}));await page.goto('/monitor.html');
  const observations=page.getByRole('region',{name:'Controller observations'});
  await expect(observations).toContainText('Capture cadence: 50 Hz');
  await expect(observations).toContainText('Scheduled capture outage active');
  await expect(observations).toContainText('220 ms');
  await expect(page.getByRole('status')).toHaveText('Live · provisional');
  await page.getByRole('button',{name:'Enable 3D'}).click();await expect(page.locator('canvas')).toHaveCount(1);
  data.sample.sequence=8060;data.sample.time_s=40.3;
  data.sample.observation={...data.sample.observation,source_sequence:8060,source_time_s:40.3,age_s:0};
  await expect(observations).toContainText('Outside scheduled capture outages');
  await expect(observations).toContainText('40.300 s');
  await expect(observations).toContainText('Peak received observation age220 ms');
  data.age_s=2;data.stale=true;await expect(page.getByRole('status')).toContainText('Stale');
  data.schema_version=2;await expect(page.getByRole('status')).toContainText('Disconnected');
});
