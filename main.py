from flask import Flask, request, jsonify
from flasgger import Swagger, swag_from
from config import host, user, password, db_name
import psycopg2
from psycopg2 import IntegrityError 
from specification import DELETE_ARTIST_SPEC, GET_ARTIST_SPEC, CREATE_ARTIST_SPEC, UPDATE_ARTIST_SPEC

app = Flask(__name__)
swagger = Swagger(app)

def get_connection():
    return psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=db_name
    )

@app.route('/artist/<int:artist_id>', methods=['GET'])
@swag_from(GET_ARTIST_SPEC)
def get_artist_name(artist_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT name, bio FROM artists WHERE artist_id=%s;",
                (artist_id,)
            )
            result = cursor.fetchone()
        
        if result:
            return jsonify({"artist_id": artist_id, "name": result[0], "bio": result[1]}), 200
        return jsonify({"error": f"Артист с ID {artist_id} не найден"}), 404
    finally:
        conn.close()

@app.route('/artist/<int:artist_id>', methods=['PUT'])
@swag_from(UPDATE_ARTIST_SPEC)
def update_artist_name(artist_id):
    
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "В теле запроса обязательно должно быть имя"}), 400
    
    new_name = str(data['name']).strip()
    if not new_name:
        return jsonify({'error': 'Имя не может быть пустым'}), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE artists SET name = %s WHERE artist_id = %s;",
                (new_name, artist_id)
            )
            
            if cursor.rowcount == 0:
                conn.rollback()
                return jsonify({"error": f"Артист с ID {artist_id} не найден"}), 404
            
            conn.commit()
            
        return jsonify({
            "message": "Имя артиста успешно обновлено",
            "artist_id": artist_id,
            "new_name": new_name
        }), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Ошибка базы данных: {str(e)}"}), 500
    finally:
        conn.close()


@app.route('/artist/<int:artist_id>', methods = ['DELETE'])
@swag_from(DELETE_ARTIST_SPEC)
def delete_artist_from_id(artist_id):
    
    conn = get_connection()
    try:
        
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM artists WHERE artist_id =%s;",
                (artist_id,)
            )
        
            if cursor.rowcount == 0:
                conn.rollback()
                return jsonify({"error": f"Артист с ID {artist_id} не найден"}), 404
        
        conn.commit()
        return jsonify({"message": "Артист успешно удален"}), 200
        
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Ошибка базы данных: {str(e)}"}), 500
    finally:
        conn.close()
        
@app.route('/artist', methods=['POST'])
@swag_from(CREATE_ARTIST_SPEC)
def create_artist():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Тело запроса не может быть пустым'}), 400
    
    required_fields = ['name', 'user_id']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"Поле '{field}' обязательно"}), 400
    
    name = str(data['name']).strip()
    bio = str(data.get('bio', '')).strip()
    country = str(data.get('country', '')).strip()
    user_id = int(data['user_id'])
    
    if not name or len(name) > 100:
        return jsonify({'error': 'Некорректное имя артиста'}), 400
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            
            cursor.execute(
                "SELECT artist_id FROM artists WHERE user_id = %s;",
                (user_id,)
            )
            if cursor.fetchone():
                return jsonify({
                    "error": f"У пользователя {user_id} уже есть артист"
                }), 409
                
                
            cursor.execute(
                """INSERT INTO artists (name, bio, country, user_id) 
                   VALUES (%s, %s, %s, %s) 
                   RETURNING artist_id;""",
                (name, bio, country, user_id)
            )
            new_artist_id = cursor.fetchone()[0]
            
        conn.commit()
        return jsonify({
            "message": "Артист успешно создан",
            "artist_id": new_artist_id
        }), 201
        
    except IntegrityError as e:  # ✅ Ловим ошибку уникальности
        conn.rollback()
        
        # Проверяем, какое именно ограничение нарушено
        if 'unique_artist_name' in str(e):
            return jsonify({
                "error": f"Артист с именем '{name}' уже существует",
                "code": "DUPLICATE_NAME"
            }), 409  # 409 Conflict
        
        elif 'unique_artist_name_per_user' in str(e):
            return jsonify({
                "error": f"У вас уже есть артист с именем '{name}'",
                "code": "DUPLICATE_USER_ARTIST"
            }), 409
        
        else:
            return jsonify({
                "error": "Нарушение уникальности данных",
                "code": "INTEGRITY_ERROR"
            }), 400
            
    except Exception as e:
        conn.rollback()
        return jsonify({
            "error": "Внутренняя ошибка сервера",
            "code": "INTERNAL_ERROR"
        }), 500
    finally:
        conn.close()
        
if __name__ == "__main__":
    app.run(debug=True)