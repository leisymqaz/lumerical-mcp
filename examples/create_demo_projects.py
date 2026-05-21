#!/usr/bin/env python3
"""Create small demo projects for FDTD, MODE, INTERCONNECT, and DEVICE."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_ROOT = r"D:\Program Files\Lumerical\v202"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "demo_projects"


PRODUCTS = {
    "fdtd": {
        "class": "FDTD",
        "exe": "fdtd-solutions.exe",
        "file": "demo_fdtd_si_nanoblock.fsp",
    },
    "mode": {
        "class": "MODE",
        "exe": "mode-solutions.exe",
        "file": "demo_mode_si_waveguide.lms",
    },
    "interconnect": {
        "class": "INTERCONNECT",
        "exe": "interconnect.exe",
        "file": "demo_interconnect_laser_waveguide.icp",
    },
    "device": {
        "class": "DEVICE",
        "exe": "device.exe",
        "file": "demo_device_charge_region.ldev",
    },
}


def import_lumapi(root: str):
    api_dir = os.path.join(root, "api", "python")
    bin_dir = os.path.join(root, "bin")
    sys.path.insert(0, api_dir)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(api_dir)
        os.add_dll_directory(bin_dir)
    import lumapi  # type: ignore

    return lumapi


def fdtd_script() -> str:
    return r'''
switchtolayout;
deleteall;
period=700e-9; si_h=220e-9; sub_h=600e-9;
addfdtd;
set("dimension","3D");
set("x span",period); set("y span",period);
set("z min",-sub_h-250e-9); set("z max",si_h+850e-9);
set("mesh accuracy",2);
set("x min bc","Periodic"); set("x max bc","Periodic");
set("y min bc","Periodic"); set("y max bc","Periodic");
set("z min bc","PML"); set("z max bc","PML");
addrect;
set("name","SiO2_substrate");
set("x span",period); set("y span",period);
set("z min",-sub_h); set("z max",0);
set("material","<Object defined dielectric>");
set("index",1.45);
addrect;
set("name","Si_nanoblock");
set("x span",280e-9); set("y span",180e-9);
set("z min",0); set("z max",si_h);
set("material","<Object defined dielectric>");
set("index",3.482875);
addplane;
set("name","normal_incidence_xpol");
set("injection axis","z"); set("direction","Backward");
set("x span",period); set("y span",period);
set("z",si_h+550e-9);
set("wavelength start",1200e-9); set("wavelength stop",1700e-9);
addpower;
set("name","T_bottom");
set("monitor type","2D Z-normal");
set("x span",period); set("y span",period);
set("z",-sub_h+120e-9);
addpower;
set("name","R_top");
set("monitor type","2D Z-normal");
set("x span",period); set("y span",period);
set("z",si_h+450e-9);
'''


def mode_script() -> str:
    return r'''
switchtolayout;
deleteall;
addrect;
set("name","SiO2_cladding");
set("x span",4e-6); set("y span",4e-6); set("z span",1e-6);
set("z",-0.5e-6);
set("material","<Object defined dielectric>");
set("index",1.45);
addrect;
set("name","Si_waveguide_core");
set("x span",4e-6); set("y span",500e-9); set("z span",220e-9);
set("z",110e-9);
set("material","<Object defined dielectric>");
set("index",3.482875);
addfde;
set("solver type","2D X normal");
set("x",0);
set("y span",3e-6);
set("z span",2e-6);
set("wavelength",1.55e-6);
'''


def interconnect_script() -> str:
    return r'''
deleteall;
addelement("CW Laser");
set("name","laser"); set("x position",-300); set("y position",0);
addelement("Straight Waveguide Unidirectional");
set("name","wg"); set("x position",0); set("y position",0);
addelement("Optical Spectrum Analyzer");
set("name","osa"); set("x position",300); set("y position",0);
connect("laser","output","wg","input");
connect("wg","output","osa","input");
'''


def device_script() -> str:
    return r'''
switchtolayout;
deleteall;
addrect;
set("name","Si_device_region");
set("x span",2e-6); set("y span",1e-6); set("z span",220e-9);
addrect;
set("name","Oxide_box");
set("x span",3e-6); set("y span",2e-6); set("z span",500e-9);
set("z",-360e-9);
addchargesolver;
addchargemesh;
set("name","local_charge_mesh");
'''


SCRIPTS = {
    "fdtd": fdtd_script,
    "mode": mode_script,
    "interconnect": interconnect_script,
    "device": device_script,
}


def create_project(lumapi, product: str, output_dir: Path, hidden: bool) -> Path:
    spec = PRODUCTS[product]
    cls = getattr(lumapi, spec["class"])
    session = cls(hide=hidden)
    try:
        session.eval(SCRIPTS[product]())
        output_path = output_dir / spec["file"]
        session.save(str(output_path))
        return output_path
    finally:
        session.close()


def launch_project(root: str, product: str, project_path: Path) -> subprocess.Popen:
    exe = Path(root) / "bin" / PRODUCTS[product]["exe"]
    return subprocess.Popen(
        [str(exe), str(project_path)],
        cwd=str(exe.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lumerical-root", default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--products", nargs="+", choices=list(PRODUCTS), default=list(PRODUCTS))
    parser.add_argument("--visible-create", action="store_true", help="Create projects through visible API sessions.")
    parser.add_argument("--launch", action="store_true", help="Launch saved projects in visible GUIs after creation.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    lumapi = import_lumapi(args.lumerical_root)

    created: list[Path] = []
    for product in args.products:
        path = create_project(lumapi, product, output_dir, hidden=not args.visible_create)
        created.append(path)
        print(f"{product}: {path} ({path.stat().st_size} bytes)")
        if args.launch:
            process = launch_project(args.lumerical_root, product, path)
            print(f"{product}: launched pid {process.pid}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
