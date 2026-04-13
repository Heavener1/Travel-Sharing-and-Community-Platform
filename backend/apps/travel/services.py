from pathlib import Path
from uuid import uuid4
import json
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from elasticsearch import Elasticsearch
from minio import Minio

from apps.travel.models import Destination


def get_minio_client():
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_bucket():
    client = get_minio_client()
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)
    public_read_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET}"],
            },
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{settings.MINIO_BUCKET}/*"],
            },
        ],
    }
    client.set_bucket_policy(settings.MINIO_BUCKET, json.dumps(public_read_policy))
    return client


def upload_fileobj(file_obj, folder="uploads"):
    client = ensure_bucket()
    suffix = Path(file_obj.name).suffix or ".bin"
    object_name = f"{folder}/{uuid4().hex}{suffix}"
    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)
    client.put_object(
        settings.MINIO_BUCKET,
        object_name,
        file_obj,
        length=size,
        content_type=getattr(file_obj, "content_type", "application/octet-stream"),
    )
    return {
        "object_name": object_name,
        "reference": build_object_reference(object_name),
        "url": get_object_url(object_name),
    }


def build_object_reference(object_name):
    return f"minio://{settings.MINIO_BUCKET}/{object_name}"


def get_object_url(object_name):
    client = ensure_bucket()
    return client.presigned_get_object(
        settings.MINIO_BUCKET,
        object_name,
        expires=timedelta(days=7),
    )


def resolve_media_url(url):
    if not url:
        return url
    try:
        if url.startswith("minio://"):
            remainder = url.split("://", 1)[1]
            bucket, object_name = remainder.split("/", 1)
            if bucket == settings.MINIO_BUCKET:
                return get_object_url(object_name)
            return url
        parsed = urlparse(url)
        marker = f"/{settings.MINIO_BUCKET}/"
        if marker not in parsed.path:
            return url
        object_name = parsed.path.split(marker, 1)[1]
        return get_object_url(object_name)
    except Exception:
        return url


def get_es_client():
    if not settings.ELASTICSEARCH_ENABLED:
        raise RuntimeError("ElasticSearch is disabled")
    return Elasticsearch(settings.ELASTICSEARCH_URL, request_timeout=10)


def index_destination(destination):
    client = get_es_client()
    client.index(
        index=settings.ELASTICSEARCH_INDEX,
        id=destination.id,
        document={
            "name": destination.name,
            "city": destination.city,
            "province": destination.province,
            "summary": destination.summary,
            "tags": destination.tags,
            "budget_level": destination.budget_level,
            "best_season": destination.best_season,
            "score": float(destination.score),
            "is_hidden_gem": destination.is_hidden_gem,
            "cover": destination.cover,
        },
    )


def rebuild_destination_index():
    client = get_es_client()
    if client.indices.exists(index=settings.ELASTICSEARCH_INDEX):
        client.indices.delete(index=settings.ELASTICSEARCH_INDEX)
    client.indices.create(
        index=settings.ELASTICSEARCH_INDEX,
        mappings={
            "properties": {
                "name": {"type": "text"},
                "city": {"type": "text"},
                "province": {"type": "keyword"},
                "summary": {"type": "text"},
                "tags": {"type": "text"},
                "budget_level": {"type": "keyword"},
                "best_season": {"type": "keyword"},
                "score": {"type": "float"},
                "is_hidden_gem": {"type": "boolean"},
                "cover": {"type": "keyword"},
            }
        },
    )
    for destination in Destination.objects.all():
        index_destination(destination)


def search_destination_ids(keyword):
    client = get_es_client()
    response = client.search(
        index=settings.ELASTICSEARCH_INDEX,
        query={
            "multi_match": {
                "query": keyword,
                "fields": ["name^3", "city^2", "summary", "tags^2"],
            }
        },
        size=20,
    )
    return [int(hit["_id"]) for hit in response["hits"]["hits"]]
