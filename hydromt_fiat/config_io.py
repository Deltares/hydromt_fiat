from configparser import ConfigParser
from hydromt.cli.cli_utils import parse_config

### TO BE UPDATED ###
class Config:
    def _configread(self, fn):
        """Parse fiat_configuration.ini to dict."""

        # Read and parse the fiat_configuration.ini.
        opt = parse_config(fn)

        # Store the general information.
        config = opt["setup_config"]

        # Store the hazard information.
        config["hazard"] = {}
        for hazard_dict in [opt[key] for key in opt.keys() if "hazard" in key]:
            hazard_dict.update(
                {"map_fn": config["hazard_dp"].joinpath(hazard_dict["map_fn"])}
            )
            if not hazard_dict["map_type"] in config["hazard"].keys():
                config["hazard"][hazard_dict["map_type"]] = {
                    hazard_dict["map_fn"].stem: hazard_dict,
                }
            else:
                config["hazard"][hazard_dict["map_type"]].update(
                    {
                        hazard_dict["map_fn"].stem: hazard_dict,
                    }
                )

        # Store the exposure information.
        config["exposure"] = {}
        for exposure_dict in [opt[key] for key in opt.keys() if "exposure" in key]:
            exposure_dict.update(
                {"map_fn": config["exposure_dp"].joinpath(exposure_dict["map_fn"])}
            )
            exposure_dict.update(
                {
                    "function_fn": {
                        i: config["susceptibility_dp"].joinpath(j)
                        for i, j in exposure_dict["function_fn"].items()
                    }
                }
            )
            config["exposure"].update(
                {
                    exposure_dict["map_fn"].stem: exposure_dict,
                }
            )

        return config

    def _configwrite(self, fn):
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

