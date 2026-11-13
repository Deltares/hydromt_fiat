from pathlib import Path


def check_dir_exist(dir, name=None):
    """ """

    if not isinstance(dir, Path):
        raise TypeError(
            f"The directory indicated by the '{name}' parameter does not exist."
        )


def check_uniqueness(map_name_lst):
    def check_duplicates(lst):
        unique_elements = set()
        for element in lst:
            if element in unique_elements:
                return True  # Found a duplicate
            unique_elements.add(element)
        return False  # No duplicates found

    check = check_duplicates(map_name_lst)

    if check:
        raise ValueError("The filenames of the hazard maps should be unique.")


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
