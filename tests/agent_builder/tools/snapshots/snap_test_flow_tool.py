# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['test_flow_tool_support_wxo_file_input_output 1'] = {
    'binding': {
        'flow': {
            'flow_id': 'hello-flow-tool',
            'model': {
                'edges': [
                    {
                        'end': 'get_file',
                        'start': '__start__'
                    },
                    {
                        'end': '__end__',
                        'start': 'get_file'
                    }
                ],
                'metadata': {
                },
                'nodes': {
                    '__end__': {
                        'spec': {
                            'display_name': '__end__',
                            'kind': 'end',
                            'name': '__end__'
                        }
                    },
                    '__start__': {
                        'spec': {
                            'display_name': '__start__',
                            'kind': 'start',
                            'name': '__start__'
                        }
                    },
                    'get_file': {
                        'spec': {
                            'description': 'Returns a file url for download.',
                            'display_name': 'get_file',
                            'input_schema': {
                                '$ref': '#/schemas/get_file_input'
                            },
                            'kind': 'tool',
                            'name': 'get_file',
                            'output_schema': {
                                'description': 'A file url for download.',
                                'format': 'wxo-file',
                                'type': 'string'
                            },
                            'tool': 'get_file'
                        }
                    }
                },
                'schemas': {
                    'get_file_input': {
                        'properties': {
                            'file_url': {
                                'description': 'A URL identifying the File to be used.',
                                'format': 'wxo-file',
                                'title': 'File reference',
                                'type': 'string'
                            }
                        },
                        'required': [
                            'file_url'
                        ],
                        'title': 'get_file_input',
                        'type': 'object'
                    },
                    'hello_file_flow_input': {
                        'properties': {
                            'data': {
                                'description': 'A URL identifying the File to be used.',
                                'format': 'wxo-file',
                                'title': 'File reference',
                                'type': 'string'
                            }
                        },
                        'required': [
                        ],
                        'title': 'hello_file_flow_input',
                        'type': 'object'
                    }
                },
                'spec': {
                    'display_name': 'hello_file_flow',
                    'input_schema': {
                        '$ref': '#/schemas/hello_file_flow_input'
                    },
                    'kind': 'flow',
                    'name': 'hello_file_flow',
                    'output_schema': {
                        'description': 'A URL identifying the File to be used.',
                        'format': 'wxo-file',
                        'type': 'string'
                    },
                    'schedulable': False
                }
            }
        }
    },
    'description': 'This is a flow tool to generate hello world with file claim',
    'display_name': 'hello_file_flow',
    'name': 'hello-flow-tool',
    'permission': 'read_only'
}
