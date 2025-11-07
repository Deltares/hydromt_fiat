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

.. grid:: 4
    :gutter: 1

    .. grid-item-card::
        :text-align: center
        :link: user_guide_data_index
        :link-type: ref

        :octicon:`stack;5em`
        +++
        Data

    .. grid-item-card::
        :text-align: center
        :link: user_guide_model_index
        :link-type: ref

        :octicon:`package;5em`
        +++
        Model (building)

.. toctree::
   :caption: Table of Contents
   :maxdepth: 2
   :hidden:

   model/index.rst
   data/index.rst
