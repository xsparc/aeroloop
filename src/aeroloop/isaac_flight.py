"""Native flight control with four lagged rotors in actual Isaac Sim PhysX."""
from dataclasses import asdict
from pathlib import Path
import random
import time

from .controller import RateController
from .frames import normalize, rotate
from .physics import Model, State, desired_wrench
from .rotors import RotorModel
from .simulation import encoded, metrics, record, sha256


def flight(output: Path, launcher_args):
    import torch
    from isaaclab.app import launch_simulation
    from isaaclab_physx.physics import PhysxCfg
    from .isaac_runtime import body_config, set_inertia, versions

    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    dt, duration = .005, 35.
    model, rotors = Model(), RotorModel()
    results = []
    with launch_simulation(PhysxCfg(), launcher_args) as physics_cfg:
        # Kit must own USD before scene modules load on Windows.
        from isaaclab.assets import RigidObject
        import isaaclab.sim as sim_utils
        sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(
            dt=dt, gravity=(0., 0., -model.gravity), device=launcher_args.device,
            physics=physics_cfg, save_logs_to_file=False))
        vehicle = body_config()
        vehicle.spawn.rigid_props.enable_gyroscopic_forces = True
        body = RigidObject(vehicle)
        set_inertia(sim.stage, "/World/Vehicle")
        sim.reset()
        package_versions = versions()
        forces = torch.zeros((1, 1, 3), device=sim.device)
        torques = torch.zeros_like(forces)
        for scenario in launcher_args.scenarios:
            for seed in launcher_args.seeds:
                rng = random.Random(seed)
                initial = State(position=(rng.uniform(-.05, .05), rng.uniform(-.05, .05), 1.5+rng.uniform(-.05, .05)))
                pose = body.data.default_root_pose.torch.clone()
                pose[0, :3] = torch.tensor(initial.position, device=sim.device)
                pose[0, 3:] = torch.tensor((0., 0., 0., 1.), device=sim.device)
                body.write_root_pose_to_sim_index(root_pose=pose)
                body.write_root_velocity_to_sim_index(root_velocity=torch.zeros((1, 6), device=sim.device))
                body.reset()
                motors = (model.mass*model.gravity/4,)*4
                previous_rate, saturation = (0., 0., 0.), (0, 0, 0)
                samples, events = [], []
                status, reason = "passed", None
                with RateController() as controller:
                    library_hash = sha256(controller.path.read_bytes())
                    for step in range(round(duration/dt)+1):
                        t = round(step*dt, 9)
                        q = body.data.root_quat_w.torch[0].cpu().tolist()  # Lab 3: xyzw
                        rate = tuple(body.data.root_ang_vel_b.torch[0].cpu().tolist())
                        state = State(
                            tuple(body.data.root_pos_w.torch[0].cpu().tolist()),
                            tuple(body.data.root_lin_vel_w.torch[0].cpu().tolist()),
                            normalize((q[3], *q[:3])), rate,
                            tuple((v-old)/dt for v, old in zip(rate, previous_rate)) if step else (0., 0., 0.))
                        target = (0., 1., 1.5) if scenario == "position-step" and 10 <= t < 25 else (0., 0., 1.5)
                        external = (.5, 0., 0.) if scenario == "lateral-force-pulse" and 15 <= t < 15.5 else (0., 0., 0.)
                        if scenario == "position-step" and t in (10., 25.):
                            events.append({"time_s": t, "type": "target_step"})
                        if scenario == "lateral-force-pulse" and t in (15., 15.5):
                            events.append({"time_s": t, "type": "force_start" if t == 15. else "force_end"})
                        thrust_request, rate_request = desired_wrench(state, target, model)
                        effort = controller.step(rate, rate_request, state.acceleration, dt, saturation)
                        wanted = tuple(e*s for e, s in zip(effort, model.max_moment))
                        commands, saturation, scale = rotors.allocate(thrust_request, wanted)
                        saturation = tuple(flag | (1 if e >= 1 else 2 if e <= -1 else 0)
                                           for flag, e in zip(saturation, effort))
                        motors = rotors.advance(motors, commands, dt)
                        thrust, moment = rotors.wrench(motors)
                        samples.append({"time_s": t, "sequence": step, "position_m": state.position,
                            "velocity_m_s": state.velocity, "quaternion_wxyz": state.quaternion,
                            "target_m": target, "rates_rad_s": rate, "rate_setpoint_rad_s": rate_request,
                            "effort_normalized": effort, "thrust_n": thrust, "external_force_n": external,
                            "thrust_setpoint_n": thrust_request, "rotor_command_n": commands,
                            "rotor_thrust_n": motors, "moment_nm": moment, "allocation_scale": scale})
                        if state.position[2] <= 0 or sum(v*v for v in state.position) > 100**2:
                            status, reason = "failed", "model_bounds_exceeded"
                            break
                        if step == round(duration/dt):
                            break
                        inverse = (state.quaternion[0], *(-v for v in state.quaternion[1:]))
                        body_external = rotate(inverse, external)
                        forces[0, 0] = torch.tensor((body_external[0], body_external[1], thrust+body_external[2]), device=sim.device)
                        torques[0, 0] = torch.tensor(moment, device=sim.device)
                        body.permanent_wrench_composer.set_forces_and_torques_index(
                            forces=forces, torques=torques, is_global=False)
                        body.write_data_to_sim()
                        sim.step(render=False)
                        body.update(dt)
                        previous_rate = rate
                measured = metrics(samples, scenario)
                if status == "passed":
                    if scenario == "hover" and (measured["position_rmse_m"] is None or measured["position_rmse_m"] > .25):
                        status, reason = "failed", "hover_threshold"
                    if scenario == "position-step" and measured["step_response"]["settling_time_s"] is None:
                        status, reason = "failed", "step_did_not_settle"
                    if scenario == "lateral-force-pulse" and (measured["recovery_time_s"] is None or measured["recovery_time_s"] > 5):
                        status, reason = "failed", "recovery_threshold"
                config = {"model": asdict(model), "initial_state": asdict(initial), "dt_s": dt,
                    "duration_s": duration, "scenario": scenario, "seed": seed, "controller": "rate-pid-v1",
                    "position_kp": 2.5, "position_kd": 2.8, "attitude_kp": 5.,
                    "rate_gains": {"p": [.6]*3, "i": [.1]*3, "d": [.005]*3, "ff": [0.]*3, "integral_limit": [.3]*3},
                    "actuator": asdict(rotors), "simulator_versions": package_versions,
                    "physics_options": {"gyroscopic_forces": True}}
                run = record({"experiment": "isaac-quadrotor", "config": config, "samples": samples,
                    "events": events, "metrics": measured, "status": status, "failure_reason": reason,
                    "controller_binary_sha256": library_hash}, output)
                summary = {"run_id": run.name, "scenario": scenario, "seed": seed, "status": status, "metrics": measured}
                results.append(summary)
                print(encoded(summary).decode(), end="", flush=True)
        result = {"schema_version": 1, "kind": "isaac_quadrotor_flight", "backend": "isaacsim_physx",
                  "versions": package_versions, "results": results, "trials": len(results),
                  "passed": sum(r["status"] == "passed" for r in results), "wall_time_s": time.perf_counter()-started}
        (output / "result.json").write_bytes(encoded(result))
        print(f"Completed {len(results)} rotor-actuated PhysX trials.", flush=True)
