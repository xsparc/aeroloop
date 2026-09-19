#include "rate_pid.hpp"
#include <cstdlib>
#include <iostream>
#include <limits>

void require(bool ok, const char* message) {
    if (!ok) { std::cerr << message << '\n'; std::exit(1); }
}
int main() {
    using namespace aeroloop;
    RatePid3Axis pid;
    RateInput in;
    auto out = pid.update(in);
    require(out.valid && out.effort == Vector3{}, "zero error");
    for (unsigned a = 0; a < 3; ++a) {
        pid.reset(); in = RateInput{}; in.setpoint[a] = 0.5;
        require(pid.update(in).effort[a] > 0, "positive axis response");
        in.setpoint[a] = -0.5;
        require(pid.update(in).effort[a] < 0, "negative axis response");
    }
    in = RateInput{}; in.setpoint = {{0.5, 0.5, 0.5}};
    for (unsigned n = 0; n < 10000; ++n) out = pid.update(in);
    require(std::abs(out.integral[0] - 0.3) < 1e-9, "integral limit");
    in.armed = false;
    out = pid.update(in);
    require(out.valid && out.integral == Vector3{} && out.effort == Vector3{}, "disarm reset");
    in.armed = true; in.saturation = {{1, 1, 1}};
    require(pid.update(in).integral == Vector3{}, "positive saturation antiwindup");
    in.setpoint = {{-0.5, -0.5, -0.5}};
    require(pid.update(in).integral[0] < 0, "unwind during saturation");
    in.saturation = {{0, 0, 0}}; in.setpoint = {{0.5, 0.5, 0.5}};
    require(pid.update(in).valid, "saturation release");
    pid.reset(); in = RateInput{}; in.acceleration = {{1, 1, 1}};
    require(pid.update(in).effort[0] < 0, "derivative on measurement");
    for (double dt : {0., 0.0009, 0.021, std::numeric_limits<double>::infinity()}) {
        in.dt = dt; require(!pid.update(in).valid, "invalid dt rejected");
    }
    for (double dt : {0.001, 0.02}) { in.dt = dt; require(pid.update(in).valid, "dt bounds accepted"); }
    in.rate[1] = std::numeric_limits<double>::quiet_NaN();
    require(!pid.update(in).valid, "nan rejected");
    in = RateInput{}; in.setpoint[0] = std::numeric_limits<double>::max();
    in.rate[0] = -std::numeric_limits<double>::max();
    require(!pid.update(in).valid, "overflow rejected");
    Gains bad; bad.i[0] = -1;
    require(!RatePid3Axis(bad).update(RateInput{}).valid, "invalid gains rejected");
    return 0;
}
