import os
import json
import boto3
from botocore.exceptions import NoCredentialsError

# ---------- CONFIGURATION ----------
LOCAL_DIR = "./resumes/marketing_submission"  # Local directory containing resumes/files
BUCKET_NAME = "marketing-resumes"
S3_FOLDER = "uploads/resumes"  # Folder path inside the bucket
OUTPUT_JSON = "uploaded_files.json"
AWS_REGION = "ap-south-1"  # Change as per your region
# ----------------------------------


def upload_files_to_s3(local_dir, bucket, s3_folder):
    s3_client = boto3.client(
        's3', region_name=os.getenv('AWS_REGION_NAME'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    uploaded_items = []

    for root, _, files in os.walk(local_dir):
        for file_name in files:
            local_path = os.path.join(root, file_name)
            relative_path = os.path.relpath(local_path, local_dir)
            s3_key = f"{s3_folder}/{relative_path}".replace("\\", "/")

            try:
                # Upload file to S3
                s3_client.upload_file(local_path, bucket, s3_key)

                # Generate hosted public URL
                file_url = f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

                uploaded_items.append({
                    "name": file_name,
                    "url": file_url
                })

                print(f"✅ Uploaded: {file_name}")

            except FileNotFoundError:
                print(f"❌ File not found: {local_path}")
            except NoCredentialsError:
                print("❌ AWS credentials not available.")
                return []
            except Exception as e:
                print(f"❌ Error uploading {file_name}: {e}")

    return uploaded_items


def main():
    uploaded_files = upload_files_to_s3(LOCAL_DIR, BUCKET_NAME, S3_FOLDER)

    if uploaded_files:
        # Write uploaded details to JSON
        with open(OUTPUT_JSON, "w") as f:
            json.dump(uploaded_files, f, indent=4)
        print(f"\n📁 JSON file created: {OUTPUT_JSON}")
    else:
        print("⚠️ No files were uploaded.")


if __name__ == "__main__":
    main()

