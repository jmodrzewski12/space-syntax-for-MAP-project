import asyncio
import datetime
import shutil
import sys
from os import chmod, getcwd, path
from time import time
from typing import NamedTuple
from urllib.request import urlretrieve

from config import (
    AnalysisConfiguration,
    AxialAnalysisConfiguration,
    SegmentAnalysisConfiguration,
)
from convert import mif_to_shp
from logger import default_logger

log = default_logger()


class DepthmapX(NamedTuple):
    executable: str


def depthmapx_factory() -> DepthmapX:
    executable = "depthmapXcli"
    if shutil.which(executable) is None:
        log.info("No depthmapXcli executable found, commencing download.")
        executable = path.join(getcwd(), "depthmapXcli")
        if sys.platform == "darwin":
            urlretrieve(
                "https://github.com/SpaceGroupUCL/depthmapX/releases/download/v0.8.0/depthmapXcli_macos",
                executable,
            )
        elif sys.platform == "linux":
            urlretrieve(
                "https://github.com/SpaceGroupUCL/depthmapX/releases/download/v0.8.0/depthmapXcli_linux64",
                executable,
            )
        else:
            raise NotImplementedError()
        chmod(executable, 0o775)

    return DepthmapX(executable)


async def run(cmd: str, description="Running command"):
    start = time()
    log.info(f"running: {cmd} because: {description}")
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    if proc.stdout:
        async for logLine in proc.stdout:
            log.info(f"{description} -> {logLine.decode().rstrip()!s}")

    if proc.stderr:
        async for logLine in proc.stderr:
            log.warn(f"{description} -> {logLine.decode().rstrip()!s}")

    log.info(
        f"[{cmd!r} exited with {proc.returncode}] and took {datetime.timedelta(seconds=(time() - start))}¬"
    )


async def axial(
    graph_file: str, depthmapx: DepthmapX, config: AxialAnalysisConfiguration
):
    base_file, _ = path.splitext(graph_file)
    axial_map_file = f"{base_file}-axial-map.graph"
    await run(
        f"{depthmapx.executable} -m MAPCONVERT -f {graph_file} -o {axial_map_file} -p -co axial -con axialMap",
        "Converting to axial map",
    )
    axial_analysis_file = f"{base_file}-axial-analysis.graph"
    await run(
        f"{depthmapx.executable} -m AXIAL -f {axial_map_file} -o {axial_analysis_file} -p -xa n -xac {','.join(str(radius) for radius in config.radii)}",
        "Performing axial analysis",
    )
    axial_shapefile_mif = f"{base_file}.axial.mif"
    await run(
        f"{depthmapx.executable} -m EXPORT -f {axial_analysis_file} -o {axial_shapefile_mif} -em shapegraph-map-mif",
        "Exporting axial analysis to mif",
    )
    return mif_to_shp(axial_shapefile_mif)


async def segment(
    graph_file: str, depthmapx: DepthmapX, config: SegmentAnalysisConfiguration
):
    base_file, _ = path.splitext(graph_file)
    log.info("This operation may take longer than 25 minutes to complete!!!")
    segment_map_file = f"{base_file}-segment-map.graph"
    await run(
        f"{depthmapx.executable} -m MAPCONVERT -f {graph_file} -o {segment_map_file} -p -co segment -con segmentMap",
        "Converting to segment map",
    )
    segment_analysis_file = f"{base_file}-segment-analysis.graph"
    await run(
        f"{depthmapx.executable} -m SEGMENT -f {segment_map_file} -o {segment_analysis_file} -p  -st {config.type.value} -srt {config.radius_type.value} -sic n -stb {config.tulip_bins} -sr {','.join(str(radius) for radius in config.radii)}",
        "Performing segment analysis",
    )
    segment_shapefile_mif = f"{base_file}.segment.mif"
    await run(
        f"{depthmapx.executable} -m EXPORT -f {segment_analysis_file} -o {segment_shapefile_mif} -em shapegraph-map-mif",
        "Exporting segment analysis to mif",
    )
    return mif_to_shp(segment_shapefile_mif)


async def analyse(dxfFile: str, analysis_config: AnalysisConfiguration):
    base_file, _ = path.splitext(dxfFile)
    graph_file = base_file + ".graph"
    depthmapx = depthmapx_factory()
    await run(
        f"{depthmapx.executable} -v ",
        "Using depthmapX cli version:",
    )

    await run(
        f"{depthmapx.executable} -m IMPORT -it drawing -f '{dxfFile}' -o '{graph_file}' ",
        "Transform dxf to shape file",
    )
    return await asyncio.gather(
        axial(graph_file, depthmapx, analysis_config.axial),
        segment(graph_file, depthmapx, analysis_config.segment),
    )
