# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['test_should_allow_naked_decorators 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:my_tool'
        }
    },
    'description': 'The description',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'name': 'my_tool',
    'output_schema': {
    },
    'permission': 'read_only'
}

snapshots['test_should_be_possible_to_override_defaults 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:my_tool'
        }
    },
    'description': 'the description',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'name': 'myName',
    'output_schema': {
    },
    'permission': 'admin'
}

snapshots['test_should_support_pydantic_typed_args 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:sample_tool'
        }
    },
    'description': 'test python description',
    'input_schema': {
        'properties': {
            'b': {
                'properties': {
                    'a': {
                        'title': 'A',
                        'type': 'string'
                    },
                    'b': {
                        'title': 'B',
                        'type': 'string'
                    },
                    'c': {
                        'title': 'C',
                        'type': 'string'
                    },
                    'd': {
                        'properties': {
                            'na': {
                                'title': 'Na',
                                'type': 'integer'
                            }
                        },
                        'required': [
                            'na'
                        ],
                        'title': 'Nested',
                        'type': 'object'
                    },
                    'e': {
                        'properties': {
                            'na': {
                                'title': 'Na',
                                'type': 'integer'
                            }
                        },
                        'required': [
                            'na'
                        ],
                        'title': 'Nested',
                        'type': 'object'
                    },
                    'f': {
                        'properties': {
                            'na': {
                                'title': 'Na',
                                'type': 'integer'
                            }
                        },
                        'required': [
                            'na'
                        ],
                        'title': 'Nested',
                        'type': 'object'
                    }
                },
                'required': [
                    'a',
                    'd'
                ],
                'title': 'SampleParamA',
                'type': 'object'
            },
            'sampleA': {
                'properties': {
                    'a': {
                        'title': 'A',
                        'type': 'string'
                    },
                    'b': {
                        'title': 'B',
                        'type': 'string'
                    },
                    'c': {
                        'title': 'C',
                        'type': 'string'
                    },
                    'd': {
                        'properties': {
                            'na': {
                                'title': 'Na',
                                'type': 'integer'
                            }
                        },
                        'required': [
                            'na'
                        ],
                        'title': 'Nested',
                        'type': 'object'
                    },
                    'e': {
                        'properties': {
                            'na': {
                                'title': 'Na',
                                'type': 'integer'
                            }
                        },
                        'required': [
                            'na'
                        ],
                        'title': 'Nested',
                        'type': 'object'
                    },
                    'f': {
                        'properties': {
                            'na': {
                                'title': 'Na',
                                'type': 'integer'
                            }
                        },
                        'required': [
                            'na'
                        ],
                        'title': 'Nested',
                        'type': 'object'
                    }
                },
                'required': [
                    'a',
                    'd'
                ],
                'title': 'SampleParamA',
                'type': 'object'
            }
        },
        'required': [
            'sampleA'
        ],
        'type': 'object'
    },
    'name': 'sample_tool',
    'output_schema': {
        'properties': {
            'a': {
                'title': 'A',
                'type': 'string'
            },
            'b': {
                'title': 'B',
                'type': 'string'
            },
            'c': {
                'title': 'C',
                'type': 'string'
            },
            'd': {
                'properties': {
                    'na': {
                        'title': 'Na',
                        'type': 'integer'
                    }
                },
                'required': [
                    'na'
                ],
                'title': 'Nested',
                'type': 'object'
            },
            'e': {
                'properties': {
                    'na': {
                        'title': 'Na',
                        'type': 'integer'
                    }
                },
                'required': [
                    'na'
                ],
                'title': 'Nested',
                'type': 'object'
            },
            'f': {
                'properties': {
                    'na': {
                        'title': 'Na',
                        'type': 'integer'
                    }
                },
                'required': [
                    'na'
                ],
                'title': 'Nested',
                'type': 'object'
            }
        },
        'required': [
            'a',
            'd'
        ],
        'title': 'SampleParamA',
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_should_support_typed_none_args 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:my_tool'
        }
    },
    'description': 'the description',
    'input_schema': {
        'properties': {
            'input': {
                'title': 'Input',
                'type': 'null'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'name': 'myName',
    'output_schema': {
        'type': 'null'
    },
    'permission': 'admin'
}

snapshots['test_should_support_typed_optional_args 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:my_tool'
        }
    },
    'description': 'the description',
    'input_schema': {
        'properties': {
            'input': {
                'title': 'Input',
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'name': 'myName',
    'output_schema': {
        'anyOf': [
            {
                'type': 'string'
            },
            {
                'type': 'null'
            }
        ]
    },
    'permission': 'admin'
}

snapshots['test_should_support_typed_typings_inputs_and_outputs 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:my_tool'
        }
    },
    'description': 'the description',
    'input_schema': {
        'properties': {
            'input': {
                'title': 'Input',
                'type': 'string'
            }
        },
        'required': [
            'input'
        ],
        'type': 'object'
    },
    'name': 'myName',
    'output_schema': {
        'type': 'string'
    },
    'permission': 'admin'
}

snapshots['test_should_use_correct_defaults 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:my_tool'
        }
    },
    'description': 'test python description',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'name': 'my_tool',
    'output_schema': {
    },
    'permission': 'read_only'
}

snapshots['test_should_work_with_custom_join_tool 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:sample_tool'
        }
    },
    'description': 'test python description',
    'input_schema': {
        'properties': {
            'messages': {
                'items': {
                    'additionalProperties': True,
                    'type': 'object'
                },
                'title': 'Messages',
                'type': 'array'
            },
            'original_query': {
                'title': 'Original Query',
                'type': 'string'
            },
            'task_results': {
                'additionalProperties': True,
                'title': 'Task Results',
                'type': 'object'
            }
        },
        'required': [
            'original_query',
            'task_results',
            'messages'
        ],
        'type': 'object'
    },
    'name': 'sample_tool',
    'output_schema': {
        'type': 'string'
    },
    'permission': 'read_only'
}

snapshots['test_should_work_with_dicts 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:sample_tool'
        }
    },
    'description': 'test python description',
    'input_schema': {
        'properties': {
            'b': {
                'additionalProperties': {
                    'type': 'string'
                },
                'title': 'B',
                'type': 'object'
            },
            'sampleA': {
                'additionalProperties': {
                    'type': 'string'
                },
                'title': 'Samplea',
                'type': 'object'
            }
        },
        'required': [
            'sampleA'
        ],
        'type': 'object'
    },
    'name': 'sample_tool',
    'output_schema': {
        'items': {
            'additionalProperties': {
                'type': 'string'
            },
            'type': 'object'
        },
        'type': 'array'
    },
    'permission': 'read_only'
}

snapshots['test_should_work_with_lists 1'] = {
    'binding': {
        'python': {
            'function': 'test_python_tool:sample_tool'
        }
    },
    'description': 'test python description',
    'input_schema': {
        'properties': {
            'b': {
                'items': {
                    'type': 'string'
                },
                'title': 'B',
                'type': 'array'
            },
            'sampleA': {
                'items': {
                    'type': 'string'
                },
                'title': 'Samplea',
                'type': 'array'
            }
        },
        'required': [
            'sampleA'
        ],
        'type': 'object'
    },
    'name': 'sample_tool',
    'output_schema': {
        'items': {
            'type': 'string'
        },
        'type': 'array'
    },
    'permission': 'read_only'
}
