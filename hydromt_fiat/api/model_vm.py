from hydromt_fiat.api.data_types import ModelIni


class ModelViewModel:
    def __init__(self):
        self.config_model = ModelIni(
            site_name="", scenario_name="", output_dir="", crs=""
        )
