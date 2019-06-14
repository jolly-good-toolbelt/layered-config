"""
Tools for working with the ``ConfigParser`` instances.

:py:func:`load_cake` - Load layers of configuration files
with optional environment variable overrides.

:py:func:`munchify_config` - copy a ``ConfigParser`` instance to a `munch`_ to support
attribute access to configuration data. (Note: ``qe-config[munch]`` must be installed)

Layers of configuration files?  Yes! Read on!

Application or test configuration is often dependent upon
the specific environment being used.
Across many environments, there can be a good deal of common configuration as well.
Cut'n'paste-ing configuration files
and trying to maintain the various duplicated configurations is a challenge,
and is not DRY.
``load_cake`` gives you a way to layer configurations
so you can have common configurations in one place,
and use them, with variations, in many places.
For convenience a layering of configuration files is called a config cake,
or just a cake.

Additionally, ``load_cake``'s configuration file can declare
that environment variables can be used to override configuration settings.
This makes it easy to have a cake used by your CI/CD server
and still permit configuration values to be defined/overridden
with manually entered job parameters.

``load_cake`` returns a plain old Python ``ConfigParser`` instance
that we already know and love. Or at least know.

The built-in Python ``ConfigParser`` class
already supports layering multiple configuration files;
``load_cake`` allows your code to specify your layering
in an external 'master' config file.
The 'master' config file also lets you explicitly configure
if, and how, environment variable overrides work.
Note that environment variable overrides are processed only once,
when the configuration cake's layers are processed.
If you want to change the configuration dynamically after that,
use ``ConfigParser``'s methods,
as you would with any ``ConfigParser`` instance.
``load_cake`` merges configuration files
just as the ``ConfigParser.read()`` method does,
but, unlike ``read()``, all the files must exist.

The 'master' config file has sections that represent your various cakes.
Each cake section must have a ``layers`` key defining
the relative paths of configuration files to be loaded, from left to right.
All the keys and their values from the cake's section of the 'master' config file
will be set in the ``defaults`` dictionary of the ``ConfigParser`` instance
`before` the config files from the ``layers`` key are loaded.

If a section for defining how environment variable overrides work
is included in the 'master' config file,
or any of the the config files from the layers,
then config values can be overridden with environment variables.


Here is a simple example.

base.config::

    [Section-A]
    key0 = value0
    key1 = value1
    .  .  .

staging.config::

    [Section-A]
    key0 = staging_value0
    .  .  .

demo.config::

    [Section-A]
    key0 = demo_value0
    . . .

master.config::

    [ENVIRONMENT VARIABLE OVERRIDE INFO]
    # Override configuration data by setting environment variables with this prefix;
    prefix=MyPrefix

    # Environment variable overrides will be of the form:
    #     <prefix><separator><section name><separator><option name>
    # In this example:
    #     MyPrefix__Section-A__key3=env_var_value_here
    separator=__

    [env1]
    # Each section name is of the form: <thing>
    # You probably want <thing> to be helpful; this example shows that the
    # section name is arbitrary and doesn't affect or determine any of the
    # config file names.

    # layers is a comma separated list of configuration files to load,
    # in order from left to right.
    layers = base.config, staging.config

    [env2]
    layers = base.config, demo.config
    key1 = value1
    all extra keys = and values will be in the defaults of the new config parser


How to use it::

    from qe_config import load_cake

    # Load a configuration from the master config file for environment 1:
    my_config = load_cake('master.config', 'env1')


.. _`munch`: https://pypi.org/project/munch/
"""

from configparser import ConfigParser
import os


def string_to_list(source, sep=",", maxsplit=-1, chars=None):
    """
    ``.split()`` a string into a list and ``.strip()`` each piece.

    For handling lists of things, from config files, etc.

    Args:
        source (str): the source string to process
        sep (str, optional): The ``.split`` ``sep`` (separator) to use.
        maxsplit (int, optional): The ``.split`` ``maxsplit`` parameter to use.
        chars (str, optional): The ``.strip`` ``chars`` parameter to use.
    """
    return [item.strip(chars) for item in source.split(sep, maxsplit)]


