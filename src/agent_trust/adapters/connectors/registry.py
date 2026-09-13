"""Explicit in-process registry. No dynamic imports/plugins or response dispatch."""
from .falcon_source import CrowdStrikeSource
from .json_source import GenericJSONSource
from .webhook import WebhookDestination

SOURCES = {'generic-json':GenericJSONSource, 'crowdstrike-falcon':CrowdStrikeSource}
DESTINATIONS = {'webhook':WebhookDestination}


def destination(name, settings):
    if name not in DESTINATIONS:
        raise ValueError('unregistered_destination')
    return DESTINATIONS[name](settings)
