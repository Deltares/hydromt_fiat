from census import Census  # install in your environment using pip install Census
from us import states  # install in your environment using pip install us
from hydromt.data_catalog import DataCatalog
from logging import Logger
import pandas as pd
import geopandas as gpd
from urllib.request import urlopen
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path
from typing import List
from itertools import zip_longest
import shutil
from hydromt_fiat.workflows.social_vulnerability_index import list_of_states


class EquityData:
    def __init__(self, data_catalog: DataCatalog, logger: Logger, save_folder: str):
        self.data_catalog = data_catalog
        self.save_folder = save_folder
        self.census_key = Census
        self.download_codes = {}
        self.state_fips = []
        self.pd_census_data = pd.DataFrame()
        self.codebook = pd.DataFrame()
        self.indicator_groups = {}
        self.processed_census_data = pd.DataFrame()

        self.pd_domain_scores_geo = pd.DataFrame()
        self.logger = logger
        self.equity_data_shp = gpd.GeoDataFrame()
        self.block_groups = gpd.GeoDataFrame()

    def set_up_census_key(self, census_key: str):
        """The Census key can be inputted in the ini file.
        This is a unique key that every user needs to specify to download census data

        Parameters
        ----------
        census_key : str
            The unique key a user gets from the census download website (an API token basically)
        """

        self.census_key = Census(census_key)
        self.logger.info(
            f"your census key {census_key} is used to download data from the Census website "
        )

    def set_up_state_code(self, state_abbreviation: List[str]):
        """download census data for a state

        Parameters
        ----------
        state_abbreviation : str
            Abbreviation of the state for which you want to set up the census data download
        """
        states_done = []
        for state in state_abbreviation:
            if state not in states_done:
                self.logger.info(
                    f"The states for which census data will be downloaded is: {list_of_states(inverted=False)[state]}"
                )
                state_obj = getattr(states, state)
                self.state_fips.append(state_obj.fips)
                states_done.append(state)

    def variables_to_download(self):
        self.download_variables = [
            "B01003_001E",
            "B19301_001E",
            "NAME",
            "GEO_ID",
        ]  # TODO: later make this a user input?

    def download_census_data(self, year_data):
        """download the census data
        it is possible to also make the county, tract and blockgroup flexible so that a user could specify exactly what to download
        """
        dfs = []
        for sf in self.state_fips:
            download_census_codes = self.census_key.acs5.state_county_blockgroup(
                fields=self.download_variables,
                state_fips=sf,
                county_fips="*",
                tract="*",
                blockgroup="*",
                year=year_data,
            )
            dfs.append(pd.DataFrame(download_census_codes))

        self.pd_census_data = pd.concat(dfs)
        self.logger.info(
            "The equity data was succesfully downloaded from the Census website"
        )

    def rename_census_data(self):
        """renaming the columns so that they have variable names instead of variable codes as their headers

        Parameters
        ----------
        from_name : str
            The name that you want to replace
        to_name : str
            The name to replace with
        """
        name_dict = {
            "B01003_001E": "TotalPopulationBG",
            "B19301_001E": "PerCapitaIncomeBG",
        }  # TODO: Later make this a user input?
        self.pd_census_data = self.pd_census_data.rename(columns=name_dict)

    def match_geo_ID(self):
        """Matches GEO_IDs for the block groups"""
        self.pd_domain_scores_geo = self.pd_census_data.copy()
        self.pd_domain_scores_geo["GEO_ID"] = (
            None  # Create a new column 'GEO_ID' with initial values set to None
        )

        for index, value in enumerate(self.pd_domain_scores_geo["NAME"]):
            if value in self.pd_census_data["NAME"].values:
                matching_row = self.pd_census_data.loc[
                    self.pd_census_data["NAME"] == value
                ]
                geo_id = matching_row["GEO_ID"].values[
                    0
                ]  # Assuming there's only one matching row, extract the GEO_ID value
                self.pd_domain_scores_geo.at[index, "GEO_ID"] = (
                    geo_id  # Assign the GEO_ID value to the corresponding row in self.pd_domain_scores_geo
                )
                self.pd_domain_scores_geo["GEOID_short"] = (
                    self.pd_domain_scores_geo["GEO_ID"].str.split("US").str[1]
                )

    def download_and_unzip(self, url, extract_to="."):
        """function to download the shapefile data from census tiger website

        Parameters
        ----------
        url : webpage
            URL to census website (TIGER) to download shapefiles for visualisation
        extract_to : str, optional
            _description_, by default '.'
        """

        try:
            http_response = urlopen(url)
            zipfile = ZipFile(BytesIO(http_response.read()))
            zipfile.extractall(path=extract_to)
        except Exception as e:
            self.logger.warning(f"Error during download and unzip: {e}")

    def download_shp_geom(self, year_data: int, counties: List[str]):
        """Downloading the shapefiles from the government Tiger website

        Parameters
        ----------
        year_data : int
            The year for which you want to download the census data and the corresponding shapefiles (for geometry)
        counties : List[str]
            A list of county codes in which your area of interest lies
        """
        block_groups_list = []
        for sf, county in zip_longest(
            self.state_fips, counties, fillvalue=self.state_fips[0]
        ):
            # Download shapefile of blocks
            if year_data == 2022:
                url = f"https://www2.census.gov/geo/tiger/TIGER_RD18/LAYER/FACES/tl_rd22_{sf}{county}_faces.zip"
            elif year_data == 2021:
                url = f"https://www2.census.gov/geo/tiger/TIGER2021/FACES/tl_2021_{sf}{county}_faces.zip"
            elif year_data == 2020:
                url = f"https://www2.census.gov/geo/tiger/TIGER2020PL/LAYER/FACES/tl_2020_{sf}{county}_faces.zip"
            else:
                self.logger.warning(
                    f"Year {year_data} not available from 'https://www2.census.gov/geo/tiger'"
                )
                return

            # Save shapefiles
            folder = (
                Path(self.save_folder) / "shapefiles" / (sf + county) / str(year_data)
            )
            self.logger.info(
                f"Downloading the county {str(sf + county)} shapefile for {str(year_data)}"
            )
            self.download_and_unzip(url, folder)
            shapefiles = list(Path(folder).glob("*.shp"))
            if shapefiles:
                shp = gpd.read_file(shapefiles[0])
                self.logger.info("The shapefile was downloaded")
            else:
                self.logger.warning(f"No county shapefile found in {folder}.")
                continue

            # Dissolve shapefile based on block groups
            code = "20"
            attrs = ["STATEFP", "COUNTYFP", "TRACTCE", "BLKGRPCE"]
            attrs = [attr + code for attr in attrs]

            block_groups_shp = shp.dissolve(by=attrs, as_index=False)
            block_groups_shp = block_groups_shp[attrs + ["geometry"]]
            block_groups_shp["GEO_ID"] = (
                "1500000US"
                + block_groups_shp["STATEFP" + code].astype(str)
                + block_groups_shp["COUNTYFP" + code].astype(str)
                + block_groups_shp["TRACTCE" + code].astype(str)
                + block_groups_shp["BLKGRPCE" + code].astype(str)
            )
            block_groups_shp["GEOID_short"] = (
                block_groups_shp["GEO_ID"].str.split("US").str[1]
            )
            block_groups_list.append(block_groups_shp)

        # TODO Save final file as geopackage
        self.block_groups = gpd.GeoDataFrame(pd.concat(block_groups_list)).reset_index(
            drop=True
        )

        # Create string from GEO_ID short
        for (
            index,
            row,
        ) in self.block_groups.iterrows():
            BG_string = f"BG: {row['GEOID_short']}"
            self.block_groups.at[index, "GEOID_short"] = BG_string

        # NOTE: the shapefile downloaded from the census tiger website is deleted here!!
        # Delete the shapefile, that is not used anymore
        shp_folder = Path(self.save_folder) / "shapefiles"
        try:
            shutil.rmtree(shp_folder)
        except Exception as e:
            self.logger.warning(f"Folder {shp_folder} cannot be removed: {e}")

    def merge_equity_data_shp(self):
        """Merges the geometry data with the equity_data downloaded"""
        self.equity_data_shp = self.pd_domain_scores_geo.merge(
            self.block_groups[["GEO_ID", "geometry"]], on="GEO_ID", how="left"
        )
        self.equity_data_shp = gpd.GeoDataFrame(self.equity_data_shp)

        # Delete the rows that do not have a geometry column
        self.equity_data_shp = self.equity_data_shp.loc[
            self.equity_data_shp["geometry"].notnull()
        ]

        self.equity_data_shp = self.equity_data_shp.to_crs(epsg=4326)
        self.logger.info(
            "The geometry information was successfully added to the equity information"
        )

    def get_block_groups(self):
        return self.block_groups[["GEOID_short", "geometry"]]

    def clean(self):
        """Removes unnecessary columns"""
        self.equity_data_shp = self.equity_data_shp[
            ["GEOID_short", "TotalPopulationBG", "PerCapitaIncomeBG"]
        ]
