from pathlib import Path

from hydromt_fiat.loader import ConfigHandler

filepath = Path(__file__).parent / "exposure.toml"
obj = ConfigHandler.load_file(filepath)

print("a")
print("a")
