.. _index_user_guide:

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

For more information and examples, please visit the following pages:

- :ref:`Model and model components <model_user_guide>`

.. toctree::
   :caption: Table of Contents
   :maxdepth: 2
   :hidden:

   model.rst
