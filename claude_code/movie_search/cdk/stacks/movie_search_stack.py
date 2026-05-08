import os
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_opensearchservice as opensearch,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
)
from constructs import Construct


class MovieSearchStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        lambda_dir = os.path.join(os.path.dirname(__file__), "..", "..", "lambda")
        lambda_dir = os.path.normpath(lambda_dir)

        # --- OpenSearch Domain ---
        domain = opensearch.Domain(
            self, "MovieSearchDomain",
            version=opensearch.EngineVersion.OPENSEARCH_2_11,
            capacity=opensearch.CapacityConfig(
                data_nodes=1,
                data_node_instance_type="t3.small.search",
            ),
            ebs=opensearch.EbsOptions(
                enabled=True,
                volume_size=10,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            enforce_https=True,
            node_to_node_encryption=True,
            encryption_at_rest=opensearch.EncryptionAtRestOptions(enabled=True),
            access_policies=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AccountPrincipal(self.account)],
                    actions=["es:ESHttp*"],
                    resources=["*"],
                )
            ],
        )

        # --- Lambda Function ---
        search_fn = _lambda.Function(
            self, "MovieSearchFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=_lambda.Code.from_asset(lambda_dir),
            timeout=Duration.seconds(15),
            environment={
                "OPENSEARCH_ENDPOINT": domain.domain_endpoint,
            },
        )

        # Grant Lambda access to read/write the OpenSearch domain (search uses POST)
        domain.grant_read_write(search_fn)

        # --- API Gateway ---
        api = apigw.RestApi(
            self, "MovieSearchApi",
            rest_api_name="MovieSearchApi",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
            ),
        )

        search_resource = api.root.add_resource("search")
        search_resource.add_method("GET", apigw.LambdaIntegration(search_fn, proxy=True))

        # --- Outputs ---
        CfnOutput(self, "ApiUrl",
                  value=f"{api.url}search",
                  description="API Gateway search endpoint")
        CfnOutput(self, "OpenSearchEndpoint",
                  value=domain.domain_endpoint,
                  description="OpenSearch domain endpoint")
