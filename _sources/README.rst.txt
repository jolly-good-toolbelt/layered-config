layered_config
==============

A simple library to ease maintaining groups of similar configurations:
   * Keep config files DRY like code.
   * Allow environment variables to override configuration file values.
   * `munch`_ your loaded configuration for easy field access.

Instead of copy'n'paste-ing related configuration files for different situations,
refactor the configuration sections and keys into separate smaller configuration files.
Then use this library to combine those files in various ways to produce a single |ConfigParser| object,
as if it had come from a single file.


tl;dr Quick Start in 3 Easy Steps:
----------------------------------

1. Create some configs:
~~~~~~~~~~~~~~~~~~~~~~~

For this simple example, consider three config files:

    | ``../base.config`` - all the common stuff between your environments,
      stored in the parent directory of the master.config file.
    | ``staging.config`` - config info specific to your staging environment.
    | ``demo.config`` - config info specific to your demo environment.

Create a ``master.config`` file describing how to layer the simpler config files.
The master config file's name is arbitrary.
Your code needs to know its name, but this library doesn't care.

``master.config`` file:

.. code:: INI

    [staging environment]
    # layers is a comma separated list of configuration files to load,
    # in order, left to right: ``../base.config`` is loaded first, and then
    # ``staging.config`` is loaded over top of it.
    # The file names can be absolute paths, or relative paths.
    # Relative paths are relative to the directory containing the master.config file.
    layers = ../base.config, staging.config

    [demo environment]
    layers = ../base.config, demo.config


2. Add One Call to Your Code:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from layered_config import load_cake
    # ...
    my_config_parser_instance = load_cake("master.config", config_section_name)


3. What Just Happened?
~~~~~~~~~~~~~~~~~~~~~~

The call to ``load_cake``:

#. created a new empty |ConfigParser| object (see the API docs if you want to customize it).
#. looked in the ``master.config`` file for a section matching the value of ``config_section_name``.
#. retrieved the value for the ``layers`` key of that section.
#. processed the files in that value, from left to right,
   loading each config file into the ConfigParser instance, and making sure the file exists.
   For the example above, this means that values defined in ``../base.config`` can be replaced by,
   and/or added to by, those in ``staging.config`` or ``demo.config``


A few more details
------------------

"Cake?" - yeah, layers of configuration files, we call a cake.
There were many analogies to chose from, we chose cake.

The result of loading a configuration cake is a plain ol' Python |ConfigParser| instance,
an old Python class we know and love. Or at least know.

"Python's ``ConfigParser`` already supports loading more than one configuration file like this, what gives?"

   * ConfigParser is designed to ignore files it can't find, on purpose.
     We want to consider that an error.
   * Calling ConfigParser directly you have to put the configuration file list into your code.
     We want to allow the list of configuration files itself
     to be changed and updated without having to make any code changes.
   * ConfigParser does not support environment variable overrides.
     We have found environment variable overrides very helpful for CICD situations as well as
     one-time local testing.

"What about config tool X?"

   * We looked at several other tools before deciding on writing this one.
     Detailed comparative analysis to come in a future PR.

.. _`munch`: https://pypi.org/project/munch/
.. |ConfigParser| replace:: :py:class:`~configparser.ConfigParser`
