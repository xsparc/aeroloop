"""Explicit C ABI bridge: each simulation owns one native rate controller."""
import ctypes
import os
import sys
from pathlib import Path
from .contracts import ValidationError
from .frames import vector


def library_path():
    root = Path(__file__).resolve().parents[2] / "build"
    name = "aeroloop_rate.dll" if os.name == "nt" else "libaeroloop_rate.dylib" if sys.platform == "darwin" else "libaeroloop_rate.so"
    for path in (root / name, root / "Release" / name):
        if path.is_file():
            return path.resolve()
    raise ValidationError("native controller unavailable; build with CMake first")


class RateController:
    def __init__(self):
        self.path = library_path()
        self.lib = ctypes.CDLL(str(self.path))
        self.lib.al_rate_create.argtypes = []
        self.lib.al_rate_create.restype = ctypes.c_void_p
        self.lib.al_rate_destroy.argtypes = [ctypes.c_void_p]
        self.lib.al_rate_destroy.restype = None
        pointer = ctypes.POINTER(ctypes.c_double)
        self.lib.al_rate_step.argtypes = [ctypes.c_void_p, pointer, pointer, pointer,
                                         ctypes.POINTER(ctypes.c_uint), ctypes.c_double, ctypes.c_int, pointer]
        self.lib.al_rate_step.restype = ctypes.c_int
        self.handle = self.lib.al_rate_create()
        if not self.handle:
            raise ValidationError("cannot allocate controller state")

    def step(self, rate, setpoint, acceleration, dt, saturation=(0, 0, 0), armed=True):
        if not self.handle:
            raise ValidationError("controller is closed")
        if len(saturation) != 3 or any(type(v) is not int or v not in range(4) for v in saturation):
            raise ValidationError("invalid saturation feedback")
        array = ctypes.c_double * 3
        result = array()
        ok = self.lib.al_rate_step(self.handle, array(*vector(rate)), array(*vector(setpoint)),
                                   array(*vector(acceleration)), (ctypes.c_uint * 3)(*saturation), dt, int(armed), result)
        if not ok:
            raise ValidationError("native controller rejected input")
        return tuple(result)

    def close(self):
        if self.handle:
            self.lib.al_rate_destroy(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
