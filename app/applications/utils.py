from flask import flash, current_app
from werkzeug.utils import secure_filename
import os
import uuid
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