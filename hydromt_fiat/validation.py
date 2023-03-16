from pathlib import Path

### TO BE UPDATED ###
class Validation:
    """CONTROL FUNCTIONS"""

    def check_dir_exist(self, dir, name=None):
        """ """

        if not isinstance(dir, Path):
            raise TypeError(
                f"The directory indicated by the '{name}' parameter does not exist."
            )

    def check_file_exist(self, param_lst, name=None, input_dir=None):
        """ """

        for param_idx, param in enumerate(param_lst):
            if isinstance(param, dict):
                fn_lst = list(param.values())
            else:
                fn_lst = [param]
            for fn_idx, fn in enumerate(fn_lst):
                if not Path(fn).is_file():
                    if self.root.joinpath(fn).is_file():
                        if isinstance(param, dict):
                            param_lst[param_idx][
                                list(param.keys())[fn_idx]
                            ] = self.root.joinpath(fn)
                        else:
                            param_lst[param_idx] = self.root.joinpath(fn)
                    if input_dir is not None:
                        if self.get_config(input_dir).joinpath(fn).is_file():
                            if isinstance(param, dict):
                                param_lst[param_idx][
                                    list(param.keys())[fn_idx]
                                ] = self.get_config(input_dir).joinpath(fn)
                            else:
                                param_lst[param_idx] = self.get_config(
                                    input_dir
                                ).joinpath(fn)
                else:
                    if isinstance(param, dict):
                        param_lst[param_idx][list(param.keys())[fn_idx]] = Path(fn)
                    else:
                        param_lst[param_idx] = Path(fn)
                try:
                    if isinstance(param, dict):
                        assert isinstance(
                            param_lst[param_idx][list(param.keys())[fn_idx]], Path
                        )
                    else:
                        assert isinstance(param_lst[param_idx], Path)
                except AssertionError:
                    if input_dir is None:
                        raise TypeError(
                            f"The file indicated by the '{name}' parameter does not"
                            f" exist in the directory '{self.root}'."
                        )
                    else:
                        raise TypeError(
                            f"The file indicated by the '{name}' parameter does not"
                            f" exist in either of the directories '{self.root}' or "
                            f"'{self.get_config(input_dir)}'."
                        )

    def check_uniqueness(self, *args, file_type=None, filename=None):
        """ """

        args = list(args)
        if len(args) == 1 and "." in args[0]:
            args = args[0].split(".") + args[1:]
        branch = args.pop(-1)
        for key in args[::-1]:
            branch = {key: branch}

        if self.get_config(args[0], args[1]):
            for key in self.staticmaps.data_vars:
                if filename == key:
                    raise ValueError(
                        f"The filenames of the {file_type} maps should be unique."
                    )
                if (
                    self.get_config(args[0], args[1], key)
                    == list(branch[args[0]][args[1]].values())[0]
                ):
                    raise ValueError("Each model input layers must be unique.")
