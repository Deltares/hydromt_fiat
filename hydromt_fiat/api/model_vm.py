from hydromt_fiat.api.data_types import OutputSettings, GlobalSettings


class ModelViewModel:
    def __init__(self):
        self.global_settings_model = GlobalSettings(crs=4326)
        self.output_model = OutputSettings(
            output_dir="output",
            output_csv_name="output.csv",
            output_vector_name="spatial.gpkg",
        )
