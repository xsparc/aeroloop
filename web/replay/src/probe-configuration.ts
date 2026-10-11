// Fixed diagnostic configuration, shared with the Python capture contract.
export const PROBE_CONFIGURATION = {
  "physics_dt_s": 0.005,
  "control_dt_s": 0.005,
  "duration_s": 3.0,
  "seed": 301,
  "force_mode": "per-iteration",
  "solver": "TGS",
  "capacity": 64,
  "ground_kind": "stationary-kinematic",
  "model": {
    "mass": 1.0,
    "inertia": [
      0.02,
      0.02,
      0.04
    ],
    "gravity": 9.80665,
    "max_thrust": 20.0,
    "max_moment": [
      0.4,
      0.4,
      0.2
    ]
  },
  "contact": {
    "kind": "wind-contact-mission-v1",
    "collider_size_m": [
      0.4,
      0.4,
      0.1
    ],
    "ground_size_m": [
      20.0,
      20.0,
      0.1
    ],
    "ground_position_m": [
      0.0,
      0.0,
      -0.05
    ],
    "static_friction": 0.7,
    "dynamic_friction": 0.5,
    "restitution": 0.0,
    "contact_offset_m": 0.001,
    "rest_offset_m": 0.0,
    "contact_force_threshold_n": 0.1,
    "landing_clearance_m": 0.015,
    "landing_speed_m_s": 0.2,
    "contact_dwell_s": 0.05,
    "waypoints": [
      {
        "window_s": [
          7.0,
          10.0
        ],
        "position_m": [
          0.0,
          0.0,
          1.5
        ]
      },
      {
        "window_s": [
          15.0,
          18.0
        ],
        "position_m": [
          0.0,
          1.0,
          1.5
        ]
      },
      {
        "window_s": [
          23.0,
          26.0
        ],
        "position_m": [
          1.0,
          1.0,
          1.5
        ]
      },
      {
        "window_s": [
          31.0,
          34.0
        ],
        "position_m": [
          0.0,
          0.0,
          1.5
        ]
      }
    ]
  },
  "wind": {
    "kind": "bounded-temporal-ou-v1",
    "mean_m_s": [
      3.0,
      -1.0,
      0.0
    ],
    "sigma_m_s": [
      1.2,
      1.0,
      0.5
    ],
    "correlation_s": 0.6,
    "speed_limit_m_s": 12.0,
    "density_kg_m3": 1.225,
    "drag_area_m2": 0.06,
    "pressure_centre_m": [
      0.0,
      0.0,
      0.03
    ],
    "active_s": [
      0.0,
      55.0
    ],
    "ramp_s": 1.0,
    "gust_s": [
      40.0,
      42.0
    ],
    "gust_m_s": [
      3.0,
      0.0,
      0.0
    ]
  },
  "timing": "preceding-physics-interval",
  "measurement": "signed-diagnostic-only"
};
