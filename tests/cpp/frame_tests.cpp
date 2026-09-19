#include "frames.hpp"
#include <iostream>

int main() {
    using namespace aeroloop;
    const Vector3 sample{{1., 2., 3.}};
    if (ned_to_enu(sample) != Vector3{{2., 1., -3.}} ||
        ned_to_enu(ned_to_enu(sample)) != sample ||
        frd_to_flu(frd_to_flu(sample)) != sample) {
        std::cerr << "frame contract failed\n";
        return 1;
    }
    return 0;
}
