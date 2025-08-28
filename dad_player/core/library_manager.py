# dad_player/core/library_manager.py

import logging
import os
import sqlite3
import threading
from pathlib import Path
import mutagen
from mutagen.id3 import APIC, ID3, PictureType
from mutagen.flac import Picture as FLACPicture
from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
import io

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

from dad_player.constants import (
    ALBUM_ART_THUMBNAIL_SIZE, ART_THUMBNAIL_DIR, DATABASE_NAME,
    DB_ALBUMS_TABLE, DB_ARTISTS_TABLE, DB_TRACKS_TABLE,
    SUPPORTED_AUDIO_EXTENSIONS
)
from dad_player.utils.file_utils import (
    get_user_data_dir_for_app, generate_file_hash, sanitize_filename_for_cache
)
from dad_player.core.exceptions import MetadataUpdateError


log = logging.getLogger(__name__)

# =============================================================================
# Helper Functions
# =============================================================================

def _get_tag_values(meta, key_list):
    if not meta:
        return []
    values = []
    for key in key_list:
        try:
            raw_val = meta.get(key)
            if not raw_val:
                continue
            potential_values = raw_val if isinstance(raw_val, list) else [raw_val]
            for item in potential_values:
                if hasattr(item, 'text') and item.text:
                    text_val = item.text if isinstance(item.text, list) else [item.text]
                    values.extend(str(t) for t in text_val)
                elif not hasattr(item, 'text'):
                    values.append(str(item))
        except (KeyError, ValueError):
            continue
    return values

def _safe_convert(value, target_type, split_char=None):
    if not value:
        return None
    try:
        s_val = str(value)
        if split_char:
            s_val = s_val.split(split_char)[0]
        return target_type(s_val)
    except (ValueError, IndexError):
        return None

# =============================================================================
# LibraryManager Class
# =============================================================================

