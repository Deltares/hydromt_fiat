.. _user_guide_model_index:

================
Model (building)
================

This is done with the help of the :class:`FIATModel <hydromt_fiat.FIATModel>`
model class. This can be seen as the general manager of the model building process.
The FIATModel model class manages and connects model components. A model component
focuses on a single specific data entry needed by Delft-FIAT, e.g. one component for
exposure vector data, one for vulnerability data etc. As the FIATModel model class
connects the components with each other, data build in e.g. the vulnerability component
can be accessed and used by the exposure vector component.

.. toctree::
   :caption: Table of Contents
   :maxdepth: 2
   :hidden:

   components.rst