CONFIG_FILE_LIST_KEY = "layers"
ENV_VAR_SECTION_NAME = "ENVIRONMENT VARIABLE OVERRIDE INFO"
# Sections in the master config that should also be included
# in the config returned by load_cake.
MASTER_CONFIG_SECTIONS_TO_KEEP = [
    # We keep the environment variable override section in the config,
    # since it will be used for determining if and how
    # environment variable overrides will work.
    ENV_VAR_SECTION_NAME
]


def _filenames_relative_to(base_file, filename_list):
    base_dir = os.path.dirname(os.path.abspath(base_file))
    return [
        os.path.join(base_dir, os.path.expanduser(filename))
        for filename in filename_list
    ]


def _must_read(config, filename):
    if not config.read(filename):
        raise FileNotFoundError("Cannot read config file: {}".format(filename))


def _env_override(config, environment):
    """Process environment overrides, if any are configured."""
    if not config.has_section(ENV_VAR_SECTION_NAME):
        return

    prefix = config.get(ENV_VAR_SECTION_NAME, "prefix")
    separator = config.get(ENV_VAR_SECTION_NAME, "separator")

    env_prefix = prefix + separator
    for key, value in environment.items():
        if not key.startswith(env_prefix):
            continue
        parts = key.split(separator, 2)
        if len(parts) != 3:
            continue
        _, section, option = parts
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, option, value)


def load_cake(master_config_path, cake_name, into_config=None):
    """
    Load a layered configuration cake by name from a master config file.

    All the keys and their values from the ``cake_name`` section
    of the ``master_config`` file will be added to the defaults dictionary
    of the ``into_config`` config parser before any of the layers config
    files are loaded.

    Args:
        master_config_path (str): the file path for the master configuration file.
        cake_name (str): the particular configuration to load as described
            in the master configuration file.
            This is the name of a section of the master configuration file.
        into_config (ConfigParser, optional): A pre-created config parser
            to load the cake in to. If None, a plain ``ConfigParser`` is created.
            Use this if want a different variant of a ``ConfigParser`` to be used;
            for example, if you don't want the default interpolation that a
            plain ``ConfigParser`` uses.

    Returns:
        A ``ConfigParser`` instance.

    Raises:
        NoSectionError: If ``cake_name`` is not found in the master config file.
        NoOptionError: If any required options are missing, either from the
            environment override section, or any individual CAKE section.

    """
    master_config_path = os.path.expanduser(master_config_path)
    config = ConfigParser() if into_config is None else into_config
    _must_read(config, master_config_path)
    section_name = cake_name

    filename_list = string_to_list(config.get(section_name, CONFIG_FILE_LIST_KEY))
    filename_list = _filenames_relative_to(master_config_path, filename_list)

    # Move all the keys from the section_name of the config
    # into the default dictionary of the config,
    # making them a foundational starting point for the layers.
    config.read_dict({config.default_section: config[section_name]})

    # Remove all irrelevant sections from the master config file
    for section in config.sections():
        if section not in MASTER_CONFIG_SECTIONS_TO_KEEP:
            config.remove_section(section)

    for filename in filename_list:
        _must_read(config, filename)

    # The result config is used for environment variable override information
    # so that the environment variable override section can be defined
    # in any of the layers or in the master config file.
    _env_override(config, os.environ)

    return config


def munchify_config(config_parser):
    """
    Create a ``munch`` version of the config_parser's data.

    ``munch`` allows both attribute and item access to it's data.
    See the `munch`_ documentation for details.

    Note: This is a one-time conversion,
    if the ``config_parser`` is subsequently updated,
    the returned ``munch`` will be unaffected.
    """
    from munch import Munch

    result = Munch()

    for section in config_parser.sections() + [config_parser.default_section]:
        intermediate = Munch()
        result[section] = intermediate
        for key, value in config_parser.items(section):
            intermediate[key] = value

    return result
