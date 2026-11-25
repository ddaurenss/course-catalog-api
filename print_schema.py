"""Print the GraphQL schema as SDL."""

from graphql_api import schema

print(schema.as_str())
