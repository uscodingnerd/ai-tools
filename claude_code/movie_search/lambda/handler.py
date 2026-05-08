import json
import os
import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection

OPENSEARCH_ENDPOINT = os.environ["OPENSEARCH_ENDPOINT"]
INDEX_NAME = "movies"

session = boto3.Session()
credentials = session.get_credentials().get_frozen_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    os.environ.get("AWS_REGION", "us-east-1"),
    "es",
    session_token=credentials.token,
)

client = OpenSearch(
    hosts=[{"host": OPENSEARCH_ENDPOINT, "port": 443}],
    http_auth=awsauth,
    http_compress=True,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

SOURCE_FIELDS = ["title", "plot", "rating", "year", "genres", "actors",
                 "directors", "image_url", "running_time_secs", "rank"]


def lambda_handler(event, context):
    query = (event.get("queryStringParameters") or {}).get("q", "").strip()

    if not query:
        return _response(400, {"error": "Missing required query parameter: q"})

    result = client.search(
        index=INDEX_NAME,
        body={
            "query": {
                "match": {
                    "title": {
                        "query": query,
                        "operator": "or",
                    }
                }
            },
            "_source": SOURCE_FIELDS,
            "size": 20,
        },
    )

    movies = [hit["_source"] for hit in result["hits"]["hits"]]
    return _response(200, {"results": movies, "total": result["hits"]["total"]["value"]})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body),
    }
