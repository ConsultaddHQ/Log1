import io
import os
import boto3
import subprocess
from datetime import datetime, timedelta, timezone
from django.core.management import BaseCommand


def dump_db_to_s3(**kwargs) -> str:
    """
    Dump a PostgreSQL database, upload to S3, and remove old dumps beyond retention period.

    Expected kwargs:
        db_name, user, password, host, port, bucket_name, s3_key_prefix, retention_days
    """
    db_name = kwargs.get("db_name")
    user = kwargs.get("user")
    password = kwargs.get("password")
    host = kwargs.get("host")
    port = kwargs.get("port", "5432")
    bucket_name = kwargs.get("bucket_name")
    s3_key_prefix = kwargs.get("s3_key_prefix", "log1")
    retention_days = kwargs.get("retention_days", 7)

    s3 = boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION_NAME"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
    )

    # ---------- Step 1: Dump DB ----------
    dump_cmd = [
        "pg_dump", f"--dbname=postgresql://{user}:{password}@{host}:{port}/{db_name}"
    ]
    print(f"Starting database dump for {db_name}...")
    # dump_output = subprocess.check_output(dump_cmd)
    # print("Database dump completed.")
    # ---------- Step 2: Upload new dump ----------
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    s3_key = f"{s3_key_prefix}/{today_str}_dump_{db_name}.sql"

    try:
        print(s3_key)
        with subprocess.Popen(dump_cmd, stdout=subprocess.PIPE) as proc:
            s3.upload_fileobj(proc.stdout, bucket_name, s3_key)
        print(f"✅ Uploaded new dump to S3: s3://{bucket_name}/{s3_key}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return "Upload failed. No old backups were deleted."

    # ---------- Step 3: Remove old dumps (only if upload succeeded) ----------
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    old_files = []
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=f"{s3_key_prefix}/")
        if "Contents" in response:
            for obj in response["Contents"]:
                try:
                    filename = os.path.basename(obj["Key"])
                    last_modified = obj["LastModified"]
                    if "_dump_" in filename and filename.endswith(".sql"):
                        if last_modified < cutoff_date:
                            old_files.append({"Key": f"{s3_key_prefix}/{filename}"})
                except Exception as e:
                    print(f"⚠️ Skipping file {obj['Key']}: {e}")
        if not old_files:
            print(f"ℹ️ No old backups found beyond {retention_days} days.")
        else:
            s3.delete_objects(Bucket=bucket_name, Delete={"Objects": old_files})
            return f"Deleted {len(old_files)} old backup(s)."
    except Exception as e:
        print(f"⚠️ Cleanup failed: {e}")

    return f"s3://{bucket_name}/{s3_key}"


class Command(BaseCommand):
    help = "Dump the PostgreSQL database to S3 and remove old dumps beyond retention period."

    def handle(self, *args, **options):
        try:
            dump_db_to_s3(
                db_name=os.environ.get("DB_NAME"),
                user=os.environ.get("DB_USER"),
                password=os.environ.get("DB_PASSWORD"),
                host=os.environ.get("DB_HOST"),
                port=os.environ.get("DB_PORT", "5432"),
                bucket_name=os.environ.get("AWS_S3_DUMP_BUCKET"),
                s3_key_prefix="log1",
                retention_days=7
            )
        except Exception as e:
            print(f"❌ Error during DB dump process: {e}")
