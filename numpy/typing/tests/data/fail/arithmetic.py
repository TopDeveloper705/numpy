from typing import List, Any
import numpy as np

b_ = np.bool_()
dt = np.datetime64(0, "D")
td = np.timedelta64(0, "D")

AR_b: np.ndarray[Any, np.dtype[np.bool_]]
AR_f: np.ndarray[Any, np.dtype[np.float64]]
AR_c: np.ndarray[Any, np.dtype[np.complex128]]
AR_m: np.ndarray[Any, np.dtype[np.timedelta64]]
AR_M: np.ndarray[Any, np.dtype[np.datetime64]]

AR_LIKE_b: List[bool]
AR_LIKE_f: List[float]
AR_LIKE_c: List[complex]
AR_LIKE_m: List[np.timedelta64]
AR_LIKE_M: List[np.datetime64]

# NOTE: mypys `NoReturn` errors are, unfortunately, not that great
_1 = AR_b - AR_LIKE_b  # E: Need type annotation
_2 = AR_LIKE_b - AR_b  # E: Need type annotation

AR_f - AR_LIKE_m  # E: Unsupported operand types
AR_f - AR_LIKE_M  # E: Unsupported operand types
AR_c - AR_LIKE_m  # E: Unsupported operand types
AR_c - AR_LIKE_M  # E: Unsupported operand types

AR_m - AR_LIKE_f  # E: Unsupported operand types
AR_M - AR_LIKE_f  # E: Unsupported operand types
AR_m - AR_LIKE_c  # E: Unsupported operand types
AR_M - AR_LIKE_c  # E: Unsupported operand types

AR_m - AR_LIKE_M  # E: Unsupported operand types
AR_LIKE_m - AR_M  # E: Unsupported operand types

b_ - b_  # E: No overload variant

dt + dt  # E: Unsupported operand types
td - dt  # E: Unsupported operand types
td % 1  # E: Unsupported operand types
td / dt  # E: No overload
td % dt  # E: Unsupported operand types

-b_  # E: Unsupported operand type
+b_  # E: Unsupported operand type
