import time
from re import S

from hydromt_fiat.api.exposure import ExposureViewModel

# filepath = Path(__file__).parent / "exposure.toml"
# obj = ConfigHandler.load_file(filepath)


print(time.time_ns())
a = ExposureViewModel()
print(time.time_ns())
time.sleep(2)
print(time.time_ns())
S = ExposureViewModel()
print(time.time_ns())
