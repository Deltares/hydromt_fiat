import requests
from shapely.geometry import Polygon
import logging
import geopandas as gpd

logger = logging.getLogger(__name__)


def nsi_post_request(url: str, polygon: Polygon) -> requests.models.Response:
    """Post request to the National Structure Inventory (NSI) database.

    API reference: https://www.hec.usace.army.mil/confluence/nsi/technicalreferences/latest/api-reference-guide#id-.APIReferenceGuidev2022-GET

    Parameters
    ----------
    url : str
        The root URL used to extract NSI structures from the NSI database, including
        the settings to get the structures as a Feature Collection (structures?fmt=fc).
    polygon : Polygon
        The polygon delineating the area for which the NSI structures should be
        downloaded.
    """
    data = polygon.__geo_interface__

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response
    # If the request fails (404) then print the error.
    except requests.exceptions.HTTPError as error:
        logger.error(error)
        return None


def get_assets_from_nsi(url: str, polygon: Polygon) -> gpd.GeoDataFrame:
    post_response = nsi_post_request(url, polygon)
    if post_response is None:
        return gpd.GeoDataFrame()
    source_data = gpd.read_file(post_response.text, driver="GeoJSON", engine="pyogrio")
    return source_data
