from pathlib import Path

### TO BE UPDATED ###
class Validation:
    """ CONTROL FUNCTIONS """

    # Function that iterates over a list with parameters
    def get_param(self, param_lst, map_fn_lst, file_type, filename, i, param_name):
        """ """

        if len(param_lst) == 1:
            return param_lst[0]
        elif len(param_lst) != 1 and len(map_fn_lst) == len(param_lst):
            return param_lst[i]
        elif len(param_lst) != 1 and len(map_fn_lst) != len(param_lst):
            raise IndexError(
                f"Could not derive the {param_name} parameter for {file_type} "
                f"map: {filename}."
            )
        
    #Check functions. We can skip them since the chek will be done in th GUI.
    def check_param_type(self, param, name=None, types=None):
        """ """

        if not isinstance(param, list):
            raise TypeError(
                f"The '{name}_lst' parameter should be a of {list}, received a "
                f"{type(param)} instead."
            )
        for i in param:
            if not isinstance(i, types):
                if isinstance(types, tuple):
                    types = " or ".join([str(j) for j in types])
                else:
                    types = types
                raise TypeError(
                    f"The '{name}' parameter should be a of {types}, received a "
                    f"{type(i)} instead."
                )
            
    def check_file_exist(self, model_fiat, param_lst, name=None, input_dir=None):
        """ """

        for param_idx, param in enumerate(param_lst):
            if isinstance(param, dict):
                fn_lst = list(param.values())
            else:
                fn_lst = [param]
            for fn_idx, fn in enumerate(fn_lst):
                if not Path(fn).is_file():
                    if model_fiat.root.joinpath(fn).is_file():
                        if isinstance(param, dict):
                            param_lst[param_idx][
                                list(param.keys())[fn_idx]
                            ] = model_fiat.root.joinpath(fn)
                        else:
                            param_lst[param_idx] = model_fiat.root.joinpath(fn)
                    if input_dir is not None:
                        if model_fiat.get_config(input_dir).joinpath(fn).is_file():
                            if isinstance(param, dict):
                                param_lst[param_idx][
                                    list(param.keys())[fn_idx]
                                ] = model_fiat.get_config(input_dir).joinpath(fn)
                            else:
                                param_lst[param_idx] = model_fiat.get_config(
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
                            f" exist in the directory '{model_fiat.root}'."
                        )
                    else:
                        raise TypeError(
                            f"The file indicated by the '{name}' parameter does not"
                            f" exist in either of the directories '{model_fiat.root}' or "
                            f"'{model_fiat.get_config(input_dir)}'."
                        )


    def check_uniqueness(self, model_fiat, *args, file_type=None, filename=None):
        """ """

        args = list(args)
        if len(args) == 1 and "." in args[0]:
            args = args[0].split(".") + args[1:]
        branch = args.pop(-1)
        for key in args[::-1]:
            branch = {key: branch}

        if model_fiat.get_config(args[0], args[1]):
            for key in model_fiat.staticmaps.data_vars:
                if filename == key:
                    raise ValueError(
                        f"The filenames of the {file_type} maps should be unique."
                    )
                if (
                    model_fiat.get_config(args[0], args[1], key)
                    == list(branch[args[0]][args[1]].values())[0]
                ):
                    raise ValueError(f"Each model input layers must be unique.")
