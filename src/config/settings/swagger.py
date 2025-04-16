SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'Enter: "Bearer <JWT Token>" (without quotes)',
        },
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
    'PERSIST_AUTH': True,
}