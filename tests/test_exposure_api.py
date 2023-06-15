# filepath = Path(__file__).parent / "exposure.toml"
# obj = ConfigHandler.load_file(filepath)


# print(time.time_ns())
# a = ExposureViewModel()
# a.exposure_model.asset_locations = "nsi"
# print(a)


# class ExposureVectorIni(BaseModel):
#     asset_locations: Union[str, Path]
#     occupancy_type: Union[str, Path]
#     max_potential_damage: Union[int, Path]
#     ground_floor_height: Union[int, Path]
#     gfh_units: Units
#     extraction_method: ExtractionMethod


# a = ExposureVectorIni.parse_obj({})

# print(a)


def test_f(key: str, **kwargs):
    return kwargs


a = test_f(key="bana", sd=5, ds=4)
print(a)

a = HydroMtViewModel(Path(__file__).parent, str(Path(__file__).parent / "test.yml"))
a.build_config_ini()
b = HydroMtViewModel(Path(__file__).parent, str(Path(__file__).parent / "test.yml"))
print(a)
