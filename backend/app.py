from flask import Flask, request, jsonify
from flask_cors import CORS
from minio import Minio
from minio.error import S3Error
from pymongo import MongoClient
import boto3
import io
import time
import threading
from datetime import datetime, timedelta
import os
import urllib.parse

# -----------------------------
# Load environment variables
# -----------------------------
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "uploads")

AWS_BUCKET = os.getenv("AWS_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "mydb")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "files")

# -----------------------
# INIT SERVICES
# -----------------------
app = Flask(__name__)
CORS(app)

mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DB_NAME]
files_col = db["files"]

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION,
)

# Ensure bucket exists
found = minio_client.bucket_exists(MINIO_BUCKET)
if not found:
    minio_client.make_bucket(MINIO_BUCKET)
    print(f"✅ Created MinIO bucket: {MINIO_BUCKET}")

# -----------------------
# HELPER FUNCTIONS
# -----------------------

def get_content_type(filename):
    """Get content type based on file extension for proper preview"""
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
    }
    return content_types.get(extension, 'application/octet-stream')

def generate_preview_urls(filename):
    """Generate preview URLs for MinIO and S3 that open in browser"""
    
    # MinIO Preview URL
    try:
        minio_preview_url = minio_client.presigned_get_object(
            MINIO_BUCKET,
            filename,
            expires=timedelta(hours=1),
            response_headers={
                'response-content-type': get_content_type(filename),
                'response-content-disposition': f'inline; filename="{filename}"'
            }
        )
    except Exception as e:
        print(f"Error generating MinIO preview URL: {e}")
        minio_preview_url = None

    # S3 Preview URL
    try:
        s3_preview_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': AWS_BUCKET,
                'Key': filename,
                'ResponseContentType': get_content_type(filename),
                'ResponseContentDisposition': f'inline; filename="{filename}"'
            },
            ExpiresIn=3600
        )
    except Exception as e:
        print(f"Error generating S3 preview URL: {e}")
        s3_preview_url = None

    return minio_preview_url, s3_preview_url

# -----------------------
# ROUTES
# -----------------------

@app.route("/upload", methods=["POST"])
def upload_file():
    """Upload file to MinIO + save MongoDB entry"""
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file provided"}), 400

    filename = file.filename
    file_data = file.read()

    try:
        minio_client.put_object(
            MINIO_BUCKET,
            filename,
            io.BytesIO(file_data),
            length=len(file_data),
            content_type=get_content_type(filename)
        )

        files_col.insert_one({
            "filename": filename,
            "status": "pending",
            "size": len(file_data),
            "content_type": get_content_type(filename),
            "created_at": datetime.utcnow(),
        })

        return jsonify({"message": f"{filename} uploaded to MinIO"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/files", methods=["GET"])
def list_files():
    """Return all file metadata"""
    docs = list(files_col.find({}, {"_id": 0}))
    return jsonify(docs)


@app.route("/delete/<filename>", methods=["DELETE"])
def delete_file(filename):
    """Delete from MinIO, S3, and MongoDB"""
    try:
        minio_client.remove_object(MINIO_BUCKET, filename)
    except Exception:
        pass

    try:
        s3_client.delete_object(Bucket=AWS_BUCKET, Key=filename)
    except Exception:
        pass

    files_col.delete_one({"filename": filename})
    return jsonify({"message": f"{filename} deleted successfully"}), 200


@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    """Download file from MinIO or S3"""
    source = request.args.get("source", "minio")  # minio or s3
    
    try:
        if source == "s3":
            # Download from S3
            obj = s3_client.get_object(Bucket=AWS_BUCKET, Key=filename)
            file_data = obj['Body'].read()
        else:
            # Download from MinIO
            minio_obj = minio_client.get_object(MINIO_BUCKET, filename)
            file_data = minio_obj.read()
            minio_obj.close()
        
        from flask import send_file
        return send_file(
            io.BytesIO(file_data),
            as_attachment=True,
            download_name=filename,
            mimetype=get_content_type(filename)
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/preview/<filename>", methods=["GET"])
def preview_file(filename):
    """Preview file in browser (inline) from MinIO or S3"""
    source = request.args.get("source", "minio")  # minio or s3
    
    try:
        if source == "s3":
            # Get from S3
            obj = s3_client.get_object(Bucket=AWS_BUCKET, Key=filename)
            file_data = obj['Body'].read()
            content_type = obj.get('ContentType', get_content_type(filename))
        else:
            # Get from MinIO
            minio_obj = minio_client.get_object(MINIO_BUCKET, filename)
            file_data = minio_obj.read()
            content_type = get_content_type(filename)
            minio_obj.close()
        
        from flask import Response
        return Response(
            file_data,
            content_type=content_type,
            headers={
                'Content-Disposition': f'inline; filename="{filename}"'
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------
# BACKGROUND SYNC THREAD
# -----------------------

def sync_to_s3():
    """Continuously sync pending MinIO files to AWS S3"""
    print("🚀 Background sync thread started")
    while True:
        try:
            pending_files = list(files_col.find({"status": "pending"}))
            for file in pending_files:
                filename = file["filename"]
                print(f"🔄 Syncing {filename}...")

                try:
                    minio_obj = minio_client.get_object(MINIO_BUCKET, filename)
                    data = minio_obj.read()
                    minio_obj.close()
                except S3Error as e:
                    print(f"⚠️ Cannot read {filename}: {e}")
                    continue

                try:
                    s3_client.upload_fileobj(
                        io.BytesIO(data), 
                        AWS_BUCKET, 
                        filename,
                        ExtraArgs={'ContentType': get_content_type(filename)}
                    )
                except Exception as e:
                    print(f"❌ Failed to upload {filename} to S3: {e}")
                    continue

                # Generate preview URLs
                minio_preview_url, s3_preview_url = generate_preview_urls(filename)

                # Update database with preview URLs
                files_col.update_one(
                    {"filename": filename},
                    {
                        "$set": {
                            "status": "uploaded-to-s3",
                            "minio_preview_url": minio_preview_url,
                            "s3_preview_url": s3_preview_url,
                            "content_type": get_content_type(filename),
                            "uploaded_at": datetime.utcnow(),
                        }
                    },
                )

                print(f"✅ Synced {filename} → AWS S3")

        except Exception as e:
            print("❌ Error in sync thread:", e)

        time.sleep(60)  # Check every 60 s


# Start background thread
threading.Thread(target=sync_to_s3, daemon=True).start()

# -----------------------
# RUN
# -----------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)