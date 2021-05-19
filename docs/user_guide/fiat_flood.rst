.. _fiat_flooding:

===============================
Setting up a flood damage model
===============================

To build a **flood damage model**  from an existing hazard layer, 
the model region_ is defined by a the grid of that hazard map. 
see example below. 

A typical workflow to setup a flood damage model schematization is privided in the
:download:`build_fiat.ini <../_examples/build_fiat.ini>` and shown below. 
Each section corresponds to one of the model :ref:`components` and the `[global]` section can be used to pass
aditional arguments to the :py:class:`~hydromt.models.fiat.FiatModel`. initialization.
An example is provided in :ref:`examples` section.


.. code-block:: console

    hydromt build fiat /path/to/model_root "{'grid': /path/to/hazard}" -i build_fiat.ini -vv


.. literalinclude:: ../_examples/build_fiat.ini
   :language: Ini


.. _region: https://deltares.github.io/hydromt/latest/user_guide/cli.html#region-options


