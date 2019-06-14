"""Unit tests for the qecommon_tools config_cake module."""

from configparser import NoSectionError
from uuid import uuid4
from os import path

import pytest
from layered_config import load_cake, munchify_config


# Some simple configuration files.
# Note: ConfigParser itself is not being tested, just config_cake's use of it.

# Note: For simplicity, all the config files are in the same directory
#       as the master config file; we are testing that the relative
#       lookup is working because the config files are created in a temporary
#       directory that is not the current working directory.

MASTER_CONFIG_SIGNATURE = "# master"
# Testing note: The master config file can have any name, our test code
#               finds it by looking for a file that starts with MASTER_CONFIG_SIGNATURE

test_configs = {
    "basic.config": """
[DEFAULT]
key=with default section value

[Foundation]
key1=key1 from basic configuration
key2=key2 from basic configuration
""",
    "layer1.config": """
[Foundation]
key2=key2 from layer1 configuration

[New Stuff]
new key=new key from layer1 configuration
new key3=new key3 from layer1 configuration
""",
    "layer2.config": """
[Foundation]
key1=key1 from layer2 configuration

[New Stuff]
new key=new key from layer2 configuration
new key2=new key2 from layer2 configuration
""",
    "cake.config": f"""{MASTER_CONFIG_SIGNATURE}
# NOTE: For testing purposes, the non-erroring Cake sections
#       should define a name key. The value of the name key is arbitrary but
#       should contain the name of the cake itself somewhere.

[ENVIRONMENT VARIABLE OVERRIDE INFO]
prefix = CONFIG
separator = +

[DEFAULT]
common = basic.config

[L1]
layers = %(common)s, layer1.config
name=I am the cake who says Ni! L1

[L2]
layers = %(common)s, layer2.config
name=Names are hard. L2

[L1L2]
layers = %(common)s, layer1.config, layer2.config
name=I'm not sure who I am L1L2

[Nonexistant File]
layers = no_such.config, layer1.config

[Expanduser Nonexistant File]
layers = ~/no_such_{uuid4()}.config, %(common)s
""",
    "master_without_env_override_section.config": """
[L3]
layers = layer_with_env_override.config
""",
    "layer_with_env_override.config": """
[ENVIRONMENT VARIABLE OVERRIDE INFO]
prefix = FROM_LAYER
separator = ~

[section_1]
key1=key1 from layer with env override section
""",
}


# Valid means that these config cakes are expected to load correctly:
VALID_CAKE_NAMES = ["L1", "L2", "L1L2"]


@pytest.fixture(scope="session")
def sample_configs(tmp_path_factory):
    """Create sample configs and return the filename of the master config file."""

    base_dir = tmp_path_factory.mktemp("qe_config_tests")

    result = None
    for config_name, contents in test_configs.items():
        filename = str(base_dir.joinpath(config_name))  # str needed for py2.7
        with open(filename, "w") as f:
            f.write(contents)
        if contents.startswith(MASTER_CONFIG_SIGNATURE):
            result = filename
    return result


def test_fail_to_load_non_existant_config(sample_configs):
    with pytest.raises(NoSectionError):
        load_cake(sample_configs, str(uuid4()))


@pytest.mark.parametrize("config_name", VALID_CAKE_NAMES)
def test_load_config_relative_filenames(sample_configs, config_name):
    # This is so simple because sample_configs is already creating the configs
    # in a temporary directory, not the current working directory.
    config = load_cake(sample_configs, config_name)
    assert config is not None
    assert config.sections(), "Config data should have been loaded"


@pytest.mark.parametrize("config_name", VALID_CAKE_NAMES)
def test_config_ordering(sample_configs, config_name):
    """Test that  config files were loaded in the expected order."""

    config = load_cake(sample_configs, config_name)

    key1 = "layer2" if "L2" in config_name else "basic"
    target = "key1 from {} configuration".format(key1)
    assert target == config.get("Foundation", "key1")

    new_key = "layer2" if "L2" in config_name else "layer1"
    target = "new key from {} configuration".format(new_key)
    assert target == config.get("New Stuff", "new key")


def test_env_var_can_override_config_value(sample_configs, monkeypatch):
    new_value = "key1 from environment override"
    monkeypatch.setenv("CONFIG+Foundation+key1", new_value)
    config = load_cake(sample_configs, "L1")
    assert config.get("Foundation", "key1") == new_value


def test_env_var_override_section_can_be_defined_in_a_layer(
    sample_configs, monkeypatch
):
    master = path.join(
        path.dirname(sample_configs), "master_without_env_override_section.config"
    )
    new_value = "key1 from environment override"
    monkeypatch.setenv("FROM_LAYER~section_1~key1", new_value)
    config = load_cake(master, "L3")
    assert config.get("section_1", "key1") == new_value


def test_env_var_can_define_new_section(sample_configs, monkeypatch):
    new_section = str(uuid4())
    new_key = str(uuid4())

    # First test that the section does not exist:
    with pytest.raises(NoSectionError):
        config = load_cake(sample_configs, "L1")
        config.get(new_section, new_key)

    new_value = "from environment creation"
    env_var_name = "CONFIG+{}+{}".format(new_section, new_key)
    monkeypatch.setenv(env_var_name, new_value)
    # Now check that it was created:
    config = load_cake(sample_configs, "L1")
    assert config.get(new_section, new_key) == new_value


def test_broken_config(sample_configs):
    """Ensure expected error when a cake references a non-existant file."""
    with pytest.raises(FileNotFoundError):
        load_cake(sample_configs, "Nonexistant File")


def test_munchifier(sample_configs):
    """Test conversion from config parser to munch."""
    # Munch has it's own tests, we're just spot checking our conversion function.
    config_by_dots = munchify_config(load_cake(sample_configs, "L1"))
    assert config_by_dots.Foundation.key1 == "key1 from basic configuration"
    assert config_by_dots.DEFAULT.key == "with default section value"


def test_custom_config_parser(sample_configs):
    """Test that we can pass in our own config parser."""
    arbitrary_cake_name = "L1"

    # Make sure we are able to load this cake normally first (test self-check)
    load_cake(sample_configs, arbitrary_cake_name)

    # We are not testing ConfigParser itself, just that load_cake will use
    # the object we give it, so we give it something simple that we know
    # will break; we don't care exactly how it breaks, just that it does.
    with pytest.raises(Exception):
        load_cake(sample_configs, arbitrary_cake_name, into_config=object())


def test_expanduser_config_cake_processing(sample_configs):
    # We don't want to write in the test-running-user's home directory
    # so we just check that the expansion has happened.
    home_dir = path.expanduser("~")
    with pytest.raises(FileNotFoundError) as e:
        load_cake(sample_configs, "Expanduser Nonexistant File")
    assert home_dir in str(e.value)


@pytest.mark.parametrize("config_name", VALID_CAKE_NAMES)
def test_load_cake_includes_master_cake_keys_from_cake_section(
    sample_configs, config_name
):
    config = load_cake(sample_configs, config_name)
    assert config_name in config.defaults()["name"]


@pytest.mark.parametrize("cake_name", VALID_CAKE_NAMES)
def test_irrelevant_master_config_sections_are_not_in_config(sample_configs, cake_name):
    config = load_cake(sample_configs, cake_name)
    for cake_name in VALID_CAKE_NAMES:
        assert not config.has_section(cake_name)
