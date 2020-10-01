from typing import List
import numpy as np

class SubClass(np.ndarray): ...

A: np.ndarray
B: SubClass
C: List[int]

reveal_type(np.asarray(A))  # E: ndarray
reveal_type(np.asarray(B))  # E: ndarray
reveal_type(np.asarray(C))  # E: ndarray

reveal_type(np.asanyarray(A))  # E: ndarray
reveal_type(np.asanyarray(B))  # E: SubClass
reveal_type(np.asanyarray(B, dtype=int))  # E: ndarray
reveal_type(np.asanyarray(C))  # E: ndarray

reveal_type(np.ascontiguousarray(A))  # E: ndarray
reveal_type(np.ascontiguousarray(B))  # E: ndarray
reveal_type(np.ascontiguousarray(C))  # E: ndarray

reveal_type(np.asfortranarray(A))  # E: ndarray
reveal_type(np.asfortranarray(B))  # E: ndarray
reveal_type(np.asfortranarray(C))  # E: ndarray

reveal_type(np.require(A))  # E: ndarray
reveal_type(np.require(B))  # E: SubClass
reveal_type(np.require(B, requirements=None))  # E: SubClass
reveal_type(np.require(B, dtype=int))  # E: ndarray
reveal_type(np.require(B, requirements="E"))  # E: ndarray
reveal_type(np.require(B, requirements=["ENSUREARRAY"]))  # E: ndarray
reveal_type(np.require(B, requirements={"F", "E"}))  # E: ndarray
reveal_type(np.require(B, requirements=["C", "OWNDATA"]))  # E: SubClass
reveal_type(np.require(B, requirements="W"))  # E: SubClass
reveal_type(np.require(B, requirements="A"))  # E: SubClass
reveal_type(np.require(C))  # E: ndarray