class LibraryManager(EventDispatcher):
    __events__ = ('on_scan_progress', 'on_scan_finished')

    is_scanning = BooleanProperty(False)
    scan_progress_message = StringProperty("")
    progress_value = NumericProperty(0.0)

    def __init__(self, settings_manager, **kwargs):
        super().__init__(**kwargs)
        self.settings_manager = settings_manager
        user_data_dir = Path(get_user_data_dir_for_app())
        self.db_path = user_data_dir / DATABASE_NAME
        self.art_cache_dir = user_data_dir / "cache" / ART_THUMBNAIL_DIR
        self.art_cache_dir.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()
        self._initialize_db()
        self._scan_thread = None
        log.info(f"LibraryManager initialized. Database at: {self.db_path}")

    def _get_db_connection(self):
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            log.error(f"Database connection error: {e}")
            return None

    def _initialize_db(self):
        log.info(f"Initializing database at {self.db_path}...")
        with self._db_lock:
            conn = self._get_db_connection()
            if not conn: return
            try:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute(f"CREATE TABLE IF NOT EXISTS {DB_ARTISTS_TABLE} (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL COLLATE NOCASE)")
                    cursor.execute(f"CREATE TABLE IF NOT EXISTS {DB_ALBUMS_TABLE} (id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE, artist_id INTEGER, art_filename TEXT, year INTEGER, UNIQUE(name, artist_id), FOREIGN KEY (artist_id) REFERENCES {DB_ARTISTS_TABLE}(id) ON DELETE CASCADE)")
                    cursor.execute(f"CREATE TABLE IF NOT EXISTS {DB_TRACKS_TABLE} (id INTEGER PRIMARY KEY, filepath TEXT UNIQUE NOT NULL, filehash TEXT, title TEXT COLLATE NOCASE, album_id INTEGER, artist_id INTEGER, track_number INTEGER, disc_number INTEGER, duration REAL, genre TEXT COLLATE NOCASE, year INTEGER, last_modified REAL, composer TEXT COLLATE NOCASE, bpm REAL, comment TEXT, bitrate INTEGER, samplerate INTEGER, lyrics TEXT, publisher TEXT COLLATE NOCASE, copyright TEXT COLLATE NOCASE, FOREIGN KEY (album_id) REFERENCES {DB_ALBUMS_TABLE}(id) ON DELETE SET NULL, FOREIGN KEY (artist_id) REFERENCES {DB_ARTISTS_TABLE}(id) ON DELETE SET NULL)")
                    cursor.execute(f"PRAGMA table_info({DB_TRACKS_TABLE})")
                    existing_columns = {row['name'] for row in cursor.fetchall()}
                    
                    new_columns = {
                        'composer': 'TEXT COLLATE NOCASE',
                        'bpm': 'REAL',
                        'comment': 'TEXT',
                        'bitrate': 'INTEGER',
                        'samplerate': 'INTEGER',
                        'lyrics': 'TEXT',
                        'publisher': 'TEXT COLLATE NOCASE',
                        'copyright': 'TEXT COLLATE NOCASE'
                    }
                    
                    for col, col_type in new_columns.items():
                        if col not in existing_columns:
                            cursor.execute(f"ALTER TABLE {DB_TRACKS_TABLE} ADD COLUMN {col} {col_type}")
                    
                    log.info("Database tables created/verified and migrated.")
            except sqlite3.Error as e:
                log.error(f"Database initialization failed: {e}")

    def start_scan_music_library(self, full_rescan=False):
        if self.is_scanning:
            log.warning("Scan already in progress. Ignoring request.")
            return
        self.is_scanning = True
        self._scan_thread = threading.Thread(target=self._scan_music_library, args=(full_rescan,))
        self._scan_thread.daemon = True
        self._scan_thread.start()

    def _scan_music_library(self, full_rescan):
        try:
            log.info("Starting library scan...")
            folders = self.settings_manager.get_music_folders()
            log.info(f"Folders to scan: {folders}")

            if not folders:
                log.warning("No music folders are configured. Scan will not proceed.")
                Clock.schedule_once(lambda dt: self.dispatch('on_scan_finished', "No music folders configured."))
                return

            if full_rescan:
                log.info("Performing full rescan, clearing all entries first.")
                self._clear_database()

            all_files = [p for f in folders if os.path.isdir(f) for p in Path(f).rglob('*') if p.is_file()]
            total_files = len(all_files)
            log.info(f"Found {total_files} total files to check.")

            if total_files == 0:
                Clock.schedule_once(lambda dt: self.dispatch('on_scan_finished', "No files found in configured folders."))
                return

            processed = 0
            log.info("Starting to process files...")
            for filepath_obj in all_files:
                filepath = str(filepath_obj)
                if filepath.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS):
                    self._process_audio_file(filepath)
                
                processed += 1
                progress = processed / total_files if total_files > 0 else 0
                Clock.schedule_once(lambda dt: self.dispatch('on_scan_progress', progress, f"Scanning: {processed}/{total_files}"))

            self._clean_orphans()

            Clock.schedule_once(lambda dt: self.dispatch('on_scan_finished', "Library scan completed."))
        except Exception as e:
            log.exception("Scan failed with an unexpected error.")
            error_str = str(e)
            Clock.schedule_once(lambda dt: self.dispatch('on_scan_finished', f"Scan failed: {error_str}"))
        finally:
            self.is_scanning = False
            log.info("Scan thread finished.")

    def _process_audio_file(self, filepath):
        try:
            file_hash = generate_file_hash(filepath)
            last_modified = os.path.getmtime(filepath)
            
            with self._db_lock, self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT filehash, last_modified FROM {DB_TRACKS_TABLE} WHERE filepath = ?", (filepath,))
                row = cursor.fetchone()
                if row and row['filehash'] == file_hash and row['last_modified'] == last_modified:
                    return
                
                try:
                    meta = mutagen.File(filepath, easy=False)
                    if meta is None:
                        log.warning(f"SKIPPED: Could not load metadata for: {os.path.basename(filepath)}")
                        return
                except Exception as e:
                    log.warning(f"SKIPPED: Failed to read metadata for {os.path.basename(filepath)} due to error: {e}")
                    return
                
                self._update_track_in_db(conn, filepath, meta, file_hash, last_modified)
                conn.commit()
                log.info(f"ADDED/UPDATED: {os.path.basename(filepath)}")

        except Exception:
            log.exception(f"FAILED: Unexpected error processing file {os.path.basename(filepath)}")

    def _update_track_in_db(self, conn, filepath, meta, file_hash, last_modified):
        titles = _get_tag_values(meta, ['TIT2', 'title', '©nam'])
        title = titles[0] if titles else Path(filepath).stem

        albums = _get_tag_values(meta, ['TALB', 'album', '©alb'])
        album_name = albums[0] if albums else 'Unknown Album'

        track_artists = _get_tag_values(meta, ['TPE1', 'artist', '©ART'])
        track_artist_name = ', '.join(track_artists) if track_artists else 'Unknown Artist'

        album_artists = _get_tag_values(meta, ['TPE2', 'albumartist', 'aART'])
        album_artist_name = ', '.join(album_artists) if album_artists else track_artist_name

        composers = _get_tag_values(meta, ['TCOM', 'composer', '©wrt'])
        composer = ', '.join(composers) if composers else None

        bpm_vals = _get_tag_values(meta, ['TBPM', 'bpm'])
        bpm = _safe_convert(bpm_vals[0] if bpm_vals else None, float)

        comment_vals = _get_tag_values(meta, ['COMM', 'comment', '©cmt'])
        comment = '\n'.join(comment_vals) if comment_vals else None

        lyrics_vals = _get_tag_values(meta, ['USLT', 'lyrics', '©lyr'])
        lyrics = '\n'.join(lyrics_vals) if lyrics_vals else None

        publisher_vals = _get_tag_values(meta, ['TPUB', 'publisher'])
        publisher = ', '.join(publisher_vals) if publisher_vals else None

        copyright_vals = _get_tag_values(meta, ['TCOP', 'copyright', 'cprt'])
        copyright = ', '.join(copyright_vals) if copyright_vals else None

        years = _get_tag_values(meta, ['TYER', 'TDAT', 'TDRC', 'date', '©day'])
        year = _safe_convert(years[0][:4] if years and years[0] else None, int)

        genres = _get_tag_values(meta, ['TCON', 'genre', '©gen'])
        genre = genres[0] if genres else None

        track_numbers = _get_tag_values(meta, ['TRCK', 'tracknumber', '©trk'])
        track_number = _safe_convert(track_numbers[0] if track_numbers else None, int, split_char='/')

        disc_numbers = _get_tag_values(meta, ['TPOS', 'discnumber', '©dsk'])
        disc_number = _safe_convert(disc_numbers[0] if disc_numbers else None, int, split_char='/')

        duration = meta.info.length if hasattr(meta.info, 'length') else 0

        bitrate = int(meta.info.bitrate / 1000) if hasattr(meta.info, 'bitrate') and meta.info.bitrate else None

        samplerate = int(meta.info.sample_rate) if hasattr(meta.info, 'sample_rate') and meta.info.sample_rate else None

        album_artist_id = self._get_or_create_artist(conn, album_artist_name) if album_artist_name else None
        track_artist_id = self._get_or_create_artist(conn, track_artist_name) if track_artist_name else None

        album_id = self._get_or_create_album(conn, album_name, album_artist_id, year=year)

        art_filename = None
        pictures = None
        if hasattr(meta, 'pictures') and meta.pictures:
            pictures = meta.pictures
        elif 'APIC:' in meta:
            pictures = [meta['APIC:']]
        elif meta.tags and any(key.startswith('covr') for key in meta.tags):
            pictures = [meta.tags.get('covr')[0]]

        if pictures:
            pic = pictures[0]
            art_data = pic.data if hasattr(pic, 'data') else bytes(pic)
            art_filename = self._extract_and_save_album_art(filepath, art_data, album_name, album_artist_name)
            if art_filename:
                cursor = conn.cursor()
                cursor.execute(f"UPDATE {DB_ALBUMS_TABLE} SET art_filename = COALESCE(art_filename, ?) WHERE id = ?", (art_filename, album_id))

        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT OR REPLACE INTO {DB_TRACKS_TABLE}
            (filepath, filehash, title, album_id, artist_id, track_number, disc_number, duration, genre, year, last_modified, composer, bpm, comment, bitrate, samplerate, lyrics, publisher, copyright)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (filepath, file_hash, title, album_id, track_artist_id, track_number, disc_number, duration, genre, year, last_modified, composer, bpm, comment, bitrate, samplerate, lyrics, publisher, copyright))

    def _get_or_create_artist(self, conn, name):
        if not name:
            return None
        cursor = conn.cursor()
        cursor.execute(f"SELECT id FROM {DB_ARTISTS_TABLE} WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            return row['id']
        cursor.execute(f"INSERT INTO {DB_ARTISTS_TABLE} (name) VALUES (?)", (name,))
        return cursor.lastrowid

    def _get_or_create_album(self, conn, name, artist_id, art_filename=None, year=None):
        cursor = conn.cursor()
        if artist_id is None:
            cursor.execute(f"SELECT id FROM {DB_ALBUMS_TABLE} WHERE name = ? AND artist_id IS NULL", (name,))
        else:
            cursor.execute(f"SELECT id FROM {DB_ALBUMS_TABLE} WHERE name = ? AND artist_id = ?", (name, artist_id))
        row = cursor.fetchone()
        if row:
            album_id = row['id']
            if art_filename:
                cursor.execute(f"UPDATE {DB_ALBUMS_TABLE} SET art_filename = COALESCE(art_filename, ?) WHERE id = ?", (art_filename, album_id))
            if year is not None:
                cursor.execute(f"UPDATE {DB_ALBUMS_TABLE} SET year = COALESCE(year, ?) WHERE id = ?", (year, album_id))
            return album_id
        cursor.execute(f"INSERT INTO {DB_ALBUMS_TABLE} (name, artist_id, art_filename, year) VALUES (?, ?, ?, ?)", (name, artist_id, art_filename, year))
        return cursor.lastrowid

    def _extract_and_save_album_art(self, filepath, art_data, album_name, artist_name):
        if PILImage is None:
            log.warning("PIL not available, skipping album art extraction.")
            return None
        try:
            with io.BytesIO(art_data) as img_io:
                img = PILImage.open(img_io)
                if isinstance(ALBUM_ART_THUMBNAIL_SIZE, int):
                    thumbnail_size = (ALBUM_ART_THUMBNAIL_SIZE, ALBUM_ART_THUMBNAIL_SIZE)
                else:
                    thumbnail_size = ALBUM_ART_THUMBNAIL_SIZE
                img.thumbnail(thumbnail_size, PILImage.LANCZOS)
                thumbnail_stream = io.BytesIO()
                img.save(thumbnail_stream, format='JPEG', quality=85)
                thumbnail_stream.seek(0)

            filename = sanitize_filename_for_cache(f"{artist_name}_{album_name}.jpg")
            art_path = self.art_cache_dir / filename
            
            with open(art_path, 'wb') as f:
                f.write(thumbnail_stream.read())

            if os.path.exists(art_path):
                return filename
            else:
                log.error(f"FAILURE: Thumbnail file was NOT created at {art_path}.")
                return None
        except Exception as e:
            log.error(f"Pillow failed to process album art for {os.path.basename(filepath)}: {e}", exc_info=True)
            return None

    def _clear_obsolete_entries(self, current_folders):
        if not current_folders:
            return
        with self._db_lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            patterns = [f + os.path.sep + '%' for f in current_folders]
            condition = " AND ".join(["filepath NOT LIKE ?"] * len(patterns))
            cursor.execute(f"DELETE FROM {DB_TRACKS_TABLE} WHERE {condition}", tuple(patterns))
            conn.execute(f"DELETE FROM {DB_ALBUMS_TABLE} WHERE id NOT IN (SELECT DISTINCT album_id FROM {DB_TRACKS_TABLE} WHERE album_id IS NOT NULL)")
            conn.execute(f"DELETE FROM {DB_ARTISTS_TABLE} WHERE id NOT IN (SELECT DISTINCT artist_id FROM {DB_TRACKS_TABLE} WHERE artist_id IS NOT NULL) AND id NOT IN (SELECT DISTINCT artist_id FROM {DB_ALBUMS_TABLE} WHERE artist_id IS NOT NULL)")
            conn.commit()

    def _clear_database(self):
        with self._db_lock, self._get_db_connection() as conn:
            conn.execute(f"DELETE FROM {DB_TRACKS_TABLE}")
            conn.execute(f"DELETE FROM {DB_ALBUMS_TABLE}")
            conn.execute(f"DELETE FROM {DB_ARTISTS_TABLE}")
            conn.commit()
        log.info("Database cleared for full rescan.")

    def _clean_orphans(self):
        with self._db_lock, self._get_db_connection() as conn:
            conn.execute(f"DELETE FROM {DB_ALBUMS_TABLE} WHERE id NOT IN (SELECT DISTINCT album_id FROM {DB_TRACKS_TABLE} WHERE album_id IS NOT NULL)")
            conn.execute(f"DELETE FROM {DB_ARTISTS_TABLE} WHERE id NOT IN (SELECT DISTINCT artist_id FROM {DB_TRACKS_TABLE} WHERE artist_id IS NOT NULL) AND id NOT IN (SELECT DISTINCT artist_id FROM {DB_ALBUMS_TABLE} WHERE artist_id IS NOT NULL)")
            conn.commit()
        log.info("Cleaned orphan albums and artists.")

    def stop_scan(self):
        if self._scan_thread and self._scan_thread.is_alive():
            log.warning("Scan thread stop requested, but threading doesn't support forced stop. Waiting for completion.")
        self.is_scanning = False

    def get_all_artists(self):
        with self._db_lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM artists ORDER BY name COLLATE NOCASE")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_albums(self, consolidated=False):
        with self._db_lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            if not consolidated:
                cursor.execute("""
                    SELECT al.id, al.name, al.year, al.art_filename, ar.name as artist_name
                    FROM albums al LEFT JOIN artists ar ON al.artist_id = ar.id
                    ORDER BY al.name COLLATE NOCASE
                """)
            else:
                cursor.execute("""
                    SELECT
                        MIN(al.id) as id,
                        al.name,
                        MAX(al.year) as year,
                        (SELECT art_filename FROM albums WHERE name = al.name AND art_filename IS NOT NULL LIMIT 1) as art_filename,
                        CASE
                            WHEN COUNT(DISTINCT al.artist_id) > 1 THEN 'Various Artists'
                            ELSE MAX(ar.name)
                        END as artist_name
                    FROM albums al
                    LEFT JOIN artists ar ON al.artist_id = ar.id
                    GROUP BY al.name COLLATE NOCASE
                    ORDER BY al.name COLLATE NOCASE
                """)
            
            albums = []
            for row in cursor.fetchall():
                art_path = self.art_cache_dir / row["art_filename"] if row["art_filename"] else None
                albums.append({
                    "id": row["id"], "name": row["name"], "year": row["year"],
                    "artist_name": row["artist_name"] or "Unknown Artist",
                    "art_path": str(art_path) if art_path and art_path.exists() else None
                })
            return albums

    def get_albums_by_artist(self, artist_id):
        with self._db_lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            if artist_id is None:
                cursor.execute("""
                    SELECT al.id, al.name, al.year, al.art_filename, ar.name as artist_name
                    FROM albums al LEFT JOIN artists ar ON al.artist_id = ar.id
                    ORDER BY al.name COLLATE NOCASE
                """)
            else:
                cursor.execute("""
                    SELECT al.id, al.name, al.year, al.art_filename, ar.name as artist_name
                    FROM albums al LEFT JOIN artists ar ON al.artist_id = ar.id
                    WHERE al.artist_id = ? ORDER BY al.name COLLATE NOCASE
                """, (artist_id,))
            albums = []
            for row in cursor.fetchall():
                art_path = self.art_cache_dir / row["art_filename"] if row["art_filename"] else None
                albums.append({
                    "id": row["id"], "name": row["name"], "year": row["year"],
                    "artist_name": row["artist_name"] or "Unknown Artist",
                    "art_path": str(art_path) if art_path and art_path.exists() else None
                })
            return albums

    def get_tracks_by_album(self, album_id):
        with self._db_lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.filepath, t.title, t.track_number, t.disc_number, t.duration, ar.name as artist_name
                FROM tracks t LEFT JOIN artists ar ON t.artist_id = ar.id
                WHERE t.album_id = ? ORDER BY t.disc_number, t.track_number
            """, (album_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_tracks_by_album_name(self, album_name: str):
        with self._db_lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.filepath, t.title, t.track_number, t.disc_number, t.duration, ar.name as artist_name
                FROM tracks t
                LEFT JOIN artists ar ON t.artist_id = ar.id
                JOIN albums al ON t.album_id = al.id
                WHERE al.name = ? ORDER BY t.disc_number, t.track_number
            """, (album_name,))
            return [dict(row) for row in cursor.fetchall()]

    def search_tracks(self, query: str):
        with self._db_lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            if not query:
                cursor.execute(f"""
                    SELECT 
                        t.id, t.filepath, t.title, t.duration,
                        al.name as album_name,
                        ar.name as artist_name
                    FROM {DB_TRACKS_TABLE} t
                    LEFT JOIN {DB_ALBUMS_TABLE} al ON t.album_id = al.id
                    LEFT JOIN {DB_ARTISTS_TABLE} ar ON t.artist_id = ar.id
                    ORDER BY ar.name COLLATE NOCASE, al.name COLLATE NOCASE, t.disc_number, t.track_number
                """)
            else:
                search_term = f"%{query}%"
                cursor.execute(f"""
                    SELECT 
                        t.id, t.filepath, t.title, t.duration,
                        al.name as album_name,
                        ar.name as artist_name
                    FROM {DB_TRACKS_TABLE} t
                    LEFT JOIN {DB_ALBUMS_TABLE} al ON t.album_id = al.id
                    LEFT JOIN {DB_ARTISTS_TABLE} ar ON t.artist_id = ar.id
                    WHERE t.title LIKE ?
                    
                    UNION
                    
                    SELECT 
                        t.id, t.filepath, t.title, t.duration,
                        al.name as album_name,
                        ar.name as artist_name
                    FROM {DB_TRACKS_TABLE} t
                    JOIN {DB_ALBUMS_TABLE} al ON t.album_id = al.id
                    LEFT JOIN {DB_ARTISTS_TABLE} ar ON t.artist_id = ar.id
                    WHERE al.name LIKE ?

                    UNION

                    SELECT 
                        t.id, t.filepath, t.title, t.duration,
                        al.name as album_name,
                        ar.name as artist_name
                    FROM {DB_TRACKS_TABLE} t
                    JOIN {DB_ARTISTS_TABLE} ar ON t.artist_id = ar.id
                    LEFT JOIN {DB_ALBUMS_TABLE} al ON t.album_id = al.id
                    WHERE ar.name LIKE ?
                """, (search_term, search_term, search_term))
            
            results = [dict(row) for row in cursor.fetchall()]
            log.info(f"Search for '{query}' found {len(results)} tracks.")
            return results

    def get_track_details_by_filepath(self, filepath):
        with self._db_lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.*, al.name as album, ar.name as artist, aa.name as album_artist
                FROM tracks t
                LEFT JOIN albums al ON t.album_id = al.id
                LEFT JOIN artists ar ON t.artist_id = ar.id
                LEFT JOIN artists aa ON al.artist_id = aa.id
                WHERE t.filepath = ?
            """, (filepath,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_album_art_path_for_file(self, filepath):
        details = self.get_track_details_by_filepath(filepath)
        if not details or not details.get('album_id'): return None
        
        with self._db_lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT art_filename FROM albums WHERE id = ?", (details['album_id'],))
            row = cursor.fetchone()
            if row and row['art_filename']:
                art_path = self.art_cache_dir / row['art_filename']
                return str(art_path) if art_path.exists() else None
        return None

    def get_raw_album_art_for_file(self, filepath: str) -> bytes | None:
        if not filepath or not os.path.exists(filepath):
            return None
        try:
            meta = mutagen.File(filepath, easy=False)
            if meta is None:
                return None
            
            pictures = []
            if hasattr(meta, 'pictures') and meta.pictures:
                pictures = meta.pictures
            elif 'APIC:' in meta:
                pictures = [meta['APIC:']]
            elif meta.tags and any(key.startswith('covr') for key in meta.tags):
                pictures = [meta.tags.get('covr')[0]]

            if pictures:
                pic = pictures[0]
                return pic.data if hasattr(pic, 'data') else bytes(pic)
                
        except Exception as e:
            log.error(f"Failed to extract raw album art from {filepath}: {e}")
        
        return None
    
    def update_track_metadata(self, filepath: str, new_metadata: dict):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Track file not found: {filepath}")

        try:
            audio = mutagen.File(filepath, easy=True)
            if audio is None:
                raise MetadataUpdateError(f"Could not load metadata for: {filepath}")
            
            tag_map = {
                'title': 'title', 'artist': 'artist', 'album': 'album',
                'album_artist': 'albumartist', 'composer': 'composer',
                'genre': 'genre', 'year': 'date', 'track_number': 'tracknumber',
                'disc_number': 'discnumber'
            }

            for key, easy_key in tag_map.items():
                if key in new_metadata:
                    audio[easy_key] = str(new_metadata[key])

            audio.save()
            log.info(f"Successfully saved new metadata for {filepath}")
            self._process_audio_file(filepath)

        except Exception as e:
            log.error(f"Failed to update metadata for {filepath}: {e}")
            raise MetadataUpdateError(f"Failed to save tags for {os.path.basename(filepath)}.") from e

    def update_track_album_art(self, track_filepath: str, image_filepath: str):
        if not os.path.exists(track_filepath):
            raise FileNotFoundError(f"Track file not found: {track_filepath}")
        if not os.path.exists(image_filepath):
            raise FileNotFoundError(f"Image file not found: {image_filepath}")
            
        try:
            audio = mutagen.File(track_filepath)
            if audio is None:
                raise MetadataUpdateError("Could not process audio file.")

            with open(image_filepath, 'rb') as art_file:
                art_data = art_file.read()

            mime_type = 'image/jpeg' if image_filepath.lower().endswith(('.jpg', '.jpeg')) else 'image/png'

            if hasattr(audio, 'pictures'):
                pic = FLACPicture()
                pic.data = art_data
                pic.mime = mime_type
                pic.type = 3
                audio.clear_pictures()
                audio.add_picture(pic)
            elif isinstance(audio.tags, ID3):
                audio.tags.delall("APIC")
                audio.tags.add(
                    APIC(encoding=3, mime=mime_type, type=PictureType.COVER_FRONT, desc='Cover', data=art_data)
                )
            else:
                raise MetadataUpdateError(f"Unsupported format for embedding art: {type(audio)}")

            audio.save()
            log.info(f"Successfully updated album art for {track_filepath}")
            self._process_audio_file(track_filepath)

        except Exception as e:
            log.error(f"Failed to update album art for {track_filepath}: {e}", exc_info=True)
            raise MetadataUpdateError(f"Failed to save album art for {os.path.basename(track_filepath)}.") from e


    def close(self):
        log.info("LibraryManager is closing.")
        self.stop_scan()

    def on_scan_progress(self, progress, message):
        pass

    def on_scan_finished(self, message):
        pass
