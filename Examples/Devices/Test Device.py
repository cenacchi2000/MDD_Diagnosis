"""
Test Device

>>> @device(name=device_name)
... class Activity:
>>> @parameter(type)
... def example_parameter(self):
>>> @example_parameter.setter
>>> @example_parameter.on_demand
"""

from math import sin
from time import time

PLUG_1 = 0
PLUG_2 = 1


# run and check in Devices for a "Test Device" device
@device(name="Test Device")
class Activity:
    @system.tick(fps=100)
    def on_tick(self):
        t = time()
        x = sin(t)

        self.set_readable_double(x)
        self.set_readable_float(x)
        self.set_readable_int(int(x * 10))
        self.set_readable_enum(PLUG_1 if x > 0 else PLUG_2)
        self.set_readable_bool(x > 0)
        self.set_readable_string("hello" if x > 0 else "world")

    ##########################################################################

    _readable_double = 0

    @parameter("double", name="Readable.Double", min_value=-1, max_value=1)
    def readable_double(self):
        return self._readable_double

    @readable_double.setter
    def set_readable_double(self, value):
        self._readable_double = value

    ##########################################################################

    _readable_float = 0

    @parameter("float", name="Readable.Float", min_value=-1, max_value=1)
    def readable_float(self):
        return self._readable_float

    @readable_float.setter
    def set_readable_float(self, value):
        self._readable_float = value

    ##########################################################################

    _readable_int = 0

    @parameter("int", name="Readable.Integer", min_value=-10, max_value=10)
    def readable_int(self):
        return self._readable_int

    @readable_int.setter
    def set_readable_int(self, value):
        self._readable_int = value

    ##########################################################################

    _readable_enum = 0

    @parameter("int", name="Readable.Enum", enum_values=["plug 1", "plug 2"])
    def readable_enum(self):
        return self._readable_enum

    @readable_enum.setter
    def set_readable_enum(self, value):
        self._readable_enum = value

    ##########################################################################

    _readable_bool = False

    @parameter("boolean", name="Readable.Boolean")
    def readable_bool(self):
        return self._readable_bool

    @readable_bool.setter
    def set_readable_bool(self, value):
        self._readable_bool = value

    ##########################################################################

    _readable_string = "hello"

    @parameter("string", name="Readable.String")
    def readable_string(self):
        return self._readable_string

    @readable_string.setter
    def set_readable_string(self, value):
        self._readable_string = value

    ##########################################################################

    _readable_ndim_array = [1, 2, 3]

    @parameter(
        "n_dimensional_array",
        name="Readable.NDimArray",
        dimensions=[{"name": "dim_1", "labels": ["A", "B", "C"], "count": 3}],
    )
    def readable_n_dim_array(self):
        return self._readable_ndim_array

    @readable_n_dim_array.setter
    def set_readable_n_dim_array(self, value):
        self._readable_ndim_array = value

    ##########################################################################
    ##########################################################################

    _writable_double = 0

    @parameter("double", name="Writable.Double", min_value=-1, max_value=1)
    def writable_double(self):
        return self._writable_double

    @writable_double.setter
    def set_writable_double(self, value):
        self._writable_double = value

    @writable_double.on_demand
    def on_writable_double_demand(self, value):
        self.set_writable_double(value)

    ##########################################################################

    _writable_float = 0

    @parameter("float", name="Writable.Float", min_value=-1, max_value=1)
    def writable_float(self):
        return self._writable_float

    @writable_float.setter
    def set_writable_float(self, value):
        self._writable_float = value

    @writable_float.on_demand
    def on_writable_float_demand(self, value):
        self.set_writable_float(value)

    ##########################################################################

    _writable_int = 0

    @parameter("int", name="Writable.Integer", min_value=-10, max_value=10)
    def writable_int(self):
        return self._writable_int

    @writable_int.setter
    def set_writable_int(self, value):
        self._writable_int = value

    @writable_int.on_demand
    def on_writable_int_demand(self, value):
        self.set_writable_int(value)

    ##########################################################################

    _writable_enum = 0

    @parameter("int", name="Writable.Enum", enum_values=["plug 1", "plug 2"])
    def writable_enum(self):
        return self._writable_enum

    @writable_enum.setter
    def set_writable_enum(self, value):
        self._writable_enum = value

    @writable_enum.on_demand
    def on_writable_enum_demand(self, value):
        self.set_writable_enum(value)

    ##########################################################################

    _writable_bool = False

    @parameter("boolean", name="Writable.Boolean")
    def writable_bool(self):
        return self._writable_bool

    @writable_bool.setter
    def set_writable_bool(self, value):
        self._writable_bool = value

    @writable_bool.on_demand
    def on_writable_bool_demand(self, value):
        self.set_writable_bool(value)

    ##########################################################################

    _writable_string = "hello"

    @parameter("string", name="Writable.String")
    def writable_string(self):
        return self._writable_string

    @writable_string.setter
    def set_writable_string(self, value):
        self._writable_string = value

    @writable_string.on_demand
    def on_writable_string_demand(self, value):
        self.set_writable_string(value)

    ##########################################################################

    _writable_ndim_array = [1, 2, 3]

    @parameter(
        "n_dimensional_array",
        name="Writable.NDimArray",
        dimensions=[{"name": "dim_1", "labels": ["A", "B", "C"], "count": 3}],
    )
    def writable_n_dim_array(self):
        return self._writable_ndim_array

    @writable_n_dim_array.setter
    def set_writable_n_dim_array(self, value):
        self._writable_ndim_array = value

    @writable_n_dim_array.on_demand
    def on_writable_n_dim_array_demand(self, value):
        self.set_writable_n_dim_array(value)
