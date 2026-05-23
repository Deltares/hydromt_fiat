"""
Download data from a MinIO bucket at `s3.deltares.nl`.

Requires the `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` environment variables to be set.

Uploading files to the bucket can be done in the browser at this url (https://s3-console.deltares.nl).
Or by extending the configured minio client in this script to allow for uploads.

To use this script, you can do one of the following:
    1. set the environment variables manually
    2. create a `.env` file in the root of this project with the following content:
        ```
        MINIO_ACCESS_KEY=your_access_key
        MINIO_SECRET_KEY=your_secret_key
        ```
"""

import argparse
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio

logger = logging.getLogger(__name__)


def download_directory(
    client: Minio,
    path_in_bucket: str,
    output_dir: Path,
    bucket_name: str,
    overwrite: bool = False,
) -> None:
    """Download a directory from a MinIO bucket to a local directory."""
    if output_dir.exists() and not overwrite:
        raise FileExistsError(
            f"Path {output_dir} already exists. Use `overwrite=True` to overwrite."
        )

    if not client.bucket_exists(bucket_name):
        raise ValueError(f"Bucket {bucket_name} does not exist.")
    logger.info(
        f"Downloading from bucket '{bucket_name}': {path_in_bucket} to {output_dir}"
    )
    objs = client.list_objects(
        bucket_name=bucket_name,
        prefix=path_in_bucket,
        recursive=True,
    )
    total = len(objs)
    for i, obj in enumerate(objs):
        rel_path = Path(obj.object_name).relative_to(path_in_bucket)
        client.fget_object(
            bucket_name=bucket_name,
            object_name=obj.object_name,
            file_path=str(output_dir / rel_path),
        )
        logger.debug(
            f"Downloaded {rel_path} to {output_dir / rel_path} ({i + 1}/{total})"
        )


def prepare_client(
    endpoint: str,
    region: str,
    access_key: str,
    secret_key: str,
) -> Minio:
    """Prepare the MinIO client."""
    if not (access_key and secret_key):
        raise ValueError(
            "Access key and secret key must be provided either as cli arguments or as"
            " environment variables 'MINIO_ACCESS_KEY' and 'MINIO_SECRET_KEY'."
        )
    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
    )


def fetch_data(
    output_dir: Path,
    path_in_bucket: str,
    bucket_name: str,
    endpoint: str,
    region: str,
    access_key: str,
    secret_key: str,
    overwrite: bool = False,
) -> None:
    """Fetch data from the MinIO bucket and store it in the local _data directory."""
    client = prepare_client(
        endpoint=endpoint, region=region, access_key=access_key, secret_key=secret_key
    )

    download_directory(
        client=client,
        path_in_bucket=path_in_bucket,
        output_dir=output_dir / path_in_bucket,
        bucket_name=bucket_name,
        overwrite=overwrite,
    )


if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(description="Fetch data from a MinIO bucket.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "_data",
        help="Directory to store the downloaded data.",
    )
    parser.add_argument(
        "--path-in-bucket",
        type=str,
        default="foo",
        help="Path in the bucket to download. Default is 'foo'.",
    )
    parser.add_argument(
        "--bucket-name",
        type=str,
        default="hydromt-fiat",
        help="Name of the bucket to download from. Default is 'hydromt-fiat'.",
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="s3.deltares.nl",
        help="MinIO endpoint. Default is 's3.deltares.nl'.",
    )
    parser.add_argument(
        "--region",
        type=str,
        default="eu-west-1",
        help="MinIO region. Default is 'eu-west-1'.",
    )
    parser.add_argument(
        "--access-key",
        type=str,
        default=os.getenv("MINIO_ACCESS_KEY"),
        help="MinIO access key. By default, 'MINIO_ACCESS_KEY' environment variable.",
    )
    parser.add_argument(
        "--secret-key",
        type=str,
        default=os.getenv("MINIO_SECRET_KEY"),
        help="MinIO secret key. By default, 'MINIO_SECRET_KEY' environment variable.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Whether to overwrite the output directory if it already exists.",
        default=False,
    )
    args = parser.parse_args()

    fetch_data(
        output_dir=args.output_dir,
        path_in_bucket=args.path_in_bucket,
        bucket_name=args.bucket_name,
        endpoint=args.endpoint,
        region=args.region,
        access_key=args.access_key,
        secret_key=args.secret_key,
        overwrite=args.overwrite,
    )
