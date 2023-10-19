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
