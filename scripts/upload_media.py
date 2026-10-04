"""
One-off: upload everything in ./media to the Railway bucket, keeping the same
relative paths (media/products/x.jpg -> products/x.jpg) so the image paths
already stored in the database keep working.

Usage (from the project root):
    pip install boto3 python-dotenv
    python scripts/upload_media.py

Reads credentials from .env.bucket (git-ignored). Safe to re-run: files that
already exist in the bucket with the same size are skipped.
"""
import mimetypes
import os
import sys
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env.bucket")
except ImportError:
    pass

BUCKET = os.environ["BUCKET_NAME"]
s3 = boto3.client(
    "s3",
    endpoint_url=os.getenv("BUCKET_ENDPOINT", "https://t3.storageapi.dev"),
    aws_access_key_id=os.environ["BUCKET_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["BUCKET_SECRET_ACCESS_KEY"],
    region_name=os.getenv("BUCKET_REGION", "auto"),
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)

media_dir = ROOT / "media"
if not media_dir.is_dir():
    sys.exit(f"No media folder at {media_dir}")

uploaded = skipped = 0
for path in sorted(p for p in media_dir.rglob("*") if p.is_file()):
    key = path.relative_to(media_dir).as_posix()
    size = path.stat().st_size
    try:
        head = s3.head_object(Bucket=BUCKET, Key=key)
        if head["ContentLength"] == size:
            skipped += 1
            print(f"skip    {key}")
            continue
    except ClientError:
        pass
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    s3.upload_file(str(path), BUCKET, key, ExtraArgs={"ContentType": ctype})
    uploaded += 1
    print(f"upload  {key}  ({size:,} bytes)")

print(f"\nDone: {uploaded} uploaded, {skipped} already there.")
print("Bucket now contains:")
for obj in s3.list_objects_v2(Bucket=BUCKET).get("Contents", []):
    print(f"  {obj['Key']}  ({obj['Size']:,} bytes)")
