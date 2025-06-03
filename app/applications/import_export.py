from flask import Blueprint, request, redirect, url_for, flash, jsonify, send_file, current_app
from flask_login import login_required, current_user
from applications import mongo
from applications.admin_routes import admin_required
from bson import ObjectId
from datetime import datetime
import json
import tempfile
import os
from io import BytesIO

import_export_bp = Blueprint(
    "import_export_bp", 
    __name__, 
    template_folder="../../templates", 
    static_folder="../../static"
)

def serialize_mongodb_data(obj):
    """Convert MongoDB-specific data types to JSON serializable format"""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_mongodb_data(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_mongodb_data(item) for item in obj]
    else:
        return obj

def deserialize_mongodb_data(obj):
    """Convert JSON data back to MongoDB format"""
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            # Convert _id fields to ObjectId, but keep user_id as string for query compatibility
            if (key.endswith('_id') or key == '_id') and key != 'user_id':
                try:
                    result[key] = ObjectId(value) if value else None
                except:
                    result[key] = value
            elif _is_datetime_field(key, value):
                # Try to parse datetime fields
                try:
                    result[key] = _parse_datetime_string(value)
                except:
                    result[key] = value
            else:
                result[key] = deserialize_mongodb_data(value)
        return result
    elif isinstance(obj, list):
        return [deserialize_mongodb_data(item) for item in obj]
    else:
        return obj

def _is_datetime_field(key, value):
    """Check if a field should be treated as a datetime field"""
    if not isinstance(value, str):
        return False
    
    # Known datetime field names
    datetime_fields = {
        'created_at', 'updated_at', 'registration_time', 'last_modified_time',
        'creation_time', 'log_date', 'due_date', 'completed_at', 'planting_date'
    }
    
    # Check if it's a known datetime field
    if key in datetime_fields:
        return True
    
    # Check if it looks like an ISO datetime string
    if 'T' in value and (':' in value or 'Z' in value or '+' in value):
        return True
    
    return False

