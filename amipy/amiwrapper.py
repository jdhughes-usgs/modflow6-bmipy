import os
import numpy as np
from ctypes import *
from typing import Tuple

from .ami import Ami

BMI_SUCCESS = 0
BMI_FAILURE = 1


class AmiWrapper(Ami):
    """
    This is the AMI (BMI++) wrapper for marshalling python types into
    the kernels, and v.v.
    """

    def __init__(self, path):
        self.path = path
        self.dll = cdll.LoadLibrary(path)
        self.MAXSTRLEN = self.get_constant_int("MAXSTRLEN")

        self.working_directory = "."
        self.previous_directory = "."

    def get_constant_int(self, name: str) -> int:
        c_var = c_int.in_dll(self.dll, name)
        return c_var.value

    def set_int(self, name: str, value: int) -> None:
        c_var = c_int.in_dll(self.dll, name)
        c_var.value = value

    def initialize(self, config_file: str) -> None:
        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        check_result(self.dll.initialize(config_file), "initialize")
        os.chdir(self.previous_directory)

    def update(self) -> None:
        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        check_result(self.dll.update(), "update")
        os.chdir(self.previous_directory)

    def update_until(self, time: float) -> None:
        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        check_result(BMI_FAILURE, "update_until")
        os.chdir(self.previous_directory)

    def finalize(self) -> None:
        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        check_result(self.dll.finalize(), "finalize")
        os.chdir(self.previous_directory)

    def get_current_time(self) -> float:
        current_time = c_double(0.0)
        check_result(self.dll.get_current_time(byref(current_time)),
                     "get_current_time")
        return current_time.value

    def get_start_time(self) -> float:
        start_time = c_double(0.0)
        check_result(self.dll.get_start_time(byref(start_time)),
                     "get_start_time")
        return start_time.value

    def get_end_time(self) -> float:
        end_time = c_double(0.0)
        check_result(self.dll.get_end_time(byref(end_time)), "get_end_time")
        return end_time.value

    def get_time_step(self) -> float:
        dt = c_double(0.0)
        check_result(self.dll.get_time_step(byref(dt)), "get_time_step")
        return dt.value

    def get_component_name(self) -> str:
        raise NotImplementedError

    def get_input_item_count(self) -> int:
        raise NotImplementedError

    def get_output_item_count(self) -> int:
        raise NotImplementedError

    def get_input_var_names(self) -> Tuple[str]:
        raise NotImplementedError

    def get_output_var_names(self) -> Tuple[str]:
        raise NotImplementedError

    def get_var_grid(self, name: str) -> int:
        raise NotImplementedError

    def get_var_type(self, name: str) -> str:
        var_type = create_string_buffer(self.MAXSTRLEN)
        check_result(
            self.dll.get_var_type(c_char_p(name.encode()), byref(var_type)),
            "get_var_type", "for variable " + name)
        return var_type.value.decode()

    # strictly speaking not BMI...
    def get_var_shape(self, name: str) -> np.ndarray:
        rank = self.get_var_rank(name)
        array = np.zeros(rank, dtype=np.int32)
        check_result(self.dll.get_var_shape(c_char_p(name.encode()),
                                            c_void_p(array.ctypes.data)),
                     "get_var_shape", "for variable " + name)
        return array

    def get_var_rank(self, name: str) -> int:
        rank = c_int(0)
        check_result(
            self.dll.get_var_rank(c_char_p(name.encode()), byref(rank)),
            "get_var_rank", "for variable " + name)
        return rank.value

    def get_var_units(self, name: str) -> str:
        raise NotImplementedError

    def get_var_itemsize(self, name: str) -> int:
        item_size = c_int(0)
        check_result(self.dll.get_var_itemsize(c_char_p(name.encode()),
                                               byref(item_size)),
                     "get_var_itemsize", "for variable " + name)
        return item_size.value

    def get_var_nbytes(self, name: str) -> int:
        nbytes = c_int(0)
        check_result(
            self.dll.get_var_nbytes(c_char_p(name.encode()), byref(nbytes)),
            "get_var_nbytes", "for variable " + name)
        return nbytes.value

    def get_var_location(self, name: str) -> str:
        raise NotImplementedError

    def get_time_units(self) -> str:
        raise NotImplementedError

    def get_value(self, name: str, dest: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def get_value_ptr(self, name: str) -> np.ndarray:

        # first scalars
        rank = self.get_var_rank(name)
        if rank == 0:
            return self.get_value_ptr_scalar(name)

        vartype = self.get_var_type(name)
        shape_array = self.get_var_shape(name)

        # convert shape array to python tuple
        shape_tuple = tuple(np.trim_zeros(shape_array))
        ndim = len(shape_tuple)

        if vartype.lower().startswith("double"):
            arraytype = np.ctypeslib.ndpointer(dtype=np.float64, ndim=ndim,
                                               shape=shape_tuple, flags='F')
            values = arraytype()
            check_result(self.dll.get_value_ptr_double(c_char_p(name.encode()),
                                                       byref(values)),
                         "get_value_ptr", "for variable " + name)
            return values.contents
        elif vartype.lower().startswith("int"):
            arraytype = np.ctypeslib.ndpointer(dtype=np.int32, ndim=ndim,
                                               shape=shape_tuple, flags='F')
            values = arraytype()
            check_result(self.dll.get_value_ptr_int(c_char_p(name.encode()),
                                                    byref(values)),
                         "get_value_ptr", "for variable " + name)
            return values.contents

    def get_value_ptr_scalar(self, name: str) -> np.ndarray:
        vartype = self.get_var_type(name)
        if vartype.lower().startswith("double"):
            assert False
        elif vartype.lower().startswith("int"):
            arraytype = np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, shape=(1,),
                                               flags='F')
            values = arraytype()
            check_result(self.dll.get_value_ptr_int(c_char_p(name.encode()),
                                                    byref(values)),
                         "get_value_ptr", "for variable " + name)
            return values.contents

    def get_value_at_indices(self, name: str, dest: np.ndarray,
                             inds: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def set_value(self, name: str, values: np.ndarray) -> None:
        raise NotImplementedError

    def set_value_at_indices(self, name: str, inds: np.ndarray,
                             src: np.ndarray) -> None:
        raise NotImplementedError

    def get_grid_rank(self, grid: int) -> int:
        item_size = c_int(0)
        c_grid = c_int(grid)
        check_result(self.dll.get_grid_rank(byref(c_grid), byref(item_size)),
                     "get_grid_rank", "for id " + str(grid))
        return item_size.value

    def get_grid_size(self, grid: int) -> int:
        raise NotImplementedError

    def get_grid_type(self, grid: int) -> str:
        grid_type = create_string_buffer(self.MAXSTRLEN)
        c_grid = c_int(grid)
        check_result(
            self.dll.get_grid_type(byref(c_grid), byref(grid_type)),
            "get_grid_type", "for id " + str(grid))
        return grid_type.value.decode()

    def get_grid_shape(self, grid: int, shape: np.ndarray) -> np.ndarray:
        c_grid = c_int(grid)
        check_result(self.dll.get_grid_shape(byref(c_grid), c_void_p(shape.ctypes.data)),
                     "get_grid_shape", "for id " + str(id))
        return shape

    def get_grid_spacing(self, grid: int, spacing: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def get_grid_origin(self, grid: int, origin: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def get_grid_x(self, grid: int, x: np.ndarray) -> np.ndarray:
        c_grid = c_int(grid)
        check_result(self.dll.get_grid_x(byref(c_grid), c_void_p(x.ctypes.data)),
                     "get_grid_x", "for id " + str(id))
        return x

    def get_grid_y(self, grid: int, y: np.ndarray) -> np.ndarray:
        c_grid = c_int(grid)
        check_result(self.dll.get_grid_y(byref(c_grid), c_void_p(y.ctypes.data)),
                     "get_grid_y", "for id " + str(id))
        return y

    def get_grid_z(self, grid: int, z: np.ndarray) -> np.ndarray:
        c_grid = c_int(grid)
        check_result(self.dll.get_grid_z(byref(c_grid), c_void_p(z.ctypes.data)),
                     "get_grid_z", "for id " + str(id))
        return z

    def get_grid_node_count(self, grid: int) -> int:
        raise NotImplementedError

    def get_grid_edge_count(self, grid: int) -> int:
        raise NotImplementedError

    def get_grid_face_count(self, grid: int) -> int:
        raise NotImplementedError

    def get_grid_edge_nodes(self, grid: int,
                            edge_nodes: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def get_grid_face_edges(self, grid: int,
                            face_edges: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def get_grid_face_nodes(self, grid: int,
                            face_nodes: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def get_grid_nodes_per_face(self, grid: int,
                                nodes_per_face: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    # ===========================
    # here starts the AMI
    # ===========================
    def prepare_time_step(self, dt) -> None:
        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        dt = c_double(dt)
        check_result(self.dll.prepare_time_step(byref(dt)), "prepare_time_step")
        os.chdir(self.previous_directory)

    def do_time_step(self) -> None:
        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        check_result(self.dll.do_time_step(), "do_time_step")
        os.chdir(self.previous_directory)

    def finalize_time_step(self) -> None:
        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        check_result(self.dll.finalize_time_step(), "finalize_time_step")
        os.chdir(self.previous_directory)

    def get_subcomponent_count(self) -> int:
        count = c_int(0)
        check_result(self.dll.get_subcomponent_count(byref(count)),
                     "get_subcomponent_count")
        return count.value

    def prepare_solve(self, component_id) -> None:
        cid = c_int(component_id)

        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        check_result(self.dll.prepare_solve(byref(cid)),
                     "prepare_solve")
        os.chdir(self.previous_directory)

    def solve(self, component_id) -> bool:
        cid = c_int(component_id)
        has_converged = c_int(0)

        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        check_result(self.dll.solve(byref(cid), byref(has_converged)),
                     "solve")
        os.chdir(self.previous_directory)

        return has_converged.value == 1


    def finalize_solve(self, component_id) -> None:
        cid = c_int(component_id)

        self.previous_directory = os.getcwd()
        os.chdir(self.working_directory)
        check_result(self.dll.finalize_solve(byref(cid)),
                     "finalize_solve")
        os.chdir(self.previous_directory)


def check_result(result, function_name, detail=""):
    """
    Utility function to check the BMI status in the kernel
    TODO_MJR: rename this, is executes the bmi call (and also checks the status)
    """
    if result != BMI_SUCCESS:
        msg = "MODFLOW 6 BMI, exception in: " + function_name + \
              " (" + detail + ")"
        raise Exception(msg)