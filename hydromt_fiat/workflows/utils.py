import pandas as pd


def detect_delimiter(csvFile):
    """From stackoverflow
    https://stackoverflow.com/questions/16312104/can-i-import-a-csv-file-and-automatically-infer-the-delimiter
    """
    with open(csvFile, "r") as myCsvfile:
        header = myCsvfile.readline()
        if header.find(";") != -1:
            return ";"
        if header.find(",") != -1:
            return ","
    # default delimiter
    return ","


def get_us_county_numbers(county_names: list, states_counties_table: pd.DataFrame) -> list:
    county_numbers = list(states_counties_table.loc[states_counties_table["COUNTYNAME"].isin(county_names), "COUNTYFP"].values)
    county_numbers = [str(cn).zfill(3) for cn in county_numbers]
    return county_numbers