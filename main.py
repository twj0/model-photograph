from __future__ import annotations

import argparse
import tempfile
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

import meshio
import pyvista as pv
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = SCRIPT_DIR / "config/config.yaml"
DEFAULT_MESH_PATH = SCRIPT_DIR / "mesh/0626-micro-channel-cooling-meshing.msh"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "fig"


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file) or {}
    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a mapping")
    return data


def resolve_path(value: Any, base_dir: Path) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def load_mesh(mesh_path: Path) -> pv.DataSet:
    try:
        return pv.read(mesh_path)
    except Exception:
        if mesh_path.suffix.lower() != ".msh":
            raise
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_vtk = Path(tmpdir) / "converted_mesh.vtu"
        mesh = meshio.read(mesh_path)
        mesh.write(tmp_vtk)
        return pv.read(tmp_vtk)


def create_plotter(render_config: dict[str, Any], *, off_screen: bool = True) -> pv.Plotter:
    kwargs: dict[str, Any] = {"off_screen": off_screen}
    window_size = render_config.get("window_size")
    if window_size:
        kwargs["window_size"] = window_size
    return pv.Plotter(**kwargs)


def apply_lighting_mode(plotter: pv.Plotter, lighting_mode: Any) -> None:
    if lighting_mode is None:
        return
    if isinstance(lighting_mode, bool):
        if lighting_mode:
            return
        plotter.renderer.remove_all_lights()
        return
    mode = str(lighting_mode).strip().lower()
    if mode in {"default", "on", "true"}:
        return
    if mode in {"light kit", "kit", "physically based", "physically_based"}:
        if hasattr(plotter, "enable_lightkit"):
            plotter.enable_lightkit()
        return
    if mode in {"off", "false", "none"}:
        plotter.renderer.remove_all_lights()
        return
    raise ValueError(f"Unsupported lighting mode: {lighting_mode}")


def configure_plotter(plotter: pv.Plotter, mesh: pv.DataSet, render_config: dict[str, Any]) -> None:
    background = render_config.get("background", {})
    bottom = background.get("bottom")
    top = background.get("top")
    if bottom and top:
        plotter.set_background(bottom, top=top)
    elif bottom:
        plotter.set_background(bottom)
    apply_lighting_mode(plotter, render_config.get("lighting_mode"))
    anti_aliasing = render_config.get("anti_aliasing")
    if anti_aliasing:
        plotter.enable_anti_aliasing(anti_aliasing)
    quality_cfg = render_config.get("quality", {})
    if quality_cfg.get("ssao"):
        try:
            plotter.enable_ssao()
        except Exception:
            pass
    if quality_cfg.get("depth_peeling"):
        try:
            plotter.enable_depth_peeling()
        except Exception:
            pass
    if quality_cfg.get("fxaa"):
        try:
            plotter.enable_fxaa()
        except Exception:
            pass
    # projection and EDL
    if isinstance(render_config.get("parallel_projection"), bool):
        try:
            plotter.enable_parallel_projection(render_config.get("parallel_projection"))
        except Exception:
            # fallback for older PyVista: set camera parallel projection flag
            try:
                plotter.camera.SetParallelProjection(bool(render_config.get("parallel_projection")))
            except Exception:
                pass
    if render_config.get("eye_dome_lighting"):
        # Enhance depth perception for surface meshes
        plotter.enable_eye_dome_lighting()
    lighting = render_config.get("lighting", {})
    for light_cfg in lighting.values():
        position = light_cfg.get("position")
        if position is None:
            continue
        light_kwargs: dict[str, Any] = {"position": tuple(position)}
        if "intensity" in light_cfg:
            light_kwargs["intensity"] = light_cfg["intensity"]
        if "color" in light_cfg:
            light_kwargs["color"] = light_cfg["color"]
        plotter.add_light(pv.Light(**light_kwargs))
    mesh_options = {
        "show_edges": True,
        "smooth_shading": True,
        "edge_color": "#666666",
        "line_width": 1.0,
    }
    mesh_options.update(render_config.get("mesh", {}))
    surface = mesh if isinstance(mesh, pv.PolyData) else mesh.extract_surface()
    plotter.add_mesh(surface, **mesh_options)
    surface_center = getattr(surface, "center", None)
    if isinstance(surface_center, (tuple, list)):
        surface_center_seq: Any = list(surface_center)
    else:
        surface_center_seq = surface_center
    camera_position = render_config.get("camera_position")
    if camera_position:
        processed_camera = camera_position
        if isinstance(camera_position, (list, tuple)):
            cam_list = list(camera_position)
            if len(cam_list) == 3:
                position, focal_point, view_up = cam_list
                if isinstance(focal_point, str) and surface_center_seq is not None:
                    if focal_point.lower() in {"center", "centre", "auto"}:
                        focal_point = surface_center_seq
                processed_camera = [position, focal_point, view_up]
        plotter.camera_position = processed_camera
    else:
        plotter.camera_position = "iso"
    if surface_center_seq is not None:
        try:
            plotter.set_focus(surface_center_seq)
        except AttributeError:
            try:
                plotter.camera.focal_point = surface_center_seq
            except AttributeError:
                pass
    camera_zoom = render_config.get("camera_zoom")
    if isinstance(camera_zoom, (int, float)) and camera_zoom > 0:
        plotter.camera.zoom(camera_zoom)
    # axes widget
    axes_cfg = render_config.get("axes")
    if axes_cfg is True or (isinstance(axes_cfg, dict) and axes_cfg.get("enabled")):
        plotter.show_axes()


