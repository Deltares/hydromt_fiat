from census import Census  # install in your environment using pip install Census
from us import states  # install in your environment using pip install us
from hydromt.data_catalog import DataCatalog
from hydromt.log import setuplog
import logging
import pandas as pd
import numpy as np
import geopandas as gpd
from urllib.request import urlopen
from io import BytesIO
from zipfile import ZipFile
from pathlib import Path



class EquityData:
    def __init__(self, data_catalog: DataCatalog = None, logger: logging.Logger = None):
        self.data_catalog = data_catalog
        self.census_key = Census
        self.download_codes = {}
        self.state_fips = 0
        self.pd_census_data = pd.DataFrame()
        self.codebook = pd.DataFrame()
        self.indicator_groups = {}
        self.processed_census_data = pd.DataFrame()

        self.pd_domain_scores_geo = pd.DataFrame()
        self.logger = setuplog("SVI", log_level=10)
        self.svi_data_shp = gpd.GeoDataFrame()
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


    def set_up_state_code(self, state_abbreviation: str):
        """download census data for a state

        Parameters
        ----------
        state_abbreviation : str
            Abbreviation of the state for which you want to set up the census data download
        """
        state = [
            state_abbreviation
        ]  # read in the state abbreviation as specified in the ini file
        state_obj = getattr(states, state[0])
        self.state_fips = state_obj.fips
        self.logger.info(f"The state abbreviation specified is: {state_abbreviation}")

    def variables_to_download(self):
        self.download_variables = ['B01003_001E', 'B19301_001E', 'NAME', 'GEO_ID']  # TODO: later make this a user input?

    def download_census_data(self, year_data):
        """download the census data
        it is possible to also make the county, tract and blockgroup flexible so that a user could specify exactly what to download
        But: bear in mind, with social vulneraiblity we compare areas against each other, so Ideally you would have a large enough dataset (for statistical and validity purposes)
        """
        download_census_codes = self.census_key.acs.state_county_blockgroup(
            fields=self.download_variables,
            state_fips=self.state_fips,
            county_fips="*",
            tract="*",
            blockgroup="*",
            year=year_data
        )
        self.pd_census_data = pd.DataFrame(download_census_codes)
        self.logger.info(
            "The equity data was succesfully downloaded from the Census website"
        )
        return self.pd_census_data

    def rename_census_data(self):
        """renaming the columns so that they have variable names instead of variable codes as their headers

        Parameters
        ----------
        from_name : str
            The name that you want to replace
        to_name : str
            The name to replace with
        """
        name_dict = {'B01003_001E': "TotalPopulationBG", 'B19301_001E': "PerCapitaIncomeBG"}  # TODO: Later make this a user input?
        self.pd_census_data = self.pd_census_data.rename(columns=name_dict)

    def match_geo_ID(self):
        """Matches GEO_IDs for the block groups"""
        self.pd_domain_scores_geo = self.pd_census_data.copy()
        self.pd_domain_scores_geo[
            "GEO_ID"
        ] = None  # Create a new column 'GEO_ID' with initial values set to None

        for index, value in enumerate(self.pd_domain_scores_geo["NAME"]):
            if value in self.pd_census_data["NAME"].values:
                matching_row = self.pd_census_data.loc[
                    self.pd_census_data["NAME"] == value
                ]
                geo_id = matching_row["GEO_ID"].values[
                    0
                ]  # Assuming there's only one matching row, extract the GEO_ID value
                self.pd_domain_scores_geo.at[
                    index, "GEO_ID"
                ] = geo_id  # Assign the GEO_ID value to the corresponding row in self.pd_domain_scores_geo
                self.pd_domain_scores_geo["GEOID_short"] = (
                    self.pd_domain_scores_geo["GEO_ID"].str.split("US").str[1]
                )

    def download_and_unzip(self, url, extract_to='.'):
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
            print(f"Error during download and unzip: {e}")

    def download_shp_geom(self, year_data, county):
        """Downloading the shapefiles from the government Tiger website

        Parameters
        ----------
        year_data : int
            The year for which you want to download the census data and the corresponding shapefiles (for geometry)
        county : int
            the county code in which your area of interest lies
        """
        # Download shapefile of blocks 
        if year_data == 2022:
            url = f"https://www2.census.gov/geo/tiger/TIGER_RD18/LAYER/FACES/tl_rd22_{self.state_fips}{county}_faces.zip"
            code = "20"
            self.logger.info("Downloading the county shapefile for 2022")
        elif year_data == 2021:
            url = f"https://www2.census.gov/geo/tiger/TIGER2021/FACES/tl_2021_{self.state_fips}{county}_faces.zip"
            code = "20"
            self.logger.info("Downloading the county shapefile for 2021")
        elif year_data == 2020:
            url = f"https://www2.census.gov/geo/tiger/TIGER2020PL/LAYER/FACES/tl_2020_{self.state_fips}{county}_faces.zip"
            code = "20"
            self.logger.info("Downloading the county shapefile for 2020")
        else:
            print("year not supported")
            return
        # Save shapefiles 
        fold_name = f'Shapefiles/{self.state_fips}{county}/{year_data}'
        self.download_and_unzip(url, fold_name)
        shapefiles = list(Path(fold_name).glob("*.shp"))
        if shapefiles:
            self.shp = gpd.read_file(shapefiles[0])
            self.logger.info("The shapefile was downloaded")
        else:
            print("No shapefile found in the directory.")
        
        # Dissolve shapefile based on block groups
        attrs = ["STATEFP", "COUNTYFP", "TRACTCE", "BLKGRPCE"]
        attrs = [attr + code for attr in attrs]

        self.block_groups = self.shp.dissolve(by=attrs, as_index=False)
        self.block_groups = self.block_groups[attrs + ["geometry"]]
        # block_groups["Census_Bg"] = block_groups['TRACTCE' + code].astype(str) + "-block" + block_groups['BLKGRPCE' + code].astype(str)
        self.block_groups["GEO_ID"] = "1500000US" + self.block_groups['STATEFP' + code].astype(str) + self.block_groups['COUNTYFP' + code].astype(str) + self.block_groups['TRACTCE' + code].astype(str) + self.block_groups['BLKGRPCE' + code].astype(str)


    def merge_equity_data_shp(self):
        """Merges the geometry data with the equity_data downloaded"""
        self.equity_data_shp = self.pd_domain_scores_geo.merge(self.block_groups[["GEO_ID", "geometry"]], on="GEO_ID", how="left")
        self.equity_data_shp = gpd.GeoDataFrame(self.equity_data_shp)

        #self.svi_data_shp.drop(columns=columns_to_drop, inplace=True)
        self.equity_data_shp = self.equity_data_shp.to_crs(epsg=4326)
        self.logger.info(
            "The geometry information was successfully added to the equity information"
        )