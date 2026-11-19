import json
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('AIJobs')

def lambda_handler(event, context):
    position = event.get('queryStringParameters', {}) or {}
    position = position.get('position', '').strip()

    if position:
        response = table.get_item(
            Key={'JobTitle': position}
        )
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': f"Position '{position}' not found"})
            }

        return {
            'statusCode': 200,
            'body': json.dumps({'job_requirement': item['JobRequirements']})
        }

    # No position param — return all jobs
    response = table.scan()
    items = response.get('Items', [])

    jobs = [
        {
            'job_title': item['JobTitle'],
            'job_requirement': item['JobRequirements']
        }
        for item in items
    ]

    return {
        'statusCode': 200,
        'body': json.dumps(jobs)
    }
