import io
from datetime import timedelta
from flask import send_file, Response

def get_content_type(filename: str) -> str:
    """Get content type based on file extension"""
    extension = filename.lower().split('.')[-1]
    content_types = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'txt': 'text/plain',
        'html': 'text/html',
        'htm': 'text/html',
        'json': 'application/json',
        'xml': 'application/xml',
        'csv': 'text/csv',
        'mp4': 'video/mp4',
        'mp3': 'audio/mpeg',
        'zip': 'application/zip',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }
    return content_types.get(extension, 'application/octet-stream')

def format_file_size(bytes: int) -> str:
    """Format file size in human readable format"""
    if not bytes:
        return "N/A"
    sizes = ["Bytes", "KB", "MB", "GB"]
    i = 0
    while bytes >= 1024 and i < len(sizes) - 1:
        bytes /= 1024.0
        i += 1
    return f"{bytes:.2f} {sizes[i]}"

def is_file_supported_for_ai(filename: str) -> bool:
    """Check if file type supports AI analysis"""
    if '.' not in filename:
        return False
    extension = filename.split('.')[-1].lower()
    supported_types = ['pdf', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'csv', 'json', 'xml']
    return extension in supported_types

def create_file_response(file_data: bytes, filename: str, as_attachment: bool = False):
    """Create Flask response for file download/preview"""
    content_type = get_content_type(filename)
    
    if as_attachment:
        return send_file(
            io.BytesIO(file_data),
            as_attachment=True,
            download_name=filename,
            mimetype=content_type
        )
    else:
        return Response(
            file_data,
            content_type=content_type,
            headers={
                'Content-Disposition': f'inline; filename="{filename}"'
            }
        )