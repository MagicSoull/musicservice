from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'musicdb_secret'

DB_CONFIG = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'postgres',
    'database': 'musicdb'
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# ─────────────────────────────────────────────
# ГЛАВНАЯ
# ─────────────────────────────────────────────
@app.route('/')
def index():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS c FROM artists;")
        artists_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM tracks;")
        tracks_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM albums;")
        albums_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM playlists;")
        playlists_count = cur.fetchone()['c']
        cur.execute("""
            SELECT t.title, a.name AS artist, COUNT(*) AS plays
            FROM listening_history lh
            JOIN tracks t ON lh.track_id = t.tracks_id
            JOIN artists a ON t.artist_id = a.artist_id
            GROUP BY t.title, a.name
            ORDER BY plays DESC LIMIT 5;
        """)
        top_tracks = cur.fetchall()
    conn.close()
    return render_template('index.html',
        artists_count=artists_count,
        tracks_count=tracks_count,
        albums_count=albums_count,
        playlists_count=playlists_count,
        top_tracks=top_tracks
    )

# ─────────────────────────────────────────────
# АРТИСТЫ
# ─────────────────────────────────────────────
@app.route('/artists')
def artists():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT a.artist_id, a.name, a.bio, a.country,
                   COUNT(DISTINCT al.albums_id) AS album_count,
                   COUNT(DISTINCT t.tracks_id) AS track_count
            FROM artists a
            LEFT JOIN albums al ON al.artist_id = a.artist_id
            LEFT JOIN tracks t ON t.artist_id = a.artist_id
            GROUP BY a.artist_id, a.name, a.bio, a.country
            ORDER BY a.name;
        """)
        rows = cur.fetchall()
    conn.close()
    return render_template('artists.html', artists=rows)

@app.route('/artists/<int:artist_id>')
def artist_detail(artist_id):
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM artists WHERE artist_id=%s;", (artist_id,))
        artist = cur.fetchone()
        if not artist:
            conn.close()
            flash('Артист не найден', 'error')
            return redirect(url_for('artists'))
        cur.execute("""
            SELECT al.albums_id, al.title, al.release_date,
                   COUNT(t.tracks_id) AS track_count
            FROM albums al
            LEFT JOIN tracks t ON t.album_id = al.albums_id
            WHERE al.artist_id = %s
            GROUP BY al.albums_id, al.title, al.release_date
            ORDER BY al.release_date DESC;
        """, (artist_id,))
        albums = cur.fetchall()
        cur.execute("""
            SELECT t.tracks_id, t.title, t.duration, g.name AS genre,
                   al.title AS album
            FROM tracks t
            JOIN genres g ON g.genres_id = t.genre_id
            JOIN albums al ON al.albums_id = t.album_id
            WHERE t.artist_id = %s
            ORDER BY al.release_date DESC, t.title;
        """, (artist_id,))
        tracks = cur.fetchall()
    conn.close()
    return render_template('artist_detail.html', artist=artist, albums=albums, tracks=tracks)

@app.route('/artists/new', methods=['GET', 'POST'])
def artist_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        bio = request.form.get('bio', '').strip()
        country = request.form.get('country', '').strip()
        user_id = request.form.get('user_id', '').strip()

        if not name or not country or not user_id:
            flash('Имя, страна и ID пользователя обязательны', 'error')
            return render_template('artist_form.html', action='create', artist=None)

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO artists (name, bio, country, user_id) VALUES (%s,%s,%s,%s);",
                    (name, bio or None, country, int(user_id))
                )
            conn.commit()
            
            
            conn.close()
            flash(f'Артист «{name}» создан', 'success')
            return redirect(url_for('artists'))
        except Exception as e:
            flash(f'Ошибка: {e}', 'error')
    return render_template('artist_form.html', action='create', artist=None)

@app.route('/artists/<int:artist_id>/edit', methods=['GET', 'POST'])
def artist_edit(artist_id):
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM artists WHERE artist_id=%s;", (artist_id,))
        artist = cur.fetchone()
    conn.close()
    if not artist:
        flash('Артист не найден', 'error')
        return redirect(url_for('artists'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        bio = request.form.get('bio', '').strip()
        country = request.form.get('country', '').strip()

        if not name or not country:
            flash('Имя и страна обязательны', 'error')
            return render_template('artist_form.html', action='edit', artist=artist)

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE artists SET name=%s, bio=%s, country=%s WHERE artist_id=%s;",
                    (name, bio or None, country, artist_id)
                )
            conn.commit()
            conn.close()
            flash('Данные артиста обновлены', 'success')
            return redirect(url_for('artist_detail', artist_id=artist_id))
        except Exception as e:
            flash(f'Ошибка: {e}', 'error')
    return render_template('artist_form.html', action='edit', artist=artist)

@app.route('/artists/<int:artist_id>/delete', methods=['POST'])
def artist_delete(artist_id):
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM artists WHERE artist_id=%s;", (artist_id,))
        conn.commit()
        conn.close()
        flash('Артист удалён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    return redirect(url_for('artists'))

# ─────────────────────────────────────────────
# ТРЕКИ
# ─────────────────────────────────────────────
@app.route('/tracks')
def tracks():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT t.tracks_id, t.title, t.duration,
                   a.name AS artist, al.title AS album, g.name AS genre
            FROM tracks t
            JOIN artists a ON a.artist_id = t.artist_id
            JOIN albums al ON al.albums_id = t.album_id
            JOIN genres g ON g.genres_id = t.genre_id
            ORDER BY a.name, al.title, t.title;
        """)
        rows = cur.fetchall()
    conn.close()
    return render_template('tracks.html', tracks=rows)

