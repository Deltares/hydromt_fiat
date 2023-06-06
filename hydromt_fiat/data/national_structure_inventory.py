import requests
from shapely.geometry import Polygon
import logging


def nsi_post_request(
    url: str, polygon: Polygon, logger: logging.Logger
) -> requests.models.Response:
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
