"""Measure isolated force, actuator and contact responses in Isaac PhysX."""
from pathlib import Path
import time

from . import physics_audit as audit
from .frames import normalize, rotate
from .isaac_runtime import body_config, set_inertia, versions
from .physics import Model, State
from .simulation import encoded, sha256


def run(output: Path, args):
    import torch
    from isaaclab.app import launch_simulation
    from isaaclab_physx.physics import PhysxCfg

    output.mkdir(parents=True, exist_ok=False)
    started, dt = time.perf_counter(), args.physics_dt
    source = audit.provenance()
    substep_forces = args.force_mode == "per-iteration"
    with launch_simulation(PhysxCfg(solver_type=1, enable_external_forces_every_iteration=substep_forces), args) as physics_cfg:
        import isaaclab.sim as sim_utils
        from isaaclab.assets import RigidObject
        from isaaclab.sensors import ContactSensor, ContactSensorCfg
        sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(
            dt=dt, gravity=(0., 0., -Model().gravity), device=args.device,
            physics=physics_cfg, save_logs_to_file=False))
        cfg = audit.configuration()["contact"]
        material = sim_utils.RigidBodyMaterialCfg(**{k: cfg[k] for k in ("static_friction", "dynamic_friction", "restitution")})
        collision = sim_utils.CollisionPropertiesCfg(contact_offset=cfg["contact_offset_m"], rest_offset=cfg["rest_offset_m"])
        vehicle = body_config()
        vehicle.spawn.rigid_props.enable_gyroscopic_forces = True
        vehicle.spawn.rigid_props.solver_position_iteration_count = 4
        vehicle.spawn.rigid_props.solver_velocity_iteration_count = 1
        vehicle.spawn.collision_props = collision
        vehicle.spawn.physics_material = material
        vehicle.spawn.activate_contact_sensors = True
        ground = sim_utils.CuboidCfg(size=tuple(cfg["ground_size_m"]), collision_props=collision, physics_material=material)
        ground.func("/World/Ground", ground, translation=tuple(cfg["ground_position_m"]))
        body = RigidObject(vehicle)
        sensor = ContactSensor(ContactSensorCfg(prim_path="/World/Vehicle", update_period=0., history_length=1, debug_vis=False))
        set_inertia(sim.stage, "/World/Vehicle")
        sim.reset()
        if abs(sim.get_physics_dt()-dt) > 1e-12:
            raise RuntimeError("Simulator timestep differs from requested physics timestep")
        force_tensor = torch.zeros((1, 1, 3), device=sim.device)
        torque_tensor = torch.zeros_like(force_tensor)
        rows, checksums = [], {}
        for case, duration in audit.CASES.items():
            initial = audit.initial_state(case)
            pose = body.data.default_root_pose.torch.clone()
            pose[0, :3] = torch.tensor(initial.position, device=sim.device)
            pose[0, 3:] = torch.tensor((*initial.quaternion[1:], initial.quaternion[0]), device=sim.device)
            velocity = torch.tensor([(*initial.velocity, *initial.rates)], device=sim.device)
            body.write_root_pose_to_sim_index(root_pose=pose)
            body.write_root_velocity_to_sim_index(root_velocity=velocity)
            body.reset(); sensor.reset()
            force_tensor.zero_(); torque_tensor.zero_()
            body.permanent_wrench_composer.set_forces_and_torques_index(forces=force_tensor, torques=torque_tensor, is_global=False)
            body.update(dt)
            motors, samples = (0.,)*4, []
            for step in range(round(duration/dt)+1):
                q = body.data.root_quat_w.torch[0].cpu().tolist()
                state = State(tuple(body.data.root_pos_w.torch[0].cpu().tolist()),
                              tuple(body.data.root_lin_vel_w.torch[0].cpu().tolist()), normalize((q[3], *q[:3])),
                              tuple(body.data.root_ang_vel_b.torch[0].cpu().tolist()))
                normal = tuple(sensor.data.net_normal_forces_w.torch[0, 0].cpu().tolist()) if step else (0.,)*3
                force, torque, motors = audit.inputs(case, state, motors, dt)
                samples.append({"time_s": round(step*dt, 9), "position_m": state.position, "velocity_m_s": state.velocity,
                                "quaternion_wxyz": state.quaternion, "rates_rad_s": state.rates, "force_enu_n": force,
                                "torque_flu_nm": torque, "rotor_thrust_n": motors, "contact_normal_force_n": normal})
                if step == round(duration/dt): break
                inverse = (state.quaternion[0], *(-v for v in state.quaternion[1:]))
                force_tensor[0, 0] = torch.tensor(rotate(inverse, force), device=sim.device)
                torque_tensor[0, 0] = torch.tensor(torque, device=sim.device)
                body.permanent_wrench_composer.set_forces_and_torques_index(forces=force_tensor, torques=torque_tensor, is_global=False)
                body.write_data_to_sim(); sim.step(render=False); body.update(dt)
                sensor.update(dt, force_recompute=True)
            data = encoded({"schema_version": 1, "kind": "measured_physics_trace", "case": case, "dt_s": dt, "samples": samples})
            (output/(case+".json")).write_bytes(data)
            checksums[case+".json"] = sha256(data)
            m = audit.measurements(case, samples, dt)
            rows.append({"case": case, "metrics": m, "passed": audit.passes(case, m, dt)})
        if source != audit.provenance():
            raise RuntimeError("Physics source changed during measurement")
        result = {"schema_version": 1, "kind": audit.KIND, "backend": "isaacsim_physx", "dt_s": dt,
                  "configuration": audit.configuration(substep_forces=substep_forces), "provenance": source, "versions": versions(),
                  "wall_time_s": time.perf_counter()-started, "checksums": checksums, "results": rows,
                  "passed": sum(row["passed"] for row in rows), "trials": len(rows)}
        (output/"result.json").write_bytes(encoded(result))
        audit.read_physics(output)
        print(f"Physics accuracy at {1/dt:g} Hz: {result['passed']}/{result['trials']} cases passed", flush=True)
