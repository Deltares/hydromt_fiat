from pathlib import Path

### TO BE UPDATED ###
#class Validation:
#    """CONTROL FUNCTIONS"""

def check_dir_exist(dir, name=None):
    """ """

    if not isinstance(dir, Path):
        raise TypeError(
            f"The directory indicated by the '{name}' parameter does not exist."
        )

def check_file_exist(root, param_lst, name=None, input_dir=None):
    """ """
    root = Path(root)
    param_lst = [Path(p) for p in param_lst]
    for param_idx, param in enumerate(param_lst):
        if isinstance(param, dict):
            fn_lst = list(param.values())
        else:
            fn_lst = [param]
        for fn_idx, fn in enumerate(fn_lst):
            if not Path(fn).is_file():
                if root.joinpath(fn).is_file():
                    if isinstance(param, dict):
                        param_lst[param_idx][
                            list(param.keys())[fn_idx]
                        ] = root.joinpath(fn)
                    else:
                        param_lst[param_idx] = root.joinpath(fn)
                if input_dir is not None:
                    if input_dir.joinpath(fn).is_file():
                        if isinstance(param, dict):
                            param_lst[param_idx][
                                list(param.keys())[fn_idx]
                            ] = input_dir.joinpath(fn)
                        else:
                            param_lst[param_idx] = input_dir.joinpath(fn)
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
                        f" exist in the directory '{root}'."
                    )
                else:
                    raise TypeError(
                        f"The file indicated by the '{name}' parameter does not"
                        f" exist in either of the directories '{root}' or "
                        f"'{input_dir}'."
                    )

def check_uniqueness(*args, ds_check, file_type=None, filename=None):
    """TODO: this function should be checked"""

    args = list(args)
    if len(args) == 1 and "." in args[0]:
        args = args[0].split(".") + args[1:]
    branch = args.pop(-1)
    for key in args[::-1]:
        branch = {key: branch}

    if args[0].get_config(args[0], args[1]):
        for key in ds_check.data_vars:
            if filename == key:
                raise ValueError(
                    f"The filenames of the {file_type} maps should be unique."
                )
            #if (
            #    self.get_config(args[0], args[1], key) # not sure what this self refers too, Validation class had no attribute
            #    == list(branch[args[0]][args[1]].values())[0]
            #):
            #    raise ValueError("Each model input layers must be unique.")

def check_param_type(param, name=None, types=None):
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

def get_param(param_lst, map_fn_lst, file_type, filename, i, param_name):
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
