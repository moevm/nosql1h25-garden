from flask import flash, current_app
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime, timezone, timedelta
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_photo(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not upload_folder:
            flash('Upload folder is not configured.', 'error')
            return None
        file_path = os.path.join(upload_folder, unique_filename)
        try:
            file.save(file_path)
            return os.path.join('uploads', unique_filename).replace("\\", "/")
        except Exception as e:
            flash(f'Error saving photo: {e}', 'error')
            return None
    return None

from datetime import datetime, timezone, timedelta

MOSCOW_TZ = timezone(timedelta(hours=3))

def moscow_now():
    """Возвращает текущее время в московском часовом поясе"""
    return datetime.now(MOSCOW_TZ)

def moscow_utcnow():
    """Возвращает текущее время в московском часовом поясе (альтернативное название для совместимости)"""
    return datetime.now(MOSCOW_TZ)

def to_moscow_time(dt):
    """Конвертирует datetime объект в московское время"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Если время без таймзоны, предполагаем что это UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MOSCOW_TZ)

def moscow_date_from_string(date_str, time_str=None):
    """Создает datetime объект в московском времени из строк даты и времени"""
    if time_str:
        dt = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
    else:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
    
    # Устанавливаем московскую таймзону
    return dt.replace(tzinfo=MOSCOW_TZ)

def format_moscow_datetime(dt, format_str='%Y-%m-%d %H:%M'):
    """Форматирует datetime в московском времени"""
    if dt is None:
        return None
    moscow_dt = to_moscow_time(dt)
    return moscow_dt.strftime(format_str)