"""Collect independent public/direct pose channels from actual PhysX yaw motion."""
from pathlib import Path
import time

from . import yaw_audit as audit
from .isaac_runtime import body_config, set_inertia, versions
from .physics import Model
from .simulation import encoded, sha256


def run(output: Path, args):
    import torch
    import warp as wp
    from isaaclab.app import launch_simulation
    from isaaclab_physx.physics import PhysxCfg

    output.mkdir(parents=True, exist_ok=False)
    started, dt, source = time.perf_counter(), args.physics_dt, audit.provenance()
    with launch_simulation(PhysxCfg(solver_type=1, enable_external_forces_every_iteration=True), args) as physics_cfg:
        import isaaclab.sim as sim_utils
        from isaaclab.assets import RigidObject
        sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(dt=dt, gravity=(0., 0., -Model().gravity),
            device=args.device, physics=physics_cfg, save_logs_to_file=False))
        cfg = body_config()
        cfg.spawn.rigid_props.enable_gyroscopic_forces = True
        cfg.spawn.rigid_props.solver_position_iteration_count = args.solver_iterations
        cfg.spawn.rigid_props.solver_velocity_iteration_count = 1
        body = RigidObject(cfg)
        set_inertia(sim.stage, "/World/Vehicle")
        sim.reset()
        if abs(sim.get_physics_dt()-dt) > 1e-12:
            raise RuntimeError("Simulator timestep differs from requested yaw timestep")
        force = torch.tensor([[[0., 0., Model().gravity]]], device=sim.device)
        moment = torch.zeros_like(force)
        rows, checksums = [], {}
        for case, (initial_rate, torque) in audit.CASES.items():
            pose = torch.tensor([[0., 0., 1.5, 0., 0., 0., 1.]], device=sim.device)
            velocity = torch.tensor([[0., 0., 0., 0., 0., initial_rate]], device=sim.device)
            body.write_root_pose_to_sim_index(root_pose=pose)
            body.write_root_velocity_to_sim_index(root_velocity=velocity)
            body.reset()
            moment.zero_(); moment[0, 0, 2] = torque
            body.permanent_wrench_composer.set_forces_and_torques_index(forces=force, torques=moment, is_global=False)
            body.update(dt)
            samples = []
            for step in range(round(audit.DURATION/dt)+1):
                # Host copies are completed before the next getter can refresh a shared GPU buffer.
                q = body.data.root_quat_w.torch[0].cpu().tolist()
                p = body.data.root_pos_w.torch[0].cpu().tolist()
                v = body.data.root_lin_vel_w.torch[0].cpu().tolist()
                rate = body.data.root_ang_vel_w.torch[0].cpu().tolist()
                direct = wp.to_torch(body.root_view.get_transforms())[0].cpu().tolist()
                direct_rate = wp.to_torch(body.root_view.get_velocities())[0].cpu().tolist()[3:]
                repeated = body.data.root_quat_w.torch[0].cpu().tolist()
                samples.append({"time_s": round(step*dt, 9), "position_m": p, "direct_position_m": direct[:3],
                    "velocity_m_s": v, "quaternion_wxyz": [q[3], *q[:3]],
                    "direct_quaternion_wxyz": [direct[6], *direct[3:6]],
                    "repeat_quaternion_wxyz": [repeated[3], *repeated[:3]],
                    "rates_rad_s": rate, "direct_rates_rad_s": direct_rate,
                    "force_flu_n": [0., 0., Model().gravity], "torque_flu_nm": [0., 0., torque]})
                if step == round(audit.DURATION/dt):
                    break
                body.write_data_to_sim(); sim.step(render=False); body.update(dt)
            content = encoded({"schema_version": 1, "kind": "measured_yaw_trace", "case": case, "dt_s": dt, "samples": samples})
            (output/(case+".json")).write_bytes(content)
            checksums[case+".json"] = sha256(content)
            metrics = audit.measurements(case, samples, dt)
            rows.append({"case": case, "metrics": metrics, "passed": audit.passes(metrics)})
        if source != audit.provenance():
            raise RuntimeError("Yaw source changed during measurement")
        result = {"schema_version": 1, "kind": audit.KIND, "backend": "isaacsim_physx", "dt_s": dt,
                  "configuration": audit.configuration(args.solver_iterations), "provenance": source, "versions": versions(),
                  "wall_time_s": time.perf_counter()-started, "checksums": checksums, "results": rows,
                  "passed": sum(r["passed"] for r in rows), "trials": len(rows)}
        (output/"result.json").write_bytes(encoded(result))
        audit.read_yaw(output)
        print(f"Yaw diagnostics at {1/dt:g} Hz / {args.solver_iterations} iterations: {result['passed']}/5 passed", flush=True)
