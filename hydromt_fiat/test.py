from pathlib import Path

from hydromt_fiat.loader import MBuilderComponent

filepath = Path(__file__).parent / "exposure.toml"
obj = MBuilderComponent.load_file(filepath)

print("a")
print("a")