def _parse_datetime_string(value):
    """Parse a datetime string to datetime object"""
    if not isinstance(value, str):
        return value
    
    # Handle ISO format with Z suffix
    if value.endswith('Z'):
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    
    # Handle ISO format with timezone
    if '+' in value and 'T' in value:
        return datetime.fromisoformat(value)
    
    # Handle basic ISO format without timezone
    if 'T' in value:
        try:
            return datetime.fromisoformat(value)
        except:
            # Try parsing with different formats
            formats = [
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M:%S'
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except:
                    continue
    
    # Handle date-only format for planting_date etc.
    if len(value) == 10 and value.count('-') == 2:
        try:
            return datetime.strptime(value, '%Y-%m-%d')
        except:
            pass
    
    # If all else fails, return the original value
    return value

@import_export_bp.route('/export-data', methods=['POST'])
@login_required
@admin_required
def export_data():
    """Export all application data to JSON format"""
    try:
        export_data = {
            'export_metadata': {
                'exported_at': datetime.now().isoformat(),
                'exported_by': current_user.email,
                'version': '1.0'
            },
            'data': {}
        }
        
        # Define collections to export
        collections_to_export = [
            'users',
            'gardens', 
            'beds',
            'care_logs',
            'recommendations',
            'diary'
        ]
        
        # Export each collection
        for collection_name in collections_to_export:
            collection = mongo.db[collection_name]
            documents = list(collection.find({}))
            export_data['data'][collection_name] = serialize_mongodb_data(documents)
            
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', prefix='garden_export_') as temp_file:
            json.dump(export_data, temp_file, indent=2, ensure_ascii=False)
            temp_file_path = temp_file.name
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'garden_export_{timestamp}.json'
        
        def remove_temp_file():
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
        # Read file content and clean up
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        remove_temp_file()
        
        # Create BytesIO object for sending
        file_buffer = BytesIO(file_content)
        
        flash(f'Данные успешно экспортированы. Экспортировано коллекций: {len(collections_to_export)}', 'success')
        
        return send_file(
            file_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        flash(f'Ошибка при экспорте данных: {str(e)}', 'error')
        return redirect(url_for('admin_bp.admin_dashboard'))

@import_export_bp.route('/import-data', methods=['POST'])
@login_required  
@admin_required
def import_data():
    """Import application data from JSON format"""
    try:
        if 'import_file' not in request.files:
            flash('Файл для импорта не выбран', 'error')
            return redirect(url_for('admin_bp.admin_dashboard'))
            
        file = request.files['import_file']
        if file.filename == '':
            flash('Файл для импорта не выбран', 'error')
            return redirect(url_for('admin_bp.admin_dashboard'))
            
        if not file.filename.lower().endswith('.json'):
            flash('Поддерживаются только JSON файлы', 'error')
            return redirect(url_for('admin_bp.admin_dashboard'))
            
        # Parse JSON data
        try:
            import_data = json.load(file)
        except json.JSONDecodeError as e:
            flash(f'Ошибка при чтении JSON файла: {str(e)}', 'error')
            return redirect(url_for('admin_bp.admin_dashboard'))
            
        # Validate structure
        if 'data' not in import_data:
            flash('Неверный формат файла импорта. Отсутствует секция "data"', 'error')
            return redirect(url_for('admin_bp.admin_dashboard'))
            
        data_to_import = import_data['data']
        
        # Get confirmation from user (this should be handled via form parameter)
        replace_existing = request.form.get('replace_existing') == 'true'
        
        imported_counts = {}
        
        # Define import order (to handle dependencies)
        import_order = [
            'users',
            'gardens',
            'beds', 
            'care_logs',
            'recommendations',
            'diary'
        ]
        
        # Import each collection
        for collection_name in import_order:
            if collection_name not in data_to_import:
                continue
                
            collection = mongo.db[collection_name]
            documents = data_to_import[collection_name]
            
            if not documents:
                imported_counts[collection_name] = 0
                continue
                
            # Convert back to MongoDB format
            documents = deserialize_mongodb_data(documents)
            
            if replace_existing:
                # Clear existing data for this collection
                collection.delete_many({})
                
            # Insert documents
            if isinstance(documents, list):
                if len(documents) > 0:
                    try:
                        # Use insert_many with ordered=False to continue on duplicates
                        result = collection.insert_many(documents, ordered=False)
                        imported_counts[collection_name] = len(result.inserted_ids)
                    except Exception as e:
                        # Handle duplicate key errors
                        if 'duplicate key' in str(e).lower():
                            # Try inserting one by one to handle duplicates
                            count = 0
                            for doc in documents:
                                try:
                                    collection.insert_one(doc)
                                    count += 1
                                except:
                                    # Skip duplicates or invalid documents
                                    continue
                            imported_counts[collection_name] = count
                        else:
                            flash(f'Ошибка при импорте коллекции {collection_name}: {str(e)}', 'warning')
                            imported_counts[collection_name] = 0
                else:
                    imported_counts[collection_name] = 0
                      # Create summary message
        summary_parts = []
        for collection_name, count in imported_counts.items():
            if count > 0:
                summary_parts.append(f'{collection_name}: {count}')
                
        if summary_parts:
            summary = 'Импортировано записей: ' + ', '.join(summary_parts)
            flash(summary, 'success')
        else:
            flash('Нет данных для импорта или все записи уже существуют', 'warning')
            
    except Exception as e:
        flash(f'Ошибка при импорте данных: {str(e)}', 'error')
        
    return redirect(url_for('admin_bp.admin_dashboard'))

@import_export_bp.route('/import-user-data', methods=['POST'])
@login_required
def import_user_data():
    """Import current user's own data only"""
    try:
        if 'import_file' not in request.files:
            flash('Файл для импорта не выбран', 'error')
            return redirect(url_for('auth_bp.profile'))
            
        file = request.files['import_file']
        if file.filename == '':
            flash('Файл для импорта не выбран', 'error')
            return redirect(url_for('auth_bp.profile'))
            
        if not file.filename.lower().endswith('.json'):
            flash('Поддерживаются только JSON файлы', 'error')
            return redirect(url_for('auth_bp.profile'))
            
        # Parse JSON data
        try:
            import_data = json.load(file)
        except json.JSONDecodeError as e:
            flash(f'Ошибка при чтении JSON файла: {str(e)}', 'error')
            return redirect(url_for('auth_bp.profile'))
            
        # Validate structure
        if 'data' not in import_data:
            flash('Неверный формат файла импорта. Отсутствует секция "data"', 'error')
            return redirect(url_for('auth_bp.profile'))
            
        # Check if this is a user export (not admin export)
        export_type = import_data.get('export_metadata', {}).get('export_type')
        if export_type != 'user_data':
            flash('Можно импортировать только файлы экспорта пользователей. Обратитесь к администратору для массового импорта.', 'error')
            return redirect(url_for('auth_bp.profile'))
            
        data_to_import = import_data['data']
        current_user_id = current_user.get_id()
        
        # Validate that the imported data belongs to the current user
        if 'users' in data_to_import and data_to_import['users']:
            imported_user_data = data_to_import['users'][0]  # Should be only one user
            imported_user_id = str(imported_user_data.get('_id', ''))
            
            if imported_user_id != current_user_id:
                flash('Вы можете импортировать только свои собственные данные', 'error')
                return redirect(url_for('auth_bp.profile'))
        
        # Get confirmation from user
        replace_existing = request.form.get('replace_existing') == 'true'
        
        imported_counts = {}
        
        # Define collections to import (excluding users - we don't want to overwrite user account)
        import_collections = [
            'gardens',
            'beds', 
            'care_logs',
            'recommendations',
            'diary'
        ]
        
        # Import each collection (user's data only)
        for collection_name in import_collections:
            if collection_name not in data_to_import:
                continue
                
            collection = mongo.db[collection_name]
            documents = data_to_import[collection_name]
            
            if not documents:
                imported_counts[collection_name] = 0
                continue
                
            # Additional validation: ensure all documents belong to current user
            for doc in documents:
                if 'user_id' in doc and doc['user_id'] != current_user_id:
                    flash(f'Обнаружены данные другого пользователя в коллекции {collection_name}. Импорт отменен.', 'error')
                    return redirect(url_for('auth_bp.profile'))
                
            # Convert back to MongoDB format
            documents = deserialize_mongodb_data(documents)
            
            if replace_existing:
                # Clear existing data for this collection (only for current user)
                collection.delete_many({'user_id': current_user_id})
                
            # Insert documents
            if isinstance(documents, list):
                if len(documents) > 0:
                    try:
                        result = collection.insert_many(documents, ordered=False)
                        imported_counts[collection_name] = len(result.inserted_ids)
                    except Exception as e:
                        # Handle duplicate key errors
                        if 'duplicate key' in str(e).lower():
                            # Try inserting one by one to handle duplicates
                            count = 0
                            for doc in documents:
                                try:
                                    collection.insert_one(doc)
                                    count += 1
                                except:
                                    # Skip duplicates or invalid documents
                                    continue
                            imported_counts[collection_name] = count
                        else:
                            flash(f'Ошибка при импорте коллекции {collection_name}: {str(e)}', 'warning')
                            imported_counts[collection_name] = 0
                else:
                    imported_counts[collection_name] = 0
                    
        # Create summary message
        summary_parts = []
        for collection_name, count in imported_counts.items():
            if count > 0:
                collection_names_ru = {
                    'gardens': 'участков',
                    'beds': 'грядок',
                    'care_logs': 'записей ухода',
                    'recommendations': 'рекомендаций',
                    'diary': 'записей дневника'
                }
                ru_name = collection_names_ru.get(collection_name, collection_name)
                summary_parts.append(f'{ru_name}: {count}')
                
        if summary_parts:
            summary = 'Импортировано ваших данных: ' + ', '.join(summary_parts)
            flash(summary, 'success')
        else:
            flash('Нет данных для импорта или все записи уже существуют', 'warning')
            
    except Exception as e:
        flash(f'Ошибка при импорте ваших данных: {str(e)}', 'error')
        
    return redirect(url_for('auth_bp.profile'))

@import_export_bp.route('/export-user-data', methods=['POST'])
@login_required
def export_user_data():
    """Export current user's data only"""
    try:
        user_id = current_user.get_id()
        
        export_data = {
            'export_metadata': {
                'exported_at': datetime.now().isoformat(),
                'exported_by': current_user.email,
                'export_type': 'user_data',
                'version': '1.0'
            },
            'data': {}
        }
        
        # Export user's own data
        user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        if user_data:
            export_data['data']['users'] = [serialize_mongodb_data(user_data)]
            
        # Export user's gardens
        gardens = list(mongo.db.gardens.find({'user_id': user_id}))
        export_data['data']['gardens'] = serialize_mongodb_data(gardens)
        
        # Export user's beds  
        beds = list(mongo.db.beds.find({'user_id': user_id}))
        export_data['data']['beds'] = serialize_mongodb_data(beds)
        
        # Export user's care logs
        care_logs = list(mongo.db.care_logs.find({'user_id': user_id}))
        export_data['data']['care_logs'] = serialize_mongodb_data(care_logs)
        
        # Export user's recommendations
        recommendations = list(mongo.db.recommendations.find({'user_id': user_id}))
        export_data['data']['recommendations'] = serialize_mongodb_data(recommendations)
        
        # Export user's diary entries
        diary_entries = list(mongo.db.diary.find({'user_id': user_id}))
        export_data['data']['diary'] = serialize_mongodb_data(diary_entries)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', prefix='my_garden_export_') as temp_file:
            json.dump(export_data, temp_file, indent=2, ensure_ascii=False)
            temp_file_path = temp_file.name
            
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'my_garden_data_{timestamp}.json'
        
        def remove_temp_file():
            try:
                os.unlink(temp_file_path)
            except:
                pass
                
        # Read file content and clean up
        with open(temp_file_path, 'rb') as f:
            file_content = f.read()
        remove_temp_file()
        
        # Create BytesIO object for sending
        file_buffer = BytesIO(file_content)
        
        total_records = (
            len(export_data['data'].get('gardens', [])) +
            len(export_data['data'].get('beds', [])) +
            len(export_data['data'].get('care_logs', [])) +
            len(export_data['data'].get('recommendations', [])) +
            len(export_data['data'].get('diary', []))
        )
        
        flash(f'Ваши данные успешно экспортированы. Всего записей: {total_records}', 'success')
        
        return send_file(
            file_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        flash(f'Ошибка при экспорте ваших данных: {str(e)}', 'error')
        return redirect(url_for('main_bp.index'))
