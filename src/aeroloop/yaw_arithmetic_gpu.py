"""Optional CUDA arithmetic controls; not a PhysX solver or flight model."""
import warp as wp

# A pure-yaw quaternion is the unit complex number (w, z). The three modes
# differ only in scalar precision and trig evaluation; no measured bias is fitted.
@wp.func_native(r"""
if (mode == 2) {
    double w = 1.0, z = 0.0;
    const double angle = rate * dt / (2.0 * iterations);
    const double c = cos(angle), s = sin(angle);
    out[0] = wp::vec2d(w, z);
    for (int i = 1; i <= steps; ++i) {
        double dw = 1.0, dz = 0.0;
        for (int j = 0; j < iterations; ++j) {
            const double nw = c * dw - s * dz, nz = s * dw + c * dz;
            const double norm = sqrt(nw * nw + nz * nz);
            dw = nw / norm; dz = nz / norm;
        }
        const double nw = dw * w - dz * z, nz = dz * w + dw * z;
        const double norm = sqrt(nw * nw + nz * nz);
        w = nw / norm; z = nz / norm;
        out[i] = wp::vec2d(w, z);
    }
} else {
    float w = 1.0f, z = 0.0f;
    const float angle = fabsf((float)rate) * 0.5f * ((float)dt / iterations);
    float c, s;
    if (mode == 1) {
        __sincosf(angle, &s, &c);
    } else {
        s = sinf(angle); c = cosf(angle);
    }
    if (rate < 0.0) s = -s;
    out[0] = wp::vec2d(w, z);
    for (int i = 1; i <= steps; ++i) {
        float dw = 1.0f, dz = 0.0f;
        for (int j = 0; j < iterations; ++j) {
            const float nw = c * dw - s * dz, nz = s * dw + c * dz;
            const float norm = sqrtf(nw * nw + nz * nz);
            dw = nw / norm; dz = nz / norm;
        }
        const float nw = dw * w - dz * z, nz = dz * w + dw * z;
        const float norm = sqrtf(nw * nw + nz * nz);
        w = nw / norm; z = nz / norm;
        out[i] = wp::vec2d(w, z);
    }
}
""")
def recurrence(rate: wp.float64, dt: wp.float64, iterations: int, steps: int,
               mode: int, out: wp.array[wp.vec2d]):
    ...


@wp.kernel(enable_backward=False)
def integrate(rate: wp.float64, dt: wp.float64, iterations: int, steps: int,
              mode: int, out: wp.array[wp.vec2d]):
    recurrence(rate, dt, iterations, steps, mode, out)


def capture(rate, dt, iterations, mode):
    steps = round(.5 / dt)
    out = wp.zeros(steps+1, dtype=wp.vec2d, device="cuda:0")
    wp.launch(integrate, dim=1, inputs=[wp.float64(rate), wp.float64(dt), iterations,
              steps, mode, out], device="cuda:0")
    return out.numpy().tolist()
