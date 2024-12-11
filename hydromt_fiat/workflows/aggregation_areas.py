import geopandas as gpd
from typing import List, Union
from pathlib import Path
import pandas as pd
import numpy as np


def process_value(value):
    if isinstance(value, list):
        return value[0]
    else:
        return value


def spatial_joins(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[List[str], List[Path], List[gpd.GeoDataFrame]],
    attribute_names: List[str],
    label_names: List[str],
    new_composite_area: bool,
    keep_all: bool = True,
) -> gpd.GeoDataFrame:
    """Perform spatial joins between the exposure GeoDataFrame and aggregation areas.
    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        The GeoDataFrame representing the exposure data.
    areas : Union[List[str], List[Path], List[gpd.GeoDataFrame]]
        A list of aggregation areas. Each area can be specified as a file path (str or Path),
        or as a GeoDataFrame.
        The GeoDataFrame representing the exposure data.
    areas : Union[List[str], List[Path], List[gpd.GeoDataFrame]]
        A list of aggregation areas. Each area can be specified as a file path (str or Path),
        or as a GeoDataFrame.
    attribute_names : List[str]
        A list of attribute names to be joined from the aggregation areas.
    label_names : List[str]
        A list of label names to be assigned to the joined attributes in the exposure GeoDataFrame.
    new_composite_area : bool
        If a new composite area is added split it according to aggregation
    Returns
    -------
    gpd.GeoDataFrame
        The exposure GeoDataFrame with the joined attributes from the aggregation areas.

    Raises
    ------
    AssertionError
        If the specified attribute name is not found in the aggregation area.

    Notes
    -----
    - If the exposure GeoDataFrame and the aggregation area have different coordinate reference systems (CRS),
      the aggregation area will be reprojected to match the CRS of the exposure GeoDataFrame.
    - The function performs a spatial join using the 'intersects' predicate.
    - If duplicates exist in the joined data, the function aggregates the data by grouping on the 'object_id'
      column and creating a list of values for each attribute.
    - The function expects the order of the label names to match the order of the aggregation areas in the 'areas'
      parameter.

    """

    if isinstance(aggregation_area_fn, str) or isinstance(aggregation_area_fn, Path):
        aggregation_area_fn = [aggregation_area_fn]
        attribute_names = [attribute_names]
        label_names = [label_names]

    filtered_areas = []

    # Create column to assign new composite area ID and create copy of new composite area gdf
    if new_composite_area:
        exposure_gdf["ca_ID"] = range(0, len(exposure_gdf), 1)
        exposure_gdf_copy = exposure_gdf.copy()

    for area, attribute_name, label_name in zip(
        aggregation_area_fn, attribute_names, label_names
    ):
        if isinstance(area, str) or isinstance(area, Path):
            area_gdf = gpd.read_file(area)
        else:
            area_gdf = area
            area_gdf = area

        ## check the projection of both gdf and if not match, reproject
        if exposure_gdf.crs != area_gdf.crs:
            area_gdf = area_gdf.to_crs(exposure_gdf.crs)
        assert (
            attribute_name in area_gdf.columns
        ), f"Attribute {attribute_name} not found in {area}"

        # Keep only used column
        area_gdf = area_gdf[[attribute_name, "geometry"]].reset_index(drop=True)

        # If you overwrite the exposure_gdf with the joined data, you can append all
        # aggregation areas to the same exposure_gdf

        exposure_gdf = gpd.sjoin(
            exposure_gdf,
            area_gdf,
            predicate="intersects",
            how="left",
        )
        # If we want to keep only used area we filter based on the intersections else we provide the whole dataframe
        if not keep_all:
            inds = np.sort(exposure_gdf["index_right"].dropna().unique())
            # TODO instead of keeping the ones that are joined keep everything that overlaps with the region?
            filtered_areas.append(area_gdf.iloc[inds].reset_index(drop=True))
        else:
            filtered_areas.append(area_gdf)

        ##remove the index_right column
        if "index_right" in exposure_gdf.columns:
            del exposure_gdf["index_right"]

        # aggregate the data if duplicates exist
        aggregated = (
            exposure_gdf.groupby("object_id")[attribute_name].agg(list).reset_index()
        )
        exposure_gdf.drop_duplicates(subset="object_id", keep="first", inplace=True)

        # Check if new gdf was already created in previous loop
        try:
            new_exposure_aggregation
        except NameError:
            new_exposure_aggregation = None
        else:
            new_exposure_aggregation = new_exposure_aggregation

        # If new composite area, split into the aggregation zones
        if new_composite_area:
            new_exposure_aggregation, exposure_gdf = split_composite_area(
                exposure_gdf, area_gdf, attribute_name, new_exposure_aggregation
            )
        else:
            exposure_gdf.drop(columns=attribute_name, inplace=True)
            exposure_gdf = exposure_gdf.merge(aggregated, on="object_id")

            # Create a string from the list of values in the duplicated aggregation area
            # column
            exposure_gdf[attribute_name] = exposure_gdf[attribute_name].apply(
                process_value
            )

            ##remove the index_right column
            if "index_right" in exposure_gdf.columns:
                del exposure_gdf["index_right"]

        # Rename the 'aggregation_attribute' column to 'new_column_name'. Put in
        # Documentation that the order the user put the label name must be the order of the gdf
        exposure_gdf.rename(columns={attribute_name: label_name}, inplace=True)

    # If new composite area, split Maximum Potential Damages of new composite areas per aggregation
    if new_composite_area:
        # Filter out erroneous polygons by 0.001%
        total_area = exposure_gdf.geometry.area.sum()
        filter_percentage = 0.0001
        area_threshold = total_area * filter_percentage
        exposure_gdf = exposure_gdf[exposure_gdf.geometry.area >= area_threshold]

        # Create new object_ids
        init_Object_ID = exposure_gdf_copy.loc[0, "object_name"]
        init_Object_ID = int(init_Object_ID.split(": ", 1)[1])
        exposure_gdf.loc[0:, "object_id"] = np.arange(
            init_Object_ID, init_Object_ID + int(len(exposure_gdf)), 1
        ).tolist()
        # Create new object_names
        exposure_gdf["object_name"] = exposure_gdf["object_id"].apply(
            lambda x: f"New development area: {int(x)}"
        )

        # Split max potential damages into new composite areas
        exposure_max_potential_damage = exposure_gdf_copy[["ca_ID", "max_damage_structure", "max_damage_content"]].set_index("ca_ID")
        exposure_gdf = split_max_damage_new_composite_area(
            exposure_gdf,
            exposure_max_potential_damage,
        )

    return exposure_gdf, filtered_areas


