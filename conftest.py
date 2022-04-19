# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Configuration file for Pytest

NOTE: DO NOT add fixtures here. It could generate problems with
      QtAwesome being called before a QApplication is created.
"""

import os
import os.path as osp

# ---- To activate/deactivate certain things for pytest's only
# NOTE: Please leave this before any other import here!!
os.environ['SPYDER_PYTEST'] = 'True'

# ---- Update PyLSP
# When running in CI, subrepos are installed in the env.
if not os.environ.get('CI'):
    from install_dev_repos import REPOS, install_repo
    if REPOS['python-lsp-server']['editable']:
        # Installed in editable mode -> reinstall
        install_repo('python-lsp-server', editable=True)

# ---- Pytest adjustments
import pytest


def pytest_addoption(parser):
    """Add option to run slow tests."""
    parser.addoption("--run-slow", action="store_true",
                     default=False, help="Run slow tests")


def get_passed_tests():
    """
    Get the list of passed tests by inspecting the log generated by pytest.

    This is useful on CIs to restart the test suite from the point where a
    segfault was thrown by it.
    """
    # This assumes the pytest log is placed next to this file. That's where
    # we put it on CIs.
    if osp.isfile('pytest_log.txt'):
        with open('pytest_log.txt') as f:
            logfile = f.readlines()

        # All lines that start with 'spyder' are tests. The rest are
        # informative messages.
        tests = []
        for line in logfile:
            if line.startswith('spyder'):
                tests.append(line.split()[0])

        # Don't include the last test to repeat it again.
        return tests[:-1]
    else:
        return []


def pytest_collection_modifyitems(config, items):
    """
    Decide what tests to run (slow or fast) according to the --run-slow
    option.
    """
    passed_tests = get_passed_tests()
    slow_option = config.getoption("--run-slow")
    skip_slow = pytest.mark.skip(reason="Need --run-slow option to run")
    skip_fast = pytest.mark.skip(reason="Don't need --run-slow option to run")
    skip_passed = pytest.mark.skip(reason="Test passed in previous runs")

    for item in items:
        if item.nodeid in passed_tests:
            item.add_marker(skip_passed)
        elif slow_option:
            if "slow" not in item.keywords:
                item.add_marker(skip_fast)
        else:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


@pytest.fixture(autouse=True)
def reset_conf_before_test():
    from spyder.config.manager import CONF
    CONF.reset_to_defaults(notification=False)

    from spyder.plugins.completion.api import COMPLETION_ENTRYPOINT
    from spyder.plugins.completion.plugin import CompletionPlugin

    # Restore completion clients default settings, since they
    # don't have default values on the configuration.
    from pkg_resources import iter_entry_points

    provider_configurations = {}
    for entry_point in iter_entry_points(COMPLETION_ENTRYPOINT):
        Provider = entry_point.resolve()
        provider_name = Provider.COMPLETION_PROVIDER_NAME

        (provider_conf_version,
         current_conf_values,
         provider_defaults) = CompletionPlugin._merge_default_configurations(
            Provider, provider_name, provider_configurations)

        new_provider_config = {
            'version': provider_conf_version,
            'values': current_conf_values,
            'defaults': provider_defaults
        }
        provider_configurations[provider_name] = new_provider_config

    CONF.set('completions', 'provider_configuration', provider_configurations,
             notification=False)
