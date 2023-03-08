from pathlib import Path
from configparser import ConfigParser


### TO BE UPDATED ###
class Writer:
    def __init__(self):
        """Method to write the complete model schematization and configuration to file."""

        self.logger.info(f"Writing model data to {self.root}")
        # if in r, r+ mode, only write updated components
        if not self._write:
            self.logger.warning("Cannot write in read-only mode")
            return
        if self.config:  # try to read default if not yet set
            self.write_config()
        if self._staticmaps:
            self.write_staticmaps()
        if self._staticgeoms:
            self.write_staticgeoms()

    def set_root(self, root=None):
        # TODO: Change name to something that describes creating the folder structure
        # TODO: separate into folder structure setup and setting the config paths
        """Creates the required model folder structure.

        Parameters
        ----------
        root: str, optional
            Path to model root.
        """

        super().set_root(root=root, mode=mode)
        if self._write and root is not None:
            self._root = Path(root)

            # Set the general information.
            self.set_config("hazard_dp", self.root.joinpath("hazard"))
            self.set_config("exposure_dp", self.root.joinpath("exposure"))
            self.set_config("vulnerability_dp", self.root.joinpath("vulnerability"))
            self.set_config("output_dp", self.root.joinpath("output"))

            # Set the hazard information.
            if self.get_config("hazard"):
                for hazard_type, hazard_scenario in self.get_config("hazard").items():
                    for hazard_fn in hazard_scenario:
                        hazard_scenario[hazard_fn]["map_fn"] = self.get_config(
                            "hazard_dp"
                        ).joinpath(hazard_scenario[hazard_fn]["map_fn"].name)
                        self.set_config(
                            "hazard",
                            hazard_type,
                            hazard_fn,
                            hazard_scenario[hazard_fn],
                        )
            if self.get_config("exposure"):
                for exposure_fn in self.get_config("exposure"):
                    self.set_config(
                        "exposure",
                        exposure_fn,
                        "map_fn",
                        self.get_config("exposure_dp").joinpath(
                            self.get_config("exposure", exposure_fn, "map_fn").name,
                        ),
                    )
                    for sf_path in self.get_config(
                        "exposure",
                        exposure_fn,
                        "function_fn",
                    ).values():
                        if (
                            not self.get_config("vulnerability_dp")
                            .joinpath(
                                sf_path.name,
                            )
                            .is_file()
                        ):
                            copy(
                                sf_path,
                                self.get_config("vulnerability_dp").joinpath(
                                    sf_path.name,
                                ),
                            )
                    self.set_config(
                        "exposure",
                        exposure_fn,
                        "function_fn",
                        {
                            i: self.get_config("vulnerability_dp").joinpath(j.name)
                            for i, j in self.get_config(
                                "exposure",
                                exposure_fn,
                                "function_fn",
                            ).items()
                        },
                    )

    def write_config(self, fn):
        """Write config to fiat_configuration.ini"""

        parser = ConfigParser()

        # Store the general information.
        parser["setup_config"] = {
            "case": str(self.config.get("case")),
            "strategy": str(self.config.get("strategy")),
            "scenario": str(self.config.get("scenario")),
            "year": str(self.config.get("year")),
            "country": str(self.get_config("country")),
            "hazard_type": str(self.config.get("hazard_type")),
            "output_unit": str(self.config.get("output_unit")),
            "hazard_dp": str(self.config.get("hazard_dp").name),
            "exposure_dp": str(self.config.get("exposure_dp").name),
            "susceptibility_dp": str(self.config.get("susceptibility_dp").name),
            "output_dp": str(self.config.get("output_dp").name),
            "category_output": str(self.config.get("category_output")),
            "total_output": str(self.config.get("total_output")),
            "risk_output": str(self.config.get("risk_output")),
            "map_output": str(self.config.get("map_output")),
        }

        # Store the hazard information.
        for idx, hazard_scenario in enumerate(
            [
                (i, j)
                for i in self.get_config("hazard")
                for j in self.get_config("hazard", i)
            ]
        ):
            section_name = f"setup_hazard{idx + 1}"
            parser.add_section(section_name)
            for hazard_key in self.get_config(
                "hazard", hazard_scenario[0], hazard_scenario[1]
            ):
                if hazard_key == "map_fn":
                    parser.set(
                        section_name,
                        hazard_key,
                        str(
                            self.get_config(
                                "hazard",
                                hazard_scenario[0],
                                hazard_scenario[1],
                                hazard_key,
                            ).name
                        ),
                    )
                else:
                    parser.set(
                        section_name,
                        hazard_key,
                        str(
                            self.get_config(
                                "hazard",
                                hazard_scenario[0],
                                hazard_scenario[1],
                                hazard_key,
                            )
                        ),
                    )

        # Store the exposure information.
        for idx, exposure_fn in enumerate(self.get_config("exposure")):
            section_name = f"setup_exposure{idx + 1}"
            parser.add_section(section_name)
            for exposure_key in self.get_config("exposure", exposure_fn):
                if exposure_key == "map_fn":
                    parser.set(
                        section_name,
                        exposure_key,
                        str(
                            self.get_config("exposure", exposure_fn, exposure_key).name
                        ),
                    )
                elif exposure_key == "function_fn":
                    parser.set(
                        section_name,
                        exposure_key,
                        str(
                            {
                                i: j.name
                                for i, j in self.get_config(
                                    "exposure",
                                    exposure_fn,
                                    exposure_key,
                                ).items()
                            }
                        ),
                    )
                    for function_key in self.get_config(
                        "exposure",
                        exposure_fn,
                        exposure_key,
                    ):
                        sf_path = self.get_config(
                            "exposure",
                            exposure_fn,
                            exposure_key,
                        )[function_key]
                        if (
                            not self.get_config("susceptibility_dp")
                            .joinpath(
                                sf_path.name,
                            )
                            .is_file()
                        ):
                            copy(
                                sf_path,
                                self.get_config("susceptibility_dp").joinpath(
                                    sf_path.name,
                                ),
                            )
                else:
                    parser.set(
                        section_name,
                        exposure_key,
                        str(self.get_config("exposure", exposure_fn, exposure_key)),
                    )

        # Save the configuration file.
        with open(self.root.joinpath(self._CONF), "w") as config:
            parser.write(config)

    def write_staticgeoms(self):
        """Write staticmaps at <root/?/> in model ready format."""

        if not self._write:
            raise IOError("Model opened in read-only mode")
        if self._staticgeoms:
            for name, gdf in self._staticgeoms.items():
                gdf.to_file(
                    Path(self.root).joinpath(f"{name}.geojson"), driver="GeoJSON"
                )

    def write_staticmaps(self, compress="lzw"):
        """Write staticmaps at <root/?/> in model ready format."""

        # to write to gdal raster files use: self.staticmaps.raster.to_mapstack()
        # to write to netcdf use: self.staticmaps.to_netcdf()
        if not self._write:
            raise IOError("Model opened in read-only mode.")
        hazard_maps = [
            j for i in self.get_config("hazard") for j in self.get_config("hazard", i)
        ]
        if len(hazard_maps) > 0:
            self.staticmaps[hazard_maps].raster.to_mapstack(
                self.get_config("hazard_dp"), compress=compress
            )
        exposure_maps = [i for i in self.staticmaps.data_vars if i not in hazard_maps]
        if len(exposure_maps) > 0:
            self.staticmaps[exposure_maps].raster.to_mapstack(
                self.get_config("exposure_dp"), compress=compress
            )
