# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestObservabilityConfiguration.test_configure_should_show_warning_if_project_id_missing 1'] = {
    'api_key': 'api_key',
    'config_json': {
    },
    'host_health_uri': 'https://cloud.langfuse.com//api/public/otel',
    'host_uri': 'https://cloud.langfuse.com',
    'mask_pii': False,
    'project_id': 'default',
    'tool_identifier': 'langfuse'
}

snapshots['TestObservabilityConfiguration.test_configure_should_update_langfuse_with_config_file 1'] = {
    'api_key': 'sk-lf-00000-00000-00000-00000-00000',
    'config_json': {
        'public_key': 'pk-lf-00000-00000-00000-00000-00000'
    },
    'host_health_uri': 'https://cloud.langfuse.com',
    'host_uri': 'https://cloud.langfuse.com//api/public/otel',
    'mask_pii': True,
    'project_id': 'default',
    'tool_identifier': 'langfuse'
}

snapshots['TestObservabilityConfiguration.test_configure_should_update_langfuse_with_config_file_mixed 1'] = {
    'api_key': 'api_key',
    'config_json': {
    },
    'host_health_uri': 'https://cloud.langfuse.com//api/public/otel',
    'host_uri': 'https://cloud.langfuse.com',
    'mask_pii': False,
    'project_id': 'projectId',
    'tool_identifier': 'langfuse'
}

snapshots['TestObservabilityConfiguration.test_configure_should_update_langfuse_without_config_file 1'] = {
    'api_key': 'api_key',
    'config_json': {
    },
    'host_health_uri': 'https://cloud.langfuse.com//api/public/otel',
    'host_uri': 'https://cloud.langfuse.com',
    'mask_pii': True,
    'project_id': 'projectId',
    'tool_identifier': 'langfuse'
}

snapshots['TestObservabilityPrintToConsole.test_get_should_output_to_json 1'] = '''{
  "spec_version": "v1",
  "kind": "langfuse",
  "active": true,
  "mask_pii": true,
  "extra": 3
}'''

snapshots['TestObservabilityPrintToConsole.test_get_should_output_to_yaml 1'] = '''spec_version: v1
kind: langfuse
active: true
mask_pii: true
extra: 3
'''

snapshots['TestObservabilityPrintToConsole.test_get_should_print_to_console 1'] = '''spec_version: v1
kind: langfuse
active: true
mask_pii: true

'''

snapshots['TestObservabilityPrintToConsole.test_get_should_print_to_console_with_extras 1'] = '''spec_version: v1
kind: langfuse
active: true
mask_pii: true
extra: 3

'''
