"""AeroLoop's camera-free, ideal body-wrench hover task for Isaac Lab 3."""
from __future__ import annotations

import torch
from isaaclab import cloner
from isaaclab.assets import RigidObject
from isaaclab.envs import DirectRLEnv, DirectRLEnvCfg
from isaaclab.scene import InteractiveSceneCfg
from isaaclab.sim import SimulationCfg
from isaaclab.utils import configclass
from isaaclab.utils.math import quat_from_euler_xyz
from isaaclab_physx.physics import PhysxCfg

from .isaac_runtime import DT, GRAVITY, body_config, set_inertia


@configclass
class HoverCfg(DirectRLEnvCfg):
    decimation = 4
    episode_length_s = 10.0
    action_space = 4
    observation_space = 13
    state_space = 0
    seed = 73
    sim = SimulationCfg(dt=DT, render_interval=4, gravity=(0.0, 0.0, -GRAVITY),
                        physics=PhysxCfg(), save_logs_to_file=False)
    scene = InteractiveSceneCfg(num_envs=32, env_spacing=8.0, replicate_physics=True,
                                clone_in_fabric=True)


class HoverEnv(DirectRLEnv):
    cfg: HoverCfg

    def __init__(self, cfg, **kwargs):
        super().__init__(cfg, **kwargs)
        self.actions = torch.zeros((self.num_envs, 4), device=self.device)
        self.forces = torch.zeros((self.num_envs, 1, 3), device=self.device)
        self.torques = torch.zeros_like(self.forces)
        self.moment_scale = torch.tensor([0.4, 0.4, 0.2], device=self.device)
        self.target = torch.tensor([0.0, 0.0, 1.5], device=self.device)

    def _setup_scene(self):
        self.vehicle = RigidObject(body_config("/World/envs/env_.*/Vehicle"))
        set_inertia(self.scene.stage, "/World/envs/env_0/Vehicle")
        positions = cloner.grid_transforms(self.num_envs, self.cfg.scene.env_spacing, device=self.device)[0]
        plan = cloner.clone_plan_from_env_0("/World/envs/env_0", "/World/envs/env_{}",
                                          self.num_envs, self.device, positions)
        cloner.replicate(plan, stage=self.scene.stage)
        self.scene.filter_collisions(global_prim_paths=[])
        self.scene.rigid_objects["vehicle"] = self.vehicle

    def _pre_physics_step(self, actions):
        if not torch.isfinite(actions).all():
            raise ValueError("Policy produced a non-finite action")
        self.actions = actions.clamp(-1.0, 1.0)
        self.forces[:, 0, 2] = GRAVITY * (1.0 + self.actions[:, 0])
        self.torques[:, 0, :] = self.actions[:, 1:] * self.moment_scale

    def _apply_action(self):
        self.vehicle.permanent_wrench_composer.set_forces_and_torques_index(
            forces=self.forces, torques=self.torques, is_global=False)

    def state(self):
        return (self.vehicle.data.root_pos_w.torch - self.scene.env_origins,
                self.vehicle.data.root_lin_vel_w.torch,
                self.vehicle.data.root_quat_w.torch,
                self.vehicle.data.root_ang_vel_b.torch)

    def _get_observations(self):
        pos, vel, quat, rates = self.state()
        # Lab 3 is xyzw; fix the double-cover sign for continuous local observations.
        quat = torch.where(quat[:, 3:4] < 0, -quat, quat)
        return {"policy": torch.cat((self.target - pos, vel, quat, rates), dim=-1)}

    def _get_dones(self):
        pos, vel, quat, rates = self.state()
        # Save pre-reset state: evaluation must never mistake an automatic reset for recovery.
        self.measured_state = torch.cat((pos, vel, quat, rates), dim=-1).clone()
        finite = torch.isfinite(self.measured_state).all(dim=-1)
        failed = (~finite | (pos[:, 2] < 0.2) | (pos[:, 2] > 3.5)
                  | (torch.linalg.vector_norm(pos[:, :2], dim=-1) > 3.0))
        return failed, self.episode_length_buf >= self.max_episode_length

    def _get_rewards(self):
        pos, vel, quat, rates = self.state()
        error_sq = ((pos - self.target)**2).sum(-1)
        upright = 1 - 2 * (quat[:, :2]**2).sum(-1)
        reward = (2.0 + 2.0 * torch.exp(-error_sq / 0.25) + upright
                  - 0.1 * (vel**2).sum(-1) - 0.02 * (rates**2).sum(-1)
                  - 0.01 * (self.actions**2).sum(-1)) * self.step_dt
        return torch.nan_to_num(reward, nan=-1.0) - self.reset_terminated.float()

    def _reset_idx(self, env_ids):
        if env_ids is None:
            env_ids = torch.arange(self.num_envs, device=self.device)
        super()._reset_idx(env_ids)
        count = len(env_ids)
        pose = self.vehicle.data.default_root_pose.torch[env_ids].clone()
        pose[:, :3] += self.scene.env_origins[env_ids]
        pose[:, :3] += torch.rand((count, 3), device=self.device) - 0.5
        angles = (torch.rand((count, 3), device=self.device) - 0.5) * 0.2
        pose[:, 3:] = quat_from_euler_xyz(*angles.unbind(-1))
        velocity = (torch.rand((count, 6), device=self.device) - 0.5) * 0.2
        self.vehicle.write_root_pose_to_sim_index(root_pose=pose, env_ids=env_ids)
        self.vehicle.write_root_velocity_to_sim_index(root_velocity=velocity, env_ids=env_ids)
        self.vehicle.reset(env_ids)
        if hasattr(self, "actions"):
            self.actions[env_ids] = 0


def runner_config(iterations=300):
    from isaaclab_rl.rsl_rl import RslRlMLPModelCfg, RslRlOnPolicyRunnerCfg, RslRlPpoAlgorithmCfg
    return RslRlOnPolicyRunnerCfg(
        seed=73, device="cuda:0", num_steps_per_env=64, max_iterations=iterations,
        save_interval=100, experiment_name="aeroloop_hover", logger="tensorboard",
        clip_actions=1.0, obs_groups={"actor": ["policy"], "critic": ["policy"]},
        actor=RslRlMLPModelCfg(hidden_dims=[128, 128], activation="elu", obs_normalization=True,
                             distribution_cfg=RslRlMLPModelCfg.GaussianDistributionCfg(init_std=0.5)),
        critic=RslRlMLPModelCfg(hidden_dims=[128, 128], activation="elu", obs_normalization=True),
        algorithm=RslRlPpoAlgorithmCfg(value_loss_coef=1.0, use_clipped_value_loss=True,
            clip_param=0.2, entropy_coef=0.001, num_learning_epochs=5, num_mini_batches=4,
            learning_rate=3e-4, schedule="adaptive", gamma=0.99, lam=0.95,
            desired_kl=0.01, max_grad_norm=1.0))
