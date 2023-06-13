import time

from hydromt_fiat.api.exposure import ExposureViewModel

# filepath = Path(__file__).parent / "exposure.toml"
# obj = ConfigHandler.load_file(filepath)


print(time.time_ns())
a = ExposureViewModel()
a.exposure_model.asset_locations = "nsi"
print(a)
