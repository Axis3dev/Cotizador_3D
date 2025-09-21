"""Geometry utilities for loading STL files and extracting measurements."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing assistance only
    import trimesh


@dataclass
class MeshInfo:
    """Summary of a triangular mesh loaded from an STL file."""

    file_path: Path
    file_name: str
    volume_mm3: float
    volume_cm3: float
    surface_area_mm2: float
    bbox_dimensions_mm: tuple[float, float, float]
    is_watertight: bool
    triangle_count: int

    @property
    def height_mm(self) -> float:
        """Return the model height (Z dimension) in millimetres."""
        return self.bbox_dimensions_mm[2]


def load_mesh(file_path: str) -> MeshInfo:
    """Load an STL mesh from ``file_path`` and compute useful metrics.

    Parameters
    ----------
    file_path:
        Path to a ``.stl`` file. Units are assumed to be millimetres as is
        common for desktop 3D printing workflows.

    Returns
    -------
    MeshInfo
        Dataclass with volumetric information and bounding box dimensions.
    """

    trimesh = import_module("trimesh")
    mesh = trimesh.load(file_path, force="mesh")

    if isinstance(mesh, list):
        # Some STL files contain multiple solids; merge them to a single mesh.
        mesh = trimesh.util.concatenate(mesh)

    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError("El archivo STL no pudo convertirse a una malla triangular única.")

    volume_mm3 = float(mesh.volume)
    volume_cm3 = volume_mm3 / 1000.0
    bbox = mesh.bounding_box.extents
    bbox_dimensions_mm = (float(bbox[0]), float(bbox[1]), float(bbox[2]))

    surface_area_mm2 = float(mesh.area)
    triangle_count = int(mesh.faces.shape[0])

    return MeshInfo(
        file_path=Path(file_path),
        file_name=Path(file_path).name,
        volume_mm3=volume_mm3,
        volume_cm3=volume_cm3,
        surface_area_mm2=surface_area_mm2,
        bbox_dimensions_mm=bbox_dimensions_mm,
        is_watertight=bool(mesh.is_watertight),
        triangle_count=triangle_count,
    )


__all__ = ["MeshInfo", "load_mesh"]
