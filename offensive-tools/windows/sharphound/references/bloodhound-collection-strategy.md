# SharpHound coverage and data quality

- **Default:** collects directory relationships and attempts local group and session data from domain-joined computers. Unreachable hosts or insufficient permissions can limit results.
- **DCOnly:** gathers directory data from domain controllers; it does not directly collect member-computer sessions or local group membership. Do not interpret missing host edges as proof that they do not exist.
- **Session:** session information reflects a point in time and changes as users log on and off. Check collection time before relying on a result.

Review collector output and errors, domain scope, DNS, connectivity and permissions. Compare coverage with the [SharpHound data and permissions reference](https://bloodhound.specterops.io/collect-data/sharphound-data-permissions) for the deployed version. Resolve missing coverage before drawing conclusions from an incomplete graph.
