# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['test_all_supported_http_methods[DELETE] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'DELETE',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test {request.param} with query parameters',
    'input_schema': {
        'properties': {
            'query_query_param': {
                'aliasName': 'query_param',
                'in': 'query',
                'title': 'query_param',
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'query_param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_all_supported_http_methods[GET] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'GET',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test {request.param} with query parameters',
    'input_schema': {
        'properties': {
            'query_query_param': {
                'aliasName': 'query_param',
                'in': 'query',
                'title': 'query_param',
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'query_param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_all_supported_http_methods[POST] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test {request.param} with query parameters',
    'input_schema': {
        'properties': {
            'query_query_param': {
                'aliasName': 'query_param',
                'in': 'query',
                'title': 'query_param',
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'query_param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_all_supported_http_methods[PUT] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'PUT',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test {request.param} with query parameters',
    'input_schema': {
        'properties': {
            'query_query_param': {
                'aliasName': 'query_param',
                'in': 'query',
                'title': 'query_param',
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'query_param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_all_supported_parameter_in_methods_except_body[cookie] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test cookie with query parameters',
    'input_schema': {
        'properties': {
            'cookie_param': {
                'aliasName': 'param',
                'in': 'cookie',
                'title': 'param',
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_all_supported_parameter_in_methods_except_body[header] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test header with query parameters',
    'input_schema': {
        'properties': {
            'header_param': {
                'aliasName': 'param',
                'in': 'header',
                'title': 'param',
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_all_supported_parameter_in_methods_except_body[path] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test/{param}',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test path with query parameters',
    'input_schema': {
        'properties': {
            'path_param': {
                'aliasName': 'param',
                'in': 'path',
                'title': 'param',
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_all_supported_parameter_in_methods_except_body[query] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test query with query parameters',
    'input_schema': {
        'properties': {
            'query_param': {
                'aliasName': 'param',
                'in': 'query',
                'title': 'param',
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_async_spec_with_callback 1'] = {
    'binding': {
        'openapi': {
            'callback': {
                'callback_url': '{$request.header.callbackUrl}',
                'input_schema': {
                    'properties': {
                        '__requestBody__': {
                            'description': 'The html request body used to satisfy this user utterance.',
                            'in': 'body',
                            'properties': {
                                'param': {
                                    'type': 'string'
                                }
                            },
                            'required': [
                                'param'
                            ],
                            'title': 'RequestBody',
                            'type': 'object'
                        }
                    },
                    'required': [
                        '__requestBody__'
                    ],
                    'type': 'object'
                },
                'method': 'POST',
                'output_schema': {
                    'description': 'Success response',
                    'properties': {
                        'status': {
                            'type': 'string'
                        }
                    },
                    'required': [
                    ],
                    'type': 'object'
                }
            },
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test async with callback',
    'input_schema': {
        'properties': {
            '__requestBody__': {
                'description': 'The html request body used to satisfy this user utterance.',
                'in': 'body',
                'properties': {
                    'param': {
                        'type': 'string'
                    }
                },
                'required': [
                    'param'
                ],
                'title': 'RequestBody',
                'type': 'object'
            }
        },
        'required': [
            '__requestBody__'
        ],
        'type': 'object'
    },
    'is_async': True,
    'name': 'testAsyncCallback',
    'output_schema': {
        'description': 'Success response',
        'properties': {
            'status': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_body_parameters 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test requestBody parameters',
    'input_schema': {
        'properties': {
            '__requestBody__': {
                'description': 'The html request body used to satisfy this user utterance.',
                'in': 'body',
                'properties': {
                    'param': {
                        'example': 25,
                        'type': 'number'
                    }
                },
                'required': [
                    'param'
                ],
                'title': 'RequestBody',
                'type': 'object'
            }
        },
        'required': [
            '__requestBody__'
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_global_authentication[openapi_global_authentication0] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test none with query parameters',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_global_authentication[openapi_global_authentication1] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
                {
                    'scheme': 'basic',
                    'type': 'http'
                }
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test basic with query parameters',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_global_authentication[openapi_global_authentication2] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
                {
                    'in': 'header',
                    'name': 'X-API-Key',
                    'type': 'apiKey'
                }
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test apiKey with query parameters',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_global_authentication[openapi_global_authentication3] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
                {
                    'in': 'query',
                    'name': 'X-API-Key',
                    'type': 'apiKey'
                }
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test apiKey with query parameters',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_global_authentication[openapi_global_authentication4] 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test',
            'security': [
                {
                    'in': 'cookie',
                    'name': 'X-API-Key',
                    'type': 'apiKey'
                }
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test apiKey with query parameters',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_http_get_with_api_key_auth 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'GET',
            'http_path': '/test',
            'security': [
                {
                    'scheme': 'basic',
                    'type': 'http'
                },
                {
                    'scheme': 'bearer',
                    'type': 'http'
                },
                {
                    'in': 'header',
                    'name': 'X-API-Key',
                    'type': 'apiKey'
                },
                {
                    'flows': {
                        'authorizationCode': {
                            'authorizationUrl': '/oauth2-provider/auth-code/authorize',
                            'refreshUrl': '/oauth2-provider/auth-code/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/auth-code/token'
                        },
                        'clientCredentials': {
                            'refreshUrl': '/oauth2-provider/client-cred/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/client-cred/token'
                        },
                        'password': {
                            'refreshUrl': '/oauth2-provider/password/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/password/token'
                        },
                        'x-apikey': {
                            'grantType': 'custom_apikey',
                            'refreshUrl': '/oauth2-provider/custom-apikey/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'secretKeys': [
                                'apikey_secret'
                            ],
                            'tokenUrl': '/oauth2-provider/custom-apikey/token'
                        }
                    },
                    'type': 'oauth2'
                }
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'TEST GET',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testGet',
    'output_schema': {
        'description': 'GET response',
        'properties': {
            'status': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_http_get_with_basic_auth 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'GET',
            'http_path': '/test',
            'security': [
                {
                    'scheme': 'basic',
                    'type': 'http'
                },
                {
                    'scheme': 'bearer',
                    'type': 'http'
                },
                {
                    'in': 'header',
                    'name': 'X-API-Key',
                    'type': 'apiKey'
                },
                {
                    'flows': {
                        'authorizationCode': {
                            'authorizationUrl': '/oauth2-provider/auth-code/authorize',
                            'refreshUrl': '/oauth2-provider/auth-code/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/auth-code/token'
                        },
                        'clientCredentials': {
                            'refreshUrl': '/oauth2-provider/client-cred/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/client-cred/token'
                        },
                        'password': {
                            'refreshUrl': '/oauth2-provider/password/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/password/token'
                        },
                        'x-apikey': {
                            'grantType': 'custom_apikey',
                            'refreshUrl': '/oauth2-provider/custom-apikey/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'secretKeys': [
                                'apikey_secret'
                            ],
                            'tokenUrl': '/oauth2-provider/custom-apikey/token'
                        }
                    },
                    'type': 'oauth2'
                }
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'TEST GET',
    'input_schema': {
        'properties': {
        },
        'required': [
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testGet',
    'output_schema': {
        'description': 'GET response',
        'properties': {
            'status': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_http_post_with_header_query_and_path_params 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'POST',
            'http_path': '/test/params/{path_param}',
            'security': [
                {
                    'scheme': 'basic',
                    'type': 'http'
                },
                {
                    'scheme': 'bearer',
                    'type': 'http'
                },
                {
                    'in': 'header',
                    'name': 'X-API-Key',
                    'type': 'apiKey'
                },
                {
                    'flows': {
                        'authorizationCode': {
                            'authorizationUrl': '/oauth2-provider/auth-code/authorize',
                            'refreshUrl': '/oauth2-provider/auth-code/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/auth-code/token'
                        },
                        'clientCredentials': {
                            'refreshUrl': '/oauth2-provider/client-cred/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/client-cred/token'
                        },
                        'password': {
                            'refreshUrl': '/oauth2-provider/password/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/password/token'
                        },
                        'x-apikey': {
                            'grantType': 'custom_apikey',
                            'refreshUrl': '/oauth2-provider/custom-apikey/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'secretKeys': [
                                'apikey_secret'
                            ],
                            'tokenUrl': '/oauth2-provider/custom-apikey/token'
                        }
                    },
                    'type': 'oauth2'
                }
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'Test we handle params  path, query, header',
    'input_schema': {
        'properties': {
            'header_header_param': {
                'aliasName': 'header_param',
                'in': 'header',
                'title': 'header_param',
                'type': 'string'
            },
            'path_path_param': {
                'aliasName': 'path_param',
                'in': 'path',
                'title': 'path_param',
                'type': 'string'
            },
            'query_query_param': {
                'aliasName': 'query_param',
                'in': 'query',
                'title': 'query_param',
                'type': 'string'
            }
        },
        'required': [
            'path_path_param',
            'header_header_param'
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testParams',
    'output_schema': {
        'description': 'echoes back the params values',
        'properties': {
            'header_param': {
                'type': 'string'
            },
            'path_param': {
                'type': 'string'
            },
            'query_param': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}

snapshots['test_http_put_with_json_request_body 1'] = {
    'binding': {
        'openapi': {
            'http_method': 'PUT',
            'http_path': '/test',
            'security': [
                {
                    'scheme': 'basic',
                    'type': 'http'
                },
                {
                    'scheme': 'bearer',
                    'type': 'http'
                },
                {
                    'in': 'header',
                    'name': 'X-API-Key',
                    'type': 'apiKey'
                },
                {
                    'flows': {
                        'authorizationCode': {
                            'authorizationUrl': '/oauth2-provider/auth-code/authorize',
                            'refreshUrl': '/oauth2-provider/auth-code/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/auth-code/token'
                        },
                        'clientCredentials': {
                            'refreshUrl': '/oauth2-provider/client-cred/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/client-cred/token'
                        },
                        'password': {
                            'refreshUrl': '/oauth2-provider/password/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'tokenUrl': '/oauth2-provider/password/token'
                        },
                        'x-apikey': {
                            'grantType': 'custom_apikey',
                            'refreshUrl': '/oauth2-provider/custom-apikey/token',
                            'scopes': {
                                'custom': 'Add your own scope',
                                'read': 'Read access to protected resources'
                            },
                            'secretKeys': [
                                'apikey_secret'
                            ],
                            'tokenUrl': '/oauth2-provider/custom-apikey/token'
                        }
                    },
                    'type': 'oauth2'
                }
            ],
            'servers': [
                'https://{host}:{port}'
            ]
        }
    },
    'description': 'TEST PUT',
    'input_schema': {
        'properties': {
            '__requestBody__': {
                'description': 'The html request body used to satisfy this user utterance.',
                'in': 'body',
                'properties': {
                    'some_content': {
                        'example': '25',
                        'type': 'string'
                    }
                },
                'title': 'RequestBody',
                'type': 'object'
            }
        },
        'required': [
            '__requestBody__'
        ],
        'type': 'object'
    },
    'is_async': False,
    'name': 'testPut',
    'output_schema': {
        'description': 'PUT response',
        'properties': {
            'status': {
                'type': 'string'
            }
        },
        'required': [
        ],
        'type': 'object'
    },
    'permission': 'read_only'
}
