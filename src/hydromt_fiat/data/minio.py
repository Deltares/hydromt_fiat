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
    access_key: str | None = None,
    secret_key: str | None = None,
    endpoint: str = "s3.deltares.nl",
    region: str = "eu-west-1",
) -> Minio:
    """Prepare the MinIO client."""
    load_dotenv()

    access_key = access_key or os.getenv("MINIO_ACCESS_KEY")
    secret_key = secret_key or os.getenv("MINIO_SECRET_KEY")
    if not (access_key and secret_key):
        raise ValueError(
            "Set the 'MINIO_ACCESS_KEY' and 'MINIO_SECRET_KEY' environment variables."
            "Refer to the __doc__ at the top of this file for more information."
        )
    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
    )


def fetch_data(output_dir: Path | None = None) -> None:
    """Fetch data from the MinIO bucket and store it in the local _data directory."""
    data_dir = output_dir or Path(__file__).parent / "_data"

    client = prepare_client()

    download_directory(
        client=client,
        path_in_bucket="foo",
        output_dir=data_dir / "bar",
        bucket_name="hydromt-fiat",
        overwrite=True,
    )


if __name__ == "__main__":
    fetch_data()