def split_composite_area(
    exposure_gdf, aggregation_gdf, attribute_name, new_exposure_aggregation
):
    """Split the new composite areas into the aggregation zones

     Parameters
     ----------
     exposure_gdf : gpd.GeoDataFrame
         Exposure data (new composite areas) geodataframe
    aggregation_gdf:  gpd.GeoDataFrame
         Aggregation geodataframe
     attribute_name: str
        The column name of the aggregation layer in the aggregatio_gdf.
     new_exposure_aggregation: gpd.GeoDataFrame
         new exposure to begin splitting with in case multiple aggregation zones are used for splitting. New exposure startng point per loop.
    """
    if any(
        exposure_geometry.intersects(aggregation_geometry)
        for exposure_geometry in exposure_gdf.geometry
        for aggregation_geometry in aggregation_gdf.geometry
    ):
        # Split exposure_gdf by aggregation zone
        new_exposure_gdf = exposure_gdf.rename(columns={attribute_name: "pot"})
        res_intersection = new_exposure_gdf.overlay(
            aggregation_gdf[[attribute_name, "geometry"]], how="intersection"
        )
        res_intersection.drop("pot", axis=1, inplace=True)

        # Grab the area that falls in no zone
        exposure_outside_aggregation = new_exposure_gdf.overlay(
            res_intersection[["geometry"]], how="symmetric_difference"
        )
        exposure_outside_aggregation.drop("pot", axis=1, inplace=True)

        # Combine divided objects of new composite area with areas that fall in no zone
        exposure_gdf = pd.concat(
            [res_intersection, exposure_outside_aggregation], ignore_index=True
        )
        exposure_gdf.dropna(subset=["object_id"], inplace=True)

        # Explode Multipolygons
        exposure_gdf = exposure_gdf.explode().reset_index()
        idx_multiploygon = exposure_gdf[exposure_gdf["geometry"].area < 1e-10].index
        if not idx_multiploygon.empty:
            exposure_gdf.drop(idx_multiploygon, inplace=True)
        if "level_0" in exposure_gdf.columns or "level_1" in exposure_gdf.columns:
            if "level_0" in exposure_gdf.columns:
                exposure_gdf.drop(["level_0"], axis=1, inplace=True)
            if "level_1" in exposure_gdf.columns:
                exposure_gdf.drop(["level_1"], axis=1, inplace=True)

        # create new object_ids
        exposure_gdf["object_id"] = exposure_gdf["object_id"].astype(int)
        init_Object_ID = exposure_gdf.loc[0, "object_id"]
        exposure_gdf.loc[0:, "object_id"] = np.arange(
            init_Object_ID + 1, init_Object_ID + 1 + int(len(exposure_gdf)), 1
        ).tolist()

    # Create an empty GeoDataFrame and append the exposure data
    if new_exposure_aggregation is None:
        data = pd.DataFrame(columns=["geometry"])
        final_exposure = gpd.GeoDataFrame(data, geometry="geometry")
        new_exposure_aggregation = pd.concat(
            [final_exposure, exposure_gdf], ignore_index=True
        )
        exposure_gdf = new_exposure_aggregation
    else:
        new_exposure_aggregation = exposure_gdf

    # Remove the index_right column
    if "index_right" in exposure_gdf.columns:
        del exposure_gdf["index_right"]

    return new_exposure_aggregation, exposure_gdf