@app.route('/tracks/new', methods=['GET', 'POST'])
def track_new():
    conn = get_conn()
    album_id = request.args.get('album_id')
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT artist_id, name FROM artists ORDER BY name;")
        artists = cur.fetchall()
        cur.execute("SELECT albums_id, title FROM albums ORDER BY title;")
        albums = cur.fetchall()
        cur.execute("SELECT genres_id, name FROM genres ORDER BY name;")
        genres = cur.fetchall()
    conn.close()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        duration = request.form.get('duration', '').strip()
        album_id = request.form.get('album_id', '').strip()
        artist_id = request.form.get('artist_id', '').strip()
        genre_id = request.form.get('genre_id', '').strip()

        if not all([title, duration, album_id, artist_id, genre_id]):
            flash('Все поля обязательны', 'error')
            return render_template('track_form.html', artists=artists, albums=albums, genres=genres)

        try:
            dur = int(duration)
            if dur <= 60:
                flash('Длительность должна быть больше 60 секунд', 'error')
                return render_template('track_form.html', artists=artists, albums=albums, genres=genres)
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO tracks (title, duration, album_id, artist_id, genre_id)
                       VALUES (%s,%s,%s,%s,%s);""",
                    (title, dur, int(album_id), int(artist_id), int(genre_id))
                )
            conn.commit()
            conn.close()
            flash(f'Трек «{title}» добавлен', 'success')
            return redirect(url_for('tracks'))
        except Exception as e:
            flash(f'Ошибка: {e}', 'error')

    return render_template('track_form.html', artists=artists, albums=albums, genres=genres, album_id=album_id)

@app.route('/tracks/<int:track_id>/delete', methods=['POST'])
def track_delete(track_id):
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tracks WHERE tracks_id=%s;", (track_id,))
        conn.commit()
        conn.close()
        flash('Трек удалён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    return redirect(url_for('tracks'))

# ─────────────────────────────────────────────
# АЛЬБОМЫ
# ─────────────────────────────────────────────
@app.route('/albums')
def albums():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT al.albums_id, al.title, al.release_date,
                   a.name AS artist, COUNT(t.tracks_id) AS track_count
            FROM albums al
            JOIN artists a ON a.artist_id = al.artist_id
            LEFT JOIN tracks t ON t.album_id = al.albums_id
            GROUP BY al.albums_id, al.title, al.release_date, a.name
            ORDER BY al.release_date DESC;
        """)
        rows = cur.fetchall()
    conn.close()
    return render_template('albums.html', albums=rows)

