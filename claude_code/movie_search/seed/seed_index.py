"""
Run once after CDK deploy to create the OpenSearch index and bulk-load movie data.

Usage:
    python seed_index.py --endpoint <opensearch-endpoint>

The endpoint is printed by `cdk deploy` as the OpenSearchEndpoint output.
"""
import json
import argparse
import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.helpers import bulk

INDEX_NAME = "movies"

MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
    },
    "mappings": {
        "properties": {
            "title":            {"type": "text", "analyzer": "standard"},
            "plot":             {"type": "text", "index": False},
            "directors":        {"type": "keyword"},
            "actors":           {"type": "keyword"},
            "genres":           {"type": "keyword"},
            "rating":           {"type": "float"},
            "rank":             {"type": "integer"},
            "year":             {"type": "integer"},
            "running_time_secs":{"type": "integer"},
            "release_date":     {"type": "date"},
            "image_url":        {"type": "keyword", "index": False},
            "id":               {"type": "keyword"},
            "type":             {"type": "keyword"},
        }
    },
}


def get_client(endpoint):
    session = boto3.Session()
    credentials = session.get_credentials().get_frozen_credentials()
    region = session.region_name or "us-east-1"
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        "es",
        session_token=credentials.token,
    )
    return OpenSearch(
        hosts=[{"host": endpoint, "port": 443}],
        http_auth=awsauth,
        http_compress=True,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def load_bulk_json(path):
    """Parse alternating action/document lines from NDJSON bulk file."""
    actions = []
    with open(path) as f:
        lines = [line.strip() for line in f if line.strip()]
    i = 0
    while i < len(lines):
        meta = json.loads(lines[i])
        doc  = json.loads(lines[i + 1])
        action = {
            "_index": meta["index"]["_index"],
            "_id":    meta["index"]["_id"],
            **doc,
        }
        actions.append(action)
        i += 2
    return actions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True,
                        help="OpenSearch domain endpoint (no https://)")
    args = parser.parse_args()

    client = get_client(args.endpoint)

    # Recreate index
    if client.indices.exists(index=INDEX_NAME):
        print(f"Index '{INDEX_NAME}' already exists — deleting and recreating.")
        client.indices.delete(index=INDEX_NAME)

    client.indices.create(index=INDEX_NAME, body=MAPPING)
    print(f"Index '{INDEX_NAME}' created.")

    # Bulk load
    actions = load_bulk_json("movies.json")
    success, errors = bulk(client, actions)
    print(f"Indexed {success} movies.")
    if errors:
        print(f"Errors: {errors}")

    client.indices.refresh(index=INDEX_NAME)
    print("Done.")


if __name__ == "__main__":
    main()
