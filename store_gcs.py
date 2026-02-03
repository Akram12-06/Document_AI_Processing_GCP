from google.cloud import storage
from pathlib import Path
import mimetypes

def upload_pdfs_to_gcs(
    local_folder: str,
    bucket_name: str,
    gcs_prefix: str = ""
):
    """
    Upload all PDF files from a local folder to GCS.

    :param local_folder: Path to local folder containing PDFs
    :param bucket_name: Target GCS bucket name
    :param gcs_prefix: Optional folder path inside bucket (e.g. 'documents/pdfs/')
    """

    client = storage.Client()  # Uses VM's attached service account
    bucket = client.bucket(bucket_name)

    local_path = Path(local_folder)

    if not local_path.exists():
        raise FileNotFoundError(f"Folder not found: {local_folder}")

    pdf_files = list(local_path.glob("*.pdf"))

    if not pdf_files:
        print("No PDF files found.")
        return

    for pdf in pdf_files:
        blob_name = f"{gcs_prefix.rstrip('/')}/{pdf.name}" if gcs_prefix else pdf.name
        blob = bucket.blob(blob_name)

        content_type, _ = mimetypes.guess_type(str(pdf))
        blob.upload_from_filename(
            filename=str(pdf),
            content_type=content_type or "application/pdf"
        )

        print(f"Uploaded: {pdf.name} -> gs://{bucket_name}/{blob_name}")

    print(f"\nDone. Uploaded {len(pdf_files)} PDFs to GCS.")

if __name__ == "__main__":
    LOCAL_FOLDER = "/home/si_akram/Document_processing/sample_invoices/test"   # change this
    BUCKET_NAME = "sample_invoice_bucket_coe"   # change this
    GCS_PREFIX = "input"  
    # GCS_PREFIX = "unprocessed_invoice"         # optional folder in bucket

    upload_pdfs_to_gcs(
        local_folder=LOCAL_FOLDER,
        bucket_name=BUCKET_NAME,
        gcs_prefix=GCS_PREFIX
    )
