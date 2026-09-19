"""Optional Isaac Lab 3 / Isaac Sim PhysX bridge; import only in the Isaac environment.

Public recordings use wxyz. Isaac Lab 3 root poses use xyzw. The primitive body
has the same explicit mass/inertia as the CPU model and no vendor asset dependency.
"""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import time

GRAVITY = 9.80665
DT = 0.005
INERTIA = (0.02, 0.02, 0.04)


def versions():
    return {name: importlib.metadata.version(name)
            for name in ("isaacsim", "isaaclab", "torch")}


def body_config(prim_path="/World/Vehicle"):
    import isaaclab.sim as sim_utils
    from isaaclab.assets import RigidObjectCfg
    return RigidObjectCfg(
        prim_path=prim_path,
        spawn=sim_utils.CuboidCfg(
            size=(0.4, 0.4, 0.1),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(
                linear_damping=0.0, angular_damping=0.0,
                disable_gravity=False, sleep_threshold=0.0),
            mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
            collision_props=sim_utils.CollisionPropertiesCfg()),
        init_state=RigidObjectCfg.InitialStateCfg(pos=(0.0, 0.0, 1.5)),
    )


def set_inertia(stage, prim_path):
    from pxr import Gf, UsdPhysics
    mass = UsdPhysics.MassAPI.Apply(stage.GetPrimAtPath(prim_path))
    mass.CreateDiagonalInertiaAttr(Gf.Vec3f(*INERTIA))
    mass.CreateCenterOfMassAttr(Gf.Vec3f(0, 0, 0))
    mass.CreatePrincipalAxesAttr(Gf.Quatf(1, 0, 0, 0))


def smoke(output: Path, launcher_args):
    """Measure free fall, force equilibrium, and rotated body thrust on the GPU."""
    import torch
    from isaaclab.app import launch_simulation
    from isaaclab_physx.physics import PhysxCfg

    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    with launch_simulation(PhysxCfg(), launcher_args) as physics_cfg:
        from isaaclab.assets import RigidObject
        import isaaclab.sim as sim_utils
        sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(
            dt=DT, gravity=(0.0, 0.0, -GRAVITY), device=launcher_args.device,
            physics=physics_cfg, save_logs_to_file=False))
        body = RigidObject(body_config())
        set_inertia(sim.stage, "/World/Vehicle")
        sim.reset()
        torch.cuda.reset_peak_memory_stats()
        initial_pose = body.data.default_root_pose.torch.clone()
        initial_velocity = body.data.default_root_vel.torch.clone()
        results = []
        cases = (("free_fall", 0.0, 50, False),
                 ("force_equilibrium", GRAVITY, 200, False),
                 ("rotated_body_thrust", GRAVITY, 50, True))
        for name, thrust, steps, rotated in cases:
            pose = initial_pose.clone()
            if rotated:
                # +90 degrees around body X: body +Z points toward world -Y.
                pose[:, 3:] = torch.tensor([2**-0.5, 0, 0, 2**-0.5], device=sim.device)
            body.write_root_pose_to_sim_index(root_pose=pose)
            body.write_root_velocity_to_sim_index(root_velocity=initial_velocity)
            body.reset()
            forces = torch.zeros((1, 1, 3), device=sim.device)
            forces[..., 2] = thrust
            body.permanent_wrench_composer.set_forces_and_torques_index(
                forces=forces, torques=torch.zeros_like(forces), is_global=False)
            for _ in range(steps):
                body.write_data_to_sim()
                sim.step(render=False)
                body.update(DT)
            measured = body.data.root_pos_w.torch[0].cpu().tolist()
            duration = steps * DT
            fall = -0.5 * GRAVITY * duration**2
            expected = [0.0, fall if rotated else 0.0,
                        1.5 + (fall if rotated or thrust == 0 else 0.0)]
            error = sum((a-b)**2 for a, b in zip(measured, expected))**0.5
            # Permit the semi-implicit integration error at the fixed time step.
            tolerance = 0.02 if steps == 50 else 0.002
            results.append({"case": name, "duration_s": duration,
                            "position_enu_m": measured, "expected_enu_m": expected,
                            "error_m": error, "tolerance_m": tolerance,
                            "passed": error <= tolerance})
        result = {"schema_version": 1, "kind": "isaac_physics_smoke",
                  "backend": "isaacsim_physx", "device": "cuda:0",
                  "versions": versions(), "physics_dt_s": DT,
                  "mass_kg": 1.0, "inertia_kg_m2": list(INERTIA),
                  "gpu": torch.cuda.get_device_name(),
                  "torch_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                  "wall_time_s": time.perf_counter() - started,
                  "checks": results, "passed": all(r["passed"] for r in results)}
        (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps(result, allow_nan=False), flush=True)
        if not result["passed"]:
            raise RuntimeError("Isaac physics smoke failed; inspect result.json")