@app.route('/albums/new', methods=['GET', 'POST'])
def album_new():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT artist_id, name FROM artists ORDER BY name;")
        artists = cur.fetchall()
    conn.close()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        release_date = request.form.get('release_date', '').strip()
        artist_id = request.form.get('artist_id', '').strip()

        if not all([title, artist_id]):
            flash('Название и артист обязательны', 'error')
            return render_template('album_form.html', artists=artists)

        try:
            conn = get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO albums (title, release_date, artist_id) VALUES (%s,%s,%s);",
                    (title, release_date or None, int(artist_id))
                )
            conn.commit()
            conn.close()
            flash(f'Альбом «{title}» создан', 'success')
            return redirect(url_for('albums'))
        except Exception as e:
            flash(f'Ошибка: {e}', 'error')

    return render_template('album_form.html', artists=artists)

@app.route('/albums/<int:album_id>/delete', methods=['POST'])
def album_delete(album_id):
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM albums WHERE albums_id=%s;", (album_id,))
        conn.commit()
        conn.close()
        flash('Альбом удалён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    return redirect(url_for('albums'))

# ─────────────────────────────────────────────
# ПЛЕЙЛИСТЫ
# ─────────────────────────────────────────────
@app.route('/playlists')
def playlists():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT p.playlist_id, p.name, u.username,
                   COUNT(pt.track_id) AS track_count,
                   p.created_at
            FROM playlists p
            JOIN users u ON u.user_id = p.user_id
            LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.playlist_id
            GROUP BY p.playlist_id, p.name, u.username, p.created_at
            ORDER BY p.created_at DESC;
        """)
        rows = cur.fetchall()
    conn.close()
    return render_template('playlists.html', playlists=rows)

@app.route('/playlists/<int:playlist_id>')
def playlist_detail(playlist_id):
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT p.*, u.username FROM playlists p
            JOIN users u ON u.user_id = p.user_id
            WHERE p.playlist_id=%s;
        """, (playlist_id,))
        playlist = cur.fetchone()
        if not playlist:
            conn.close()
            flash('Плейлист не найден', 'error')
            return redirect(url_for('playlists'))
        cur.execute("""
            SELECT t.tracks_id, t.title, t.duration,
                   a.name AS artist, g.name AS genre,
                   pt.playlist_track_id
            FROM playlist_tracks pt
            JOIN tracks t ON t.tracks_id = pt.track_id
            JOIN artists a ON a.artist_id = t.artist_id
            JOIN genres g ON g.genres_id = t.genre_id
            WHERE pt.playlist_id = %s
            ORDER BY pt.added_at;
        """, (playlist_id,))
        tracks = cur.fetchall()
        cur.execute("""
            SELECT t.tracks_id, t.title, a.name AS artist
            FROM tracks t
            JOIN artists a ON a.artist_id = t.artist_id
            WHERE t.tracks_id NOT IN (
                SELECT track_id FROM playlist_tracks WHERE playlist_id=%s
            )
            ORDER BY a.name, t.title;
        """, (playlist_id,))
        available_tracks = cur.fetchall()
    conn.close()
    return render_template('playlist_detail.html',
        playlist=playlist, tracks=tracks, available_tracks=available_tracks)

@app.route('/playlists/new', methods=['GET', 'POST'])
def playlist_new():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT user_id, username FROM users ORDER BY username;")
        users = cur.fetchall()
    conn.close()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        user_id = request.form.get('user_id', '').strip()

        if not name or not user_id:
            flash('Название и пользователь обязательны', 'error')
            return render_template('playlist_form.html', users=users)

        try:
            conn = get_conn()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO playlists (name, user_id) VALUES (%s,%s) RETURNING playlist_id;",
                    (name, int(user_id))
                )
                new_id = cur.fetchone()['playlist_id']
            conn.commit()
            conn.close()
            flash(f'Плейлист «{name}» создан', 'success')
            return redirect(url_for('playlist_detail', playlist_id=new_id))
        except Exception as e:
            flash(f'Ошибка: {e}', 'error')

    return render_template('playlist_form.html', users=users)