def save_mesh_screenshot(mesh_path: Path, output_path: Path, render_config: dict[str, Any] | None = None) -> None:
    mesh = load_mesh(mesh_path)
    config = render_config or {}
    plotter = create_plotter(config, off_screen=True)
    configure_plotter(plotter, mesh, config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scale = config.get("image_scale", 1)
    try:
        scale = int(scale) if scale else 1
    except Exception:
        scale = 1
    transparent = bool(config.get("transparent_background", False))
    plotter.screenshot(str(output_path), transparent_background=transparent, scale=scale)
    plotter.close()


def apply_export_controls(
    plotter: pv.Plotter,
    mesh_path: Path,
    render_config: dict[str, Any] | None,
    app_config: dict[str, Any],
) -> None:
    export_cfg: dict[str, Any] = {}
    if render_config:
        export_cfg = render_config.get("export", {}) or {}
    timestamp_format = app_config.get("timestamp_format", "%Y%m%d-%H%M%S")

    def resolve_directory() -> Path:
        direct_value = export_cfg.get("output_path")
        if direct_value is not None:
            direct_path = resolve_path(direct_value, SCRIPT_DIR)
            if direct_path is not None:
                return direct_path
        directory_value = export_cfg.get("directory")
        directory = resolve_path(directory_value, SCRIPT_DIR) if directory_value else None
        if directory is None:
            config_directory = app_config.get("export_directory")
            directory = resolve_path(config_directory, SCRIPT_DIR) if config_directory else None
        if directory is None:
            directory = DEFAULT_OUTPUT_DIR
        return directory

    def resolve_output_path() -> Path:
        base_target = resolve_directory()
        suffix = export_cfg.get("suffix") or ".png"
        name_value = export_cfg.get("filename")
        if base_target.suffix:
            base_dir = base_target.parent
            candidate = Path(base_target.name)
        else:
            base_dir = base_target
            candidate = Path(name_value) if name_value else Path(f"{mesh_path.stem}{suffix}")
        if not candidate.suffix:
            candidate = candidate.with_suffix(suffix)
        timestamp = datetime.now().strftime(timestamp_format)
        final_path = base_dir / f"{candidate.stem}_{timestamp}{candidate.suffix}"
        final_path.parent.mkdir(parents=True, exist_ok=True)
        return final_path

    def export_scale_value() -> int:
        scale_value = export_cfg.get("image_scale")
        if scale_value is None and render_config:
            scale_value = render_config.get("image_scale")
        try:
            scale_int = int(scale_value) if scale_value else 1
        except Exception:
            scale_int = 1
        if scale_int < 1:
            scale_int = 1
        return scale_int

    def export_transparency() -> bool:
        transparent = export_cfg.get("transparent_background")
        if transparent is None and render_config:
            transparent = render_config.get("transparent_background", False)
        return bool(transparent)

    def export_callback() -> None:
        try:
            output_path = resolve_output_path()
            plotter.screenshot(
                str(output_path),
                scale=export_scale_value(),
                transparent_background=export_transparency(),
            )
            print(f"Saved mesh screenshot to: {output_path}")
        except Exception as exc:
            print(f"Failed to export screenshot: {exc}")

    try:
        plotter.image_scale = export_scale_value()
    except Exception:
        pass
    if hasattr(plotter, "add_text_button"):
        plotter.add_text_button("Export Image", export_callback)
    if hasattr(plotter, "add_key_event"):
        plotter.add_key_event("e", export_callback)


def launch_interactive_viewer(
    mesh_path: Path,
    render_config: dict[str, Any] | None = None,
    app_config: dict[str, Any] | None = None,
) -> None:
    mesh = load_mesh(mesh_path)
    config = render_config or {}
    plotter = create_plotter(config, off_screen=False)
    configure_plotter(plotter, mesh, config)
    apply_export_controls(plotter, mesh_path, render_config, app_config or {})
    title = config.get("window_title", f"Mesh Viewer - {mesh_path.name}")
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r"`auto_close` ignored",
            category=UserWarning,
            module="pyvista",
        )
        plotter.show(title=title, auto_close=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render mesh files to PNG screenshots.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to YAML configuration file.",
    )
    parser.add_argument(
        "--mesh",
        type=Path,
        help="Path to the mesh file (.msh, .stl, etc.).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional output image path (defaults to fig/<mesh-stem>.png).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch an interactive viewer instead of saving a screenshot.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(resolve_path(args.config, SCRIPT_DIR) or DEFAULT_CONFIG_PATH)
    mesh_source = args.mesh or config.get("mesh_path") or DEFAULT_MESH_PATH
    output_source = args.output or config.get("output_path")
    mesh_path = resolve_path(mesh_source, SCRIPT_DIR)
    if mesh_path is None or not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_source}")
    render_config = config.get("render", {})
    if args.interactive:
        launch_interactive_viewer(mesh_path, render_config, config)
        return
    default_output = DEFAULT_OUTPUT_DIR / f"{mesh_path.stem}.png"
    output_path = resolve_path(output_source, SCRIPT_DIR) if output_source else default_output
    timestamp = datetime.now().strftime(config.get("timestamp_format", "%Y%m%d-%H%M%S"))
    output_path = output_path.with_name(f"{output_path.stem}_{timestamp}{output_path.suffix}")
    save_mesh_screenshot(mesh_path, output_path, render_config)
    print(f"Saved mesh screenshot to: {output_path}")


if __name__ == "__main__":
    main()
