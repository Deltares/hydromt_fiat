def detect_delimiter(csvFile):
    """From stackoverflow
    https://stackoverflow.com/questions/16312104/can-i-import-a-csv-file-and-automatically-infer-the-delimiter
    """
    with open(csvFile, "r") as myCsvfile:
        header = myCsvfile.readline()
        if header.find(";") != -1:
            return ";"
        if header.find(",") != -1:
            return ","
    # default delimiter
    return ","


def find_utm_projection(bbox, crs="epsg:4326"):
    """Find the UTM projection for a bounding box.
    
    Parameters
    ----------
    bbox : list
        The bounding box in WGS84 coordinates.
    crs : str, optional
        The coordinate reference system of the bounding box, by default "epsg:4326".

    Returns
    -------
    str
        The UTM projection as an EPSG code.
    """
    ...