@app.route('/playlists/<int:playlist_id>/add_track', methods=['POST'])
def playlist_add_track(playlist_id):
    track_id = request.form.get('track_id')
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO playlist_tracks (playlist_id, track_id) VALUES (%s,%s);",
                (playlist_id, int(track_id))
            )
        conn.commit()
        conn.close()
        flash('Трек добавлен в плейлист', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    return redirect(url_for('playlist_detail', playlist_id=playlist_id))

@app.route('/playlists/<int:playlist_id>/remove_track/<int:pt_id>', methods=['POST'])
def playlist_remove_track(playlist_id, pt_id):
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM playlist_tracks WHERE playlist_track_id=%s;", (pt_id,))
        conn.commit()
        conn.close()
        flash('Трек удалён из плейлиста', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    return redirect(url_for('playlist_detail', playlist_id=playlist_id))

@app.route('/playlists/<int:playlist_id>/delete', methods=['POST'])
def playlist_delete(playlist_id):
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM playlists WHERE playlist_id=%s;", (playlist_id,))
        conn.commit()
        conn.close()
        flash('Плейлист удалён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    return redirect(url_for('playlists'))


# ─────────────────────────────────────────────
# ПОЛЬЗОВАТЕЛИ
# ─────────────────────────────────────────────
@app.route('/users')
def users():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT u.user_id, u.username, u.email, u.created_at,
                   STRING_AGG(r.name, ', ' ORDER BY r.name) AS roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.user_id
            LEFT JOIN roles r ON r.role_id = ur.role_id
            GROUP BY u.user_id, u.username, u.email, u.created_at
            ORDER BY u.created_at DESC;
        """)
        rows = cur.fetchall()
    conn.close()
    return render_template('users.html', users=rows)

@app.route('/users/new', methods=['GET', 'POST'])
def user_new():
    conn = get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT role_id, name FROM roles ORDER BY role_id;")
        roles = cur.fetchall()
    conn.close()

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role_id  = request.form.get('role_id', '').strip()
        country  = request.form.get('country', '').strip()
        bio      = request.form.get('bio', '').strip()

        if not all([username, email, password, role_id]):
            flash('Все поля обязательны', 'error')
            return render_template('user_form.html', roles=roles)
        if len(username) > 20:
            flash('Имя пользователя не более 20 символов', 'error')
            return render_template('user_form.html', roles=roles)
        if len(email) > 30:
            flash('Email не более 30 символов', 'error')
            return render_template('user_form.html', roles=roles)

        try:
            conn = get_conn()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """INSERT INTO users (username, email, password)
                       VALUES (%s, %s, %s) RETURNING user_id;""",
                    (username, email, password)
                )
                new_id = cur.fetchone()['user_id']
                cur.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s);",
                    (new_id, int(role_id))
                )
                if int(role_id) == 2:
                    cur.execute(
                        "INSERT INTO artists (name, bio, country, user_id) VALUES (%s, %s, %s, %s);",
                        (username, bio, country or 'Не указана', new_id)
                    )
            conn.commit()
            conn.close()
            flash(f'Пользователь «{username}» создан', 'success')
            return redirect(url_for('users'))
        except Exception as e:
            conn.rollback()
            flash(f'Ошибка: {e}', 'error')

    return render_template('user_form.html', roles=roles)

@app.route('/users/<int:user_id>/delete', methods=['POST'])
def user_delete(user_id):
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id=%s;", (user_id,))
        conn.commit()
        conn.close()
        flash('Пользователь удалён', 'success')
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
    return redirect(url_for('users'))

@app.route("/albums/<int:albums_id>", methods=["GET"])
def det_albums(albums_id):
    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT title, release_date FROM albums WHERE albums_id = %s;",
                (albums_id,)
            )
            album = cur.fetchone()
            cur.execute("""
                SELECT t.tracks_id, t.title, t.duration,
                       a.name AS artist, g.name AS genre
                FROM tracks t
                JOIN artists a ON a.artist_id = t.artist_id
                JOIN genres g ON g.genres_id = t.genre_id
                WHERE t.album_id = %s
                ORDER BY t.title;
            """, (albums_id,))
            tracks = cur.fetchall()
    except Exception as e:
        flash(f'Ошибка: {e}', 'error')
        album = None
        tracks = []
    finally:
        conn.close()
    return render_template('album_detail.html', album=album, tracks=tracks)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