def split_max_damage_new_composite_area(
    exposure_gdf: gpd.GeoDataFrame,
    exposure_max_potential_damage: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """Split the max potential damages by area size

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        Exposure data to split the max potential damages.
    exposure_max_potential_damage: pd.DataFrame
        Max potential damage: Structure and Content of new composite area per polygon. In case of multiple polygons, multiple max potential damages
    """

    # Calculate area per new composite area ID
    area_by_id = (
        exposure_gdf.groupby("ca_ID")["geometry"]
        .apply(lambda x: x.area.sum())
        .reset_index()
    ).set_index("ca_ID")
    
    exposure_max_potential_damage = exposure_max_potential_damage.join(area_by_id)

    for index_ca, row_ca in exposure_max_potential_damage.iterrows():
        # Calculate relative Max Potential Damages for Structure and Content based on area
        splitted_exposure_gdf = exposure_gdf[exposure_gdf["ca_ID"]== index_ca]
        
        if len(splitted_exposure_gdf) > 1:
            for index, row in splitted_exposure_gdf.iterrows():
                rel_area = row.geometry.area / row_ca["geometry"]
                exposure_gdf.at[index, "max_damage_structure"] = rel_area * row_ca["max_damage_structure"]
                exposure_gdf.at[index, "max_damage_content"] = rel_area * row_ca["max_damage_content"]

    del exposure_gdf["ca_ID"]

    return exposure_gdf


def join_exposure_aggregation_areas(
    exposure_gdf: gpd.GeoDataFrame,
    aggregation_area_fn: Union[
        List[str], List[Path], List[gpd.GeoDataFrame], str, Path, gpd.GeoDataFrame
    ],
    attribute_names: Union[List[str], str],
    label_names: Union[List[str], str],
    new_composite_area: bool,
    keep_all: bool = True,
) -> gpd.GeoDataFrame:
    """Join aggregation area labels to the exposure data.

    Parameters
    ----------
    exposure_gdf : gpd.GeoDataFrame
        Exposure data to join the aggregation areas to as `label_names`.
    aggregation_area_fn : Union[List[str], List[Path], str, Path]
        Path(s) to the aggregation area(s).
    attribute_names : Union[List[str], str]
        Name of the attribute(s) to join.
    label_names : Union[List[str], str]
        Name of the label(s) to join.
    new_composite_area : bool
        Check whether aggregation is done for a new composite area.
    """

    exposure_gdf, areas_gdf = spatial_joins(
        exposure_gdf,
        aggregation_area_fn,
        attribute_names,
        label_names,
        keep_all,
        new_composite_area,
    )

    # Remove the geometry column from the exposure_gdf to return a dataframe
    exposure_geoms = exposure_gdf[["object_id", "geometry"]]

    del exposure_gdf["geometry"]

    return exposure_gdf, exposure_geoms, areas_gdf
