"""S3-compatible blob storage: Cloudflare R2 in production (plan v2, A7), any S3 elsewhere.

R2: endpoint https://<account id>.r2.cloudflarestorage.com, region "auto", and an R2 API
token's access key id and secret in AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY (boto3 reads
them from the environment; they are never in config.yaml).

Every object write is atomic on S3, which is what the local store gets from a rename.
Parsers and pdfium need a real file, so `local_path` downloads an object once into a
cache folder; originals are named by their content hash and never change, so the cache
never goes stale.
"""

import threading
from pathlib import Path

from hyper_rag.stores.blob import check_key


class S3BlobStore:
    name = "s3"

    def __init__(
        self,
        bucket: str,
        cache_dir: Path,
        endpoint_url: str = "",
        region: str = "auto",
        prefix: str = "",
        client=None,
    ):
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url or None,
                region_name=region,
                config=Config(retries={"max_attempts": 5, "mode": "standard"}),
            )
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/") + "/" if prefix.strip("/") else ""
        self.cache_dir = cache_dir
        self._lock = threading.Lock()

    def _key(self, key: str) -> str:
        return self.prefix + check_key(key)

    def _missing(self, error) -> bool:
        code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
        return code in ("404", "NoSuchKey", "NotFound")

    def read_bytes(self, key: str) -> bytes:
        from botocore.exceptions import ClientError

        try:
            return self.client.get_object(Bucket=self.bucket, Key=self._key(key))["Body"].read()
        except ClientError as error:
            if self._missing(error):
                raise KeyError(key) from None
            raise

    def write_bytes(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=self._key(key), Body=data)

    def write_file(self, key: str, source: Path, move: bool = False) -> None:
        # upload_file switches to a multipart upload for big files on its own.
        self.client.upload_file(str(source), self.bucket, self._key(key))
        if move:
            cached = self.cache_dir / check_key(key)
            cached.parent.mkdir(parents=True, exist_ok=True)
            try:
                source.replace(cached)  # keep it as the local copy: no download later
            except OSError:
                source.unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except ClientError as error:
            if self._missing(error):
                return False
            raise

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._key(key))
        cached = self.cache_dir / check_key(key)
        if cached.is_file():
            cached.unlink()

    def _keys(self, prefix: str) -> list[str]:
        full = self._key(prefix.rstrip("/")) + "/"
        keys = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=full):
            keys += [item["Key"] for item in page.get("Contents", [])]
        return keys

    def delete_prefix(self, prefix: str) -> None:
        keys = self._keys(prefix)
        self.delete(prefix.rstrip("/"))  # the prefix may also name a single object
        for start in range(0, len(keys), 1000):
            batch = [{"Key": key} for key in keys[start : start + 1000]]
            self.client.delete_objects(Bucket=self.bucket, Delete={"Objects": batch})
        import shutil

        shutil.rmtree(self.cache_dir / check_key(prefix.rstrip("/")), ignore_errors=True)

    def list(self, prefix: str) -> list[str]:
        return sorted(key[len(self.prefix) :] for key in self._keys(prefix))

    def local_path(self, key: str) -> Path:
        path = self.cache_dir / check_key(key)
        with self._lock:
            if not path.is_file():
                from botocore.exceptions import ClientError

                path.parent.mkdir(parents=True, exist_ok=True)
                partial = path.with_name(path.name + ".part")
                try:
                    self.client.download_file(self.bucket, self._key(key), str(partial))
                except ClientError as error:
                    if self._missing(error):
                        raise KeyError(key) from None
                    raise
                partial.replace(path)
        return path
