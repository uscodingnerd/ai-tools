import aws_cdk as cdk
from stacks.movie_search_stack import MovieSearchStack

app = cdk.App()
MovieSearchStack(app, "MovieSearchStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    )
)
app.synth()
