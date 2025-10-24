.. _user_guide_index:

==========
User guide
==========
The purpose of HydroMT-FIAT is of course to build a model that can be run by
Delft-FIAT. This is done with the help of the :class:`FIATModel <hydromt_fiat.FIATModel>`
model class. This can be seen as the general manager of the model building process.
The FIATModel model class manages and connects model components. A model component
focuses on a single specific data entry needed by Delft-FIAT, e.g. one component for
exposure vector data, one for vulnerability data etc. As the FIATModel model class
connects the components with each other, data build in e.g. the vulnerability component
can be accessed and used by the exposure vector component.

A quick overview of all the components is presented on the following page:

- :ref:`Model components <user_guide_components>`

All of these components need (raw) input data when trying to set up data for Delft-FIAT.
Most common is defining the data in a HydroMT `data catalog <Data_Catalog_>`_ and use
the created entry in the data catalog as input.


.. toctree::
   :caption: Table of Contents
   :maxdepth: 2
   :hidden:

   components.rst

.. _Data_Catalog: https://deltares.github.io/hydromt/stable/guides/advanced_user/data_prepare_cat.html
