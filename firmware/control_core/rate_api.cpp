#include "rate_pid.hpp"
#include <new>
#ifdef _WIN32
#define AL_API __declspec(dllexport)
#else
#define AL_API __attribute__((visibility("default")))
#endif

extern "C" {
AL_API void* al_rate_create() noexcept { return new (std::nothrow) aeroloop::RatePid3Axis(); }
AL_API void al_rate_destroy(void* handle) noexcept { delete static_cast<aeroloop::RatePid3Axis*>(handle); }
AL_API int al_rate_step(void* handle, const double* rate, const double* setpoint,
                       const double* acceleration, const unsigned* saturation, double dt,
                       int armed, double* effort) noexcept {
    if (!handle || !rate || !setpoint || !acceleration || !saturation || !effort) return 0;
    aeroloop::RateInput input;
    input.dt = dt;
    input.armed = armed != 0;
    for (unsigned a = 0; a < 3; ++a) {
        input.rate[a] = rate[a]; input.setpoint[a] = setpoint[a];
        input.acceleration[a] = acceleration[a]; input.saturation[a] = saturation[a];
    }
    const auto result = static_cast<aeroloop::RatePid3Axis*>(handle)->update(input);
    for (unsigned a = 0; a < 3; ++a) effort[a] = result.effort[a];
    return result.valid ? 1 : 0;
}
}
