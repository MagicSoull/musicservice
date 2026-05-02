GET_ARTIST_SPEC = {
    'summary': 'Get artist name by ID',
    'parameters': [
        {
            'name': 'artist_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': 'ID of the artist'
        }
    ],
    'responses': {
        '200': {'description': 'Artist name returned successfully'},
        '404': {'description': 'Artist not found'}
    }
}

DELETE_ARTIST_SPEC = {
    'summary': 'Delete artist by ID',
    'parameters': [
        {
            'name': 'artist_id',  
            'in': 'path',
            'type': 'integer',     
            'required': True,
            'description': 'ID of the artist to delete'
        }
    ],
    'responses': {
        '200': {'description': 'Artist successfully deleted'},
        '404': {'description': 'Artist not found'},
        '500': {'description': 'Internal server error'}
    }
}

UPDATE_ARTIST_SPEC = {
    'summary': 'Update artist name by ID',
    'parameters': [
        {
            'name': 'artist_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': 'ID of the artist'
        },
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': 'New name of the artist'
                    }
                },
                'required': ['name']
            }
        }
    ],
    'responses': {
        '200': {'description': 'Имя успешно обновлено'},
        '400': {'description': 'Ошибка валидации'},
        '404': {'description': 'Артист не найден'},
        '500': {'description': 'Ошибка сервера'}
    }
}

CREATE_ARTIST_SPEC = {
    'summary': 'Create a new artist',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'name': {
                        'type': 'string',
                        'description': 'Name of the artist',
                        'example': 'The Beatles'
                    },
                    'bio': {
                        'type': 'string',
                        'description': 'Biography of the artist',
                        'example': 'Legendary rock band from Liverpool'
                    },
                    'country': {
                        'type': 'string',
                        'description': 'Country of origin',
                        'example': 'UK'
                    },
                    'user_id': {
                        'type': 'integer',
                        'description': 'ID of the user who created this artist',
                        'example': 1
                    }
                },
                'required': ['name', 'user_id']  # name и user_id обязательны
            }
        }
    ],
    'responses': {
        '201': {'description': 'Artist created successfully'},
        '400': {'description': 'Invalid input data'},
        '500': {'description': 'Internal server error'}
    }
}