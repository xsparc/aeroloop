#pragma once
#include "frames.hpp"
#include <algorithm>
#include <cmath>

namespace aeroloop {
struct RateInput {
    Vector3 rate{}, setpoint{}, acceleration{};
    std::array<unsigned, 3> saturation{}; // bit 0: positive, bit 1: negative
    double dt{0.005};
    bool armed{true}, landed{false};
};
struct RateOutput { Vector3 effort{}, integral{}; bool valid{false}; };
struct Gains {
    Vector3 p{{0.6, 0.6, 0.6}}, i{{0.1, 0.1, 0.1}}, d{{0.005, 0.005, 0.005}};
    Vector3 ff{}, limit{{0.3, 0.3, 0.3}};
};

class RatePid3Axis {
public:
    explicit RatePid3Axis(const Gains& gains = Gains{}) noexcept : gains_(gains) {}
    void reset() noexcept { integral_ = {{0., 0., 0.}}; }
    RateOutput update(const RateInput& in) noexcept {
        RateOutput out;
        if (!std::isfinite(in.dt) || in.dt < 0.001 || in.dt > 0.02) { reset(); return out; }
        for (unsigned a = 0; a < 3; ++a) {
            if (!std::isfinite(in.rate[a]) || !std::isfinite(in.setpoint[a]) ||
                !std::isfinite(in.acceleration[a]) || in.saturation[a] > 3 ||
                !std::isfinite(gains_.p[a]) || !std::isfinite(gains_.i[a]) ||
                !std::isfinite(gains_.d[a]) || !std::isfinite(gains_.ff[a]) ||
                !std::isfinite(gains_.limit[a]) || gains_.p[a] < 0 || gains_.i[a] < 0 ||
                gains_.d[a] < 0 || gains_.ff[a] < 0 || gains_.limit[a] < 0) {
                reset(); return out;
            }
        }
        if (!in.armed) { reset(); out.valid = true; return out; }
        Vector3 next = integral_;
        for (unsigned a = 0; a < 3; ++a) {
            const double error = in.setpoint[a] - in.rate[a];
            const double base = gains_.p[a]*error - gains_.d[a]*in.acceleration[a] + gains_.ff[a]*in.setpoint[a];
            const double previous = base + integral_[a];
            const bool blocked = (error > 0 && ((in.saturation[a] & 1) || previous >= 1.)) ||
                                 (error < 0 && ((in.saturation[a] & 2) || previous <= -1.));
            const double candidate = in.landed ? 0. : integral_[a] + (blocked ? 0. : gains_.i[a]*error*in.dt);
            if (!std::isfinite(error) || !std::isfinite(base) || !std::isfinite(candidate)) { reset(); return RateOutput{}; }
            next[a] = std::max(-gains_.limit[a], std::min(gains_.limit[a], candidate));
            const double effort = base + next[a];
            if (!std::isfinite(effort)) { reset(); return RateOutput{}; }
            out.effort[a] = std::max(-1., std::min(1., effort));
        }
        integral_ = next;
        out.integral = next;
        out.valid = true;
        return out;
    }
private:
    Gains gains_;
    Vector3 integral_{};
};
}
