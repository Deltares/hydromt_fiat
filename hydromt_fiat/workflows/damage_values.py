import pandas as pd
from pathlib import Path
from typing import Union
from hydromt_fiat.api.data_types import Conversion

default_jrc_max_damage_adjustment_values = {
    "construction_cost_vs_depreciated_value_res": 0.6,
    "construction_cost_vs_depreciated_value_com": 0.6,
    "construction_cost_vs_depreciated_value_ind": 0.6,
    "max_damage_content_inventory_res": 0.5,
    "max_damage_content_inventory_com": 1,
    "max_damage_content_inventory_ind": 1.5,
    "undamageable_part_res": 0.4,
    "undamageable_part_com": 0.4,
    "undamageable_part_ind": 0.4,
    "material_used_res": 1,
    "material_used_com": 1,
    "material_used_ind": 1,
}


def preprocess_jrc_damage_values(
    jrc_base_damage_values: pd.DataFrame,
    country: str,
    eur_to_us_dollar: bool = False,
    max_damage_adjustment_values: dict = default_jrc_max_damage_adjustment_values,
) -> dict:
    """Preprocess the JRC damage values data.

    Parameters
    ----------
    jrc_base_damage_values : pd.DataFrame
        The JRC damage values data.
    country : str
        The country to filter the data on.
    eur_to_us_dollar: bool
        Convert JRC Damage Values (Euro 2010) into US-Dollars (2025)

    Returns
    -------
    pd.DataFrame
        The preprocessed JRC damage values data.
    """
    # Create an empty dictionary that will be used to store the damage values per
    # category
    damage_values = {}

    # Rename the column names to shorter names
    rename_dict = {
        "Construction Cost Residential (2010 €)": "residential",
        "Construction Cost Commercial (2010 €)": "commercial",
        "Construction Cost Industrial (2010 €)": "industrial",
    }
    jrc_base_damage_values.rename(columns=rename_dict, inplace=True)

    # Filter the data on the country
    jrc_base_damage_values["Country"] = jrc_base_damage_values["Country"].str.lower()
    jrc_base_damage_values = jrc_base_damage_values.loc[
        jrc_base_damage_values["Country"] == country.lower()
    ]

    # We adjust the max damage values for the different building types with the given
    # or default values
    for building_type in ["residential", "commercial", "industrial"]:
        # Get the adjustment values for the building type
        building_type_short = building_type[:3]
        cc_vs_dv = max_damage_adjustment_values[
            f"construction_cost_vs_depreciated_value_{building_type_short}"
        ]
        mdci = max_damage_adjustment_values[
            f"max_damage_content_inventory_{building_type_short}"
        ]
        up = max_damage_adjustment_values[f"undamageable_part_{building_type_short}"]
        mu = max_damage_adjustment_values[f"material_used_{building_type_short}"]

        # Get the JRC base value for the building type
        jrc_base_value = jrc_base_damage_values[building_type].values[0]

        # Calculate the adjusted damage value for structure, content and total damage
        damage_values[building_type] = {
            "structure": (jrc_base_value * cc_vs_dv * (1 - up) * mu),
            "content": ((jrc_base_value * cc_vs_dv * (1 - up) * mu) * mdci),
            "total": (
                (jrc_base_value * cc_vs_dv * (1 - up) * mu)
                + ((jrc_base_value * cc_vs_dv * (1 - up) * mu) * mdci)
            ),
        }
    
    if eur_to_us_dollar:
        for damage_types, occupancy_types in damage_values.items():
            for occupancy_type in occupancy_types:
                occupancy_types[occupancy_type] *= Conversion.eur_to_us_dollars.value
    return damage_values


def preprocess_hazus_damage_values(hazus_table: pd.DataFrame) -> dict:
    """Preprocess the Hazus damage values data.

    Parameters
    ----------
    hazus_table : pd.DataFrame
        The Hazus damage values data.

    Returns
    -------
    dict
        The preprocessed Hazus damage values data.
    """
    # Calculate the content damages per occupancy type
    hazus_table["content"] = (
        hazus_table["Maximum structure damage [$/sq.ft] (2018)"]
        * hazus_table["Maximum content damages [% of maximum structural damages]"]
        / 100
    )

    # Rename the long names for structure damage values and the occupancy types
    # to shorter names
    hazus_table.rename(
        columns={
            "Maximum structure damage [$/sq.ft] (2018)": "structure",
            "Occupancy/utility type": "occupancy",
        },
        inplace=True,
    )

    # Get the damage values for the different damage types
    damage_values = {
        occ: {"structure": struc, "content": cont}
        for occ, struc, cont in zip(
            hazus_table["occupancy"], hazus_table["structure"], hazus_table["content"]
        )
    }

    return damage_values

def preprocess_damage_values(
    base_damage_values: pd.DataFrame,
    damage_translation_fn: Union[Path, str],
) -> dict:
    """Preprocess the JRC damage values data.

    Parameters
    ----------
    base_damage_values : pd.DataFrame
        The JRC damage values data.
    damage_translation_fn : Union[Path, str]
        The path to a file that relates the max. potential damage values with the exposure primary_object_type. 

    Returns
    -------
    pd.DataFrame
        The preprocessed JRC damage values data.
    """
    # Create an empty dictionary that will be used to store the damage values per
    # category
    damage_values = {}
    

    # Read a csv with the translation of the damage values with column a: max. potential damage naming convention and column b: naming convention as link for damage curve
    # Rename the column names to shorter names
    translation_df = pd.read_csv(damage_translation_fn, header = None, encoding='utf-8', index_col = None)

    rename_dict = dict(zip(translation_df.iloc[0:,0],translation_df.iloc[0:,1]))

    # Rename damage values with primary_object_type
    base_damage_values.rename(columns=rename_dict, inplace=True)
    

    # Get building types and their values
    for building_type in translation_df.iloc[0:,1]:
        base_damage_value = base_damage_values[building_type].values[0]
        damage_values[building_type] = {
                "structure":  base_damage_value,
                "content": base_damage_value,
                "total": base_damage_value, 
        } 

    return damage_values