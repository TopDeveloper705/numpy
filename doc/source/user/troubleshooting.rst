***************
Troubleshooting
***************

.. note::

    Since this information may be updated regularly, please refer to the
    most up to date version in the development version of the documentation.


ImportError
===========

In certain cases a failed installation or setup issue can cause you to
see the following error message::

    IMPORTANT: PLEASE READ THIS FOR ADVICE ON HOW TO SOLVE THIS ISSUE!

    Importing the numpy c-extensions failed. This error can happen for
    different reasons, often due to issues with your setup.

The error has a few additional information to help you trouble shoot:

* Your Python version
* Your NumPy version

Please check both of these carefully to see if they are what you expect.
You may need to check your ``PATH`` or ``PYTHONPATH`` environment variables
(see "Check Environment Variables" below).

The following sections list commonly reported issues depending on your Setup.
If you have an issue/solution that you think should appear please open a
NumPy issue so that it will be added.

There are a few commonly reported issues depending on your system/setup.
If none of the following tips help you, please be sure to note the following:

* how you installed Python
* how you installed NumPy
* your operating system
* whether or not you have multiple versions of Python installed
* if you built from source, your compiler versions and ideally a build log

when investigating further and asking for support.


Using Python from ``conda`` (Anaconda)
--------------------------------------

Please make sure that you have activated your conda environment.
See also the `conda user-guide <https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#activating-an-environment>`_.


Using Anaconda/conda Python within PyCharm
------------------------------------------

There are fairly common issues when using PyCharm together with Anaconda,
please see the `PyCharm support <https://www.jetbrains.com/help/pycharm/conda-support-creating-conda-virtual-environment.html>`_


Raspberry Pi
------------

There are sometimes issues reported on Raspberry Pi setups when installing
using ``pip3 install`` (or ``pip`` install). These will typically mention::

    libf77blas.so.3: cannot open shared object file: No such file or directory


The solution will be to either::

    sudo apt-get install libatlas-base-dev

to install the missing libraries expected by the self compiled NumPy
(ATLAS is a possible provider of linear algebra).

*Alternatively* use the NumPy provided by raspian. In which case run::

    pip3 uninstall numpy  # remove previously installed version
    apt install python3-numpy


Debug build on Windows
----------------------

Rather than building your project in ``DEBUG`` mode on windows, try
building in ``RELEASE`` mode with debug symbols and no optimization.
Full ``DEBUG`` mode on windows changes the names of the DLLs python
expects to find, so if you wish to truly work in ``DEBUG`` mode you will
need to recompile the entire stack of python modules you work with
including NumPy


All Setups
----------

Occasionally there may be simple issues with old or bad installations
of NumPy. In this case you may just try to uninstall and reinstall NumPy.
Make sure that NumPy is not found after uninstalling.


Development Setup
-----------------

If you are using a development setup, make sure to run ``git clean -xdf``
to delete all files not under version control (be careful not to lose
any modifications you made, e.g. ``site.cfg``).
In many cases files from old builds may lead to incorrect builds.


Check Environment Variables
---------------------------

In general how to set and check your environment variables depends on
your system. If you can open a correct python shell, you can also run the
following in python::

    import os
    PYTHONPATH = os.environ['PYTHONPATH'].split(os.pathsep)
    print("The PYTHONPATH is:", PYTHONPATH)
    PATH = os.environ['PATH'].split(os.pathsep)
    print("The PATH is:", PATH)

This may mainly help you if you are not running the python and/or NumPy
version you are expecting to run.

