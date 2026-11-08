# BloodHound CE graph queries

In Explore's Cypher tab, start with a bounded read-only query and inspect the returned edge types. For example, `HasSession` runs from a computer to a user:

```cypher
MATCH (c:Computer)-[:HasSession]->(u:User)
RETURN c.name, u.name
LIMIT 25
```

The edge describes a session observed during collection; it may already have ended. Check the [edge reference](https://bloodhound.specterops.io/resources/edges/has-session) for semantics and the [API documentation](https://bloodhound.specterops.io/integrations/bloodhound-api/working-with-api) for current authentication and upload workflows. Do not assume a path exists or remains usable solely because a graph query returned it.
