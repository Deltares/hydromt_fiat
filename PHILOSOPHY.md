# Design philosopphy of HydroMT-FIAT v1
This documents highlights the structure and design philosophy of HydroMT-FIAT.

## Main Module (fiat.py)

The main module of HydroMT-FIAT contains the fiat model (FIATModel).\
The FIATModel inherits from the [HydroMT-core Model](https://deltares.github.io/hydromt/stable/_generated/hydromt.model.Model.html#hydromt.model.Model) class.

A HydroMT model has data components to store it's data in.\
The HydroMT-FIAT model class has setup/ update methods that require data,\
manipulate data and eventually set the data in the corresponding data components.\
The raw data itself is described in a data catalog yml that is picked up by\
the HydroMT [DataCatalog](https://deltares.github.io/hydromt/stable/_generated/hydromt.data_catalog.DataCatalog.html#hydromt.data_catalog.DataCatalog).
The manipulation of the data is done in so called 'workflow functions'.\
The idea behind the FIATModel class and fiat.py in general is to keep it as lean\
as possible, i.e. pure logic is not meant to be in this file/ class but in separate\
workflows/ submodules.

The structure itself is really simple:\
[![](https://mermaid.ink/img/pako:eNp1kEtrwzAQhP-K2FMCjmv5JUuHQmq3kEPooeml6CIixTa1JKPI9BH836u6j0Ohe9v5ZnZgL3C0UgGD02Bfjp1wHh0ablCY7eputz3sAx7WaLO5RjcrDrXVozXK-DOH9bdvgXWAD8pPI9LKd1b-5U3gj6MUXv1juA2G3dV9UCGC1vUSmHeTikArp8XnChduOPhOacWBIQ5SuGcO3MwhMQrzZK3-CTk7tR2wkxjOYZuW4qYXrRP6V3XKSOVqOxkPLC3JcgTYBV6BZSSJ8wrjhJaY4jwpI3gDhss0rrKKkoxSmqRZns8RvC-1SVzQAlNa0owUBclISCjZe-v2Xw9e_jx_ALd7a8c?type=png)](https://mermaid.live/edit#pako:eNp1kEtrwzAQhP-K2FMCjmv5JUuHQmq3kEPooeml6CIixTa1JKPI9BH836u6j0Ohe9v5ZnZgL3C0UgGD02Bfjp1wHh0ablCY7eputz3sAx7WaLO5RjcrDrXVozXK-DOH9bdvgXWAD8pPI9LKd1b-5U3gj6MUXv1juA2G3dV9UCGC1vUSmHeTikArp8XnChduOPhOacWBIQ5SuGcO3MwhMQrzZK3-CTk7tR2wkxjOYZuW4qYXrRP6V3XKSOVqOxkPLC3JcgTYBV6BZSSJ8wrjhJaY4jwpI3gDhss0rrKKkoxSmqRZns8RvC-1SVzQAlNa0owUBclISCjZe-v2Xw9e_jx_ALd7a8c)

### 1. Components
HydroMT-FIAT makes use of 7 components to store (or set) it's data.

- `config` (ConfigComponent)
- `region` (RegionComponent; custom made)
- `exposure_data` (TablesComponent)
- `exposure_grid` (GridComponent)
- `exposure_geoms` (GeomsComponent)
- `hazard_grid` (GridComponent)
- `vulnerability_data` (TablesComponent)

#### Config component
Holds the configurations for the Delft-FIAT model.\
Can be set directly or/ and is set in the setup/ update methods specifically for the\
data the methods concern themselves with.\
The data is in essence a python dictionary.

#### Region component
Holds the region which is used to clip the data in the setup/ update methods.\
Custom made to hold one geometry at any given moment (or None is not set) and\
creates a union between the already set geometry and a newly added one to again result\
in one geometry present in the component.\
Will return a [GeoDataFrame](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.html).

#### Exposure data component
Holds the vector exposure data that is not solely the vector data itself.\
This component is still up for debate, as we might only shift the vector and table data\
at the writing stage.\
The data takes the form of a [DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html).

#### Exposure geoms component
Holds the geometries. Whether or not the exposure data component will stay, this might\
also hold the exposure table data within the [GeoDataFrame's](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.html) in this component.

#### Exposure grid component
Holds the gridded exposure data.\
The data takes the form of a xarray [Dataset](https://docs.xarray.dev/en/stable/generated/xarray.Dataset.html).

#### Hazard grid component
Holds the hazard data. These are either different events in one dataset or\
layer with different return periods part of one risk calculation.'\
The data takes the form of a xarray [Dataset](https://docs.xarray.dev/en/stable/generated/xarray.Dataset.html).

#### Vulnerability data component
Holds the vulnerability curves in a single table. This component also holds a table\
that links the vulnerability curves to the eventual exposure data\
(either geometry or grid).\
The data takes the form of a [DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html).

### 2. Setup methods
Setup methods are meant to translate raw input data to data that is accepted by\
the Delft-FIAT model and set some variables for the configurations file.

HydroMT-FIAT will have 6 setup methods:
- `setup_config`: for setting config variables directory
- `setup_region`: for setting the region to be used in other setup methods to clip the\
geospatial data
- `setup_exposure_grid`: for setting exposure in grid format
- `setup_exposure_geom`: for setting exposure in vector format
- `setup_hazard`: for setting the hazard data
- `setup_vulnerability`: for settings the vulnerability curves

The idea of the setup methods, as stated before, is to take in raw data\
manipulate said data until it fits the needs of the kernel and set it in the\
corresponding components. The input (data) for the setup methods will always be a\
reference to data defined in a HydroMT [DataCatalog](https://deltares.github.io/hydromt/stable/_generated/hydromt.data_catalog.DataCatalog.html#hydromt.data_catalog.DataCatalog).\
The rest of the (keyword) arguments are meant to be kept to a minimum to avoid\
overcomplication of the methods.

A Simple example of the a setup methods should do is shown down below:\
[![](https://mermaid.ink/img/pako:eNpVkUlrwzAQhf-KmZMNTvAiL9Kh0DjQS3tpD4Wii7DGC7GkoMh0CfnvVey0pYKBmaf3zTvMGVojERh0k3lvB2Fd8PjMdeDffdgM2B5OUbDZ3AW7kMMDukAKJ9b_cO_bxtdk-ohDtKq7xd1496uxh-vWVVfoBiPD080WKqHH4zwJh39ss7AyfLnl_JNxkVuju7GPIIbejhKYszPGoNAqcR3hfEU4uAEVcmC-lcIeOHB98cxR6Ddj1A9mzdwPwDoxnfw0H30m7kfRW6F-VYtaom3MrB0wQpYdwM7wASyl9TYnpK5oWiQ5Tcoshk9gGcm3tCAFIUlZ5XVWX2L4WlKTbZVXtKBJXSZVmqUljQHl6Ix9Wo-w3OLyDRRrdtM?type=png)](https://mermaid.live/edit#pako:eNpVkUlrwzAQhf-KmZMNTvAiL9Kh0DjQS3tpD4Wii7DGC7GkoMh0CfnvVey0pYKBmaf3zTvMGVojERh0k3lvB2Fd8PjMdeDffdgM2B5OUbDZ3AW7kMMDukAKJ9b_cO_bxtdk-ohDtKq7xd1496uxh-vWVVfoBiPD080WKqHH4zwJh39ss7AyfLnl_JNxkVuju7GPIIbejhKYszPGoNAqcR3hfEU4uAEVcmC-lcIeOHB98cxR6Ddj1A9mzdwPwDoxnfw0H30m7kfRW6F-VYtaom3MrB0wQpYdwM7wASyl9TYnpK5oWiQ5Tcoshk9gGcm3tCAFIUlZ5XVWX2L4WlKTbZVXtKBJXSZVmqUljQHl6Ix9Wo-w3OLyDRRrdtM)

### 3. Update methods
These methods have to be thought out a little more as these will work with data\
which has already been created via the setup methods. The use case of the methods\
will be to expand upon what is already there

## Workflow functions
Workflow functions are the place where the raw input data get manipulated and\
transformed into data that is understood by Delft-FIAT. For this purpose a separate\
submodules is/ will be created where files will be created that match the theme\
of the setup methods of the FIATModel class.

Most likely this will look like the following:
```
.
└── src/hydromt_fiat
    └── workflows
        ├── __init__.py
        ├── exposure.py
        ├── exposure_utils.py
        ├── hazard.py
        └── vulnerability.py
    ├── fiat.py
    └── < other files and submudles >
```

The workflows functions are meant to take the logic out of the setup methods in regards\
to manipulating the data to keep these methods as easy as possible to follow and\
maintain. The input for these methods is no longer an entry of the data catalog but\
the actual data itself (i.e. [DataFrame](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html)
or [GeoDataFrame](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoDataFrame.html)
or [Dataset](https://docs.xarray.dev/en/stable/generated/xarray.Dataset.html) etc).

## Custom Drivers
HydroMT-core provides the opportunity to define custom drivers for the data catalog.\
For HydroMT-FIAT it is more than likely that data will be requested from api's.\
So for this usecase custom drivers will be created to facilitate the request of data\
using an entry in the data catalog that refers to a custom driver to request data from\
an api.

Custom drivers will have their own submodule named drivers. The module will also\
contain the custom uri resolvers needed by the custom drivers. At the time or writing\
only one custom driver has been created. This driver facilitates the request of data\
from OpenStreetMap (OSM).

The folder structure will look something like this:
```
.
└── src/hydromt_fiat
    └── drivers
        ├── __init__.py
        ├── osm_driver.py
        ├── resolvers.py
        └── < other driver in the future.py>
    ├── fiat.py
    └── < other files and submudles >
```

## Miscellaneous
The HydroMT-FIAT module comes with a data submodule. This submodule holds a module\
/ function and a registry json file. This function is meant to fetch data which is\
parked on the [zenodo website under the HydroMT-FIAT header](https://zenodo.org/records/15084240).\
This data is used in the testing of HydroMT-FIAT but also in the examples meant for\
the users.

## Testing
Small unit tests that cover the codebase well (kind of obvious).\
Besides that, integration tests might be necessary.\
These integration tests could include running the build model with Delft-FIAT.

## Documentation
As far as I can see at the time of writing, there are two options in terms frameworks:
- Sphinx (based on rst's, although can support markdown)
- Quarto (Quarto;s own markdown variant)

Quarto is preferred, but sphinx is more in line with Hydromt-Core.

The docs should be fairly simple and contain:
- Gettings stated
  - Installation guide
  - examples
  - Faq?
- User guide
  - Setting up data catalog
  - How to use the cli
  - Using the python api
  - And of cource examples
  - Cover different situations
    - Build from scratch
    - Update
    - etc.
- A clear well structured API reference
- A link to core docs
