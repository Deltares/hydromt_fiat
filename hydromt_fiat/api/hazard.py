from hydromt_fiat.api.data_types import HazardIni


class HazardViewModel:
    def __init__(self):
        self.hazard_model = HazardIni(hazard_map_fn="", hazard_type="")
