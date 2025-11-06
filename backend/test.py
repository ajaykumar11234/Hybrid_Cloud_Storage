from minio import Minio

client = Minio(
    "minio-on-render-8wrk.onrender.com",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=True
)

print("✅ Connected!")
print("Buckets:", [b.name for b in client.list_buckets()])
