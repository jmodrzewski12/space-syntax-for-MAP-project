import json
from osmnx import settings, config, graph, io, geocode_to_gdf
import uuid
import osmnx as ox
import geopandas as gpd
from typing import Any
from pathlib import Path
from logger import default_logger

utn = settings.useful_tags_node
oxna = settings.osm_xml_node_attrs
oxnt = settings.osm_xml_node_tags
utw = settings.useful_tags_way
oxwa = settings.osm_xml_way_attrs
oxwt = settings.osm_xml_way_tags
utn = list(set(utn + oxna + oxnt))
utw = list(set(utw + oxwa + oxwt))
config(all_oneway=True, useful_tags_node=utn, useful_tags_way=utw)

log = default_logger()



def download(place: str, operation_id=uuid.uuid4(), workdir="./downloads") -> str:
    log.info(f"Downloading map for: {place} ...")
    output_file = f"{workdir}/{operation_id}/osm.shp"
    io.save_graph_shapefile(
        download_drive_graph_from_place(place), filepath=output_file
    )
    return output_file


def download_drive_graph_from_place(place: str, root_workdir: str="/results/") -> Any:
    pathOsm=(f"{root_workdir}/{place}")
    Gosm = ox.graph_from_xml(pathOsm)
    return Gosm
    #return graph.graph_from_place(place, network_type="drive")


def download_administrative_geojson(place: str, root_workdir: str="/results/") -> Any:
    pathOsm=(f"{root_workdir}/{place}")
    Gosm=ox.graph_from_xml(pathOsm)
    gdf_nodes, gdf_edges=ox.graph_to_gdfs(Gosm)
    return json.loads(gdf_edges.to_json)

