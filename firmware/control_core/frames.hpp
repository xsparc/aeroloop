#pragma once
#include <array>

namespace aeroloop {
using Vector3 = std::array<double, 3>;
inline Vector3 ned_to_enu(const Vector3& v) noexcept { return {{v[1], v[0], -v[2]}}; }
inline Vector3 frd_to_flu(const Vector3& v) noexcept { return {{v[0], -v[1], -v[2]}}; }
}
