.. _overview_install_guide:

==================
Installation guide
==================

Prerequisites
=============

You'll need **Python 3.11, 3.12, or 3.13** and a package manager.
We recommend using pixi.

Installation
============

HydroMT-FIAT is available from pypi and conda-forge,
but we recommend installing from conda-forge using the pixi package manager.

Install HydroMT-FIAT
------------------------------------
.. Tip::

    This is our recommended way of installing HydroMT!

To make the HydroMT cli available anywhere on the system using pixi execute the command:

.. code-block:: console

    $ pixi global install hydromt_fiat

This will create a new isolated environment and install hydromt into it.
To test whether the installation was successful you can run :code:`hydromt --plugins` and the output should look approximately like the one below:

.. code-block:: shell

    $ hydromt --plugins

.. program-output:: hydromt --plugins

Installing HydroMT-FIAT in a python environment
-----------------------------------------------

If you wish to use hydromt-fiat through it's Python API, you can use pixi to create an environment for this too.
If you do not have a ``pyproject.toml`` yet you can make one by executing the command:

.. code-block:: shell

    $ pixi init --format pyproject

Which will create it for you.
After this simply add HydroMT-FIAT as a dependency with the following command:

.. code-block:: shell

    $ pixi add hydromt_fiat

Once you have your new (or existing ``pyproject.toml``) file install the pixi
environment and activate it with the following commands to be able to start using it:

.. code-block:: shell

    $ pixi install
    $ pixi shell activate
