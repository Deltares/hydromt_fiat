from .data_types import (
    Category,
    DataCatalogEntry,
    ExposureVectorIni,
    ExtractionMethod,
    Units,
)


class ExposureViewModel:
    def __init__(self):
        self.exposure_model = ExposureVectorIni(
            asset_locations=" ",
            occupancy_type="",
            max_potential_damage=-999,
            ground_floor_height=-999,
            gfh_units=Units.feet,
            extraction_method=ExtractionMethod.centroid,
        )

    def create_interest_area(self, **kwargs):
        filepath = kwargs.get("filepath")
        # make calls to backend to deduce data_type, driver, crs

        DataCatalogEntry(
            path=filepath,
            data_type="",
            driver="",
            crs="",
            meta={"category": Category.exposure},
        )
        # create entry in datacatalog in database
        ...

    # def set_asset_location(self, **kwargs):
    #     location_source = kwargs("variable")
    #     # derive file meta info such as crs, data type and driver
    #     DataCatalogEntry(
    #         path=location_source,
    #         data_type="",
    #         driver="",
    #         crs="",
    #         meta={"category": Category.exposure},
    #     )

    #     # self.set_asset_loca
    #     ...

    def create_location_source(self, **kwargs):
        location_source: str = kwargs.get("variable", "NSI")
        fiat_key_maps: dict | None = kwargs.get("keys", None)

        if location_source == "NSI":
            # .erive file meta info such as crs, data type and driver
            # make backend calls to create translation file

            ...
        elif location_source == "file" and fiat_key_maps is not None:
            # maybe save fiat_key_maps file in database
            # make calls to backend to derive file meta info such as crs, data type and driver
            # make backend calls to create translation file with fiat_key_maps
            ...

        # save translation file in data base
        # create data catalog entry
        DataCatalogEntry(
            path=location_source,
            data_type="",
            driver="",
            crs="",
            translation_fn="",
            meta={"category": Category.exposure},
        )

        # write to data catalog

    def create_extraction_map(self, *args):
        # if no exceptions, then self.exposure_model.extraction_method = args[0]
        # else if
        # make backend call to api with arguments to set extraction method per object:
        # create first with default method. Then get uploaded or drawn area and merge with default methid
        # save file to database
        # change self.exposure_model.extraction_method to file
        ...
        # change self.exposure_model.extraction_method to file
        ...
        ...
