# Azure Service Quick Reference

Use this reference when `cloud-ctf` is active and the task provides Azure credentials, tenant/subscription context, a managed-identity shell, a storage URL, a SAS token, or a Key Vault clue.

## Identity and subscription context

```bash
az account show
az account list --output table
az account set --subscription <subscription-id>
az ad signed-in-user show
```

Record tenant ID, subscription ID, user/service principal object ID, and default resource group before pivoting.

## RBAC and scope enumeration

```bash
az role assignment list --assignee <object-id> --all --output table
az role assignment list --scope /subscriptions/<subscription-id> --output table
az group list --output table
```

Check assignments at subscription, resource group, and resource scope. Management-plane visibility does not automatically mean data-plane access.

## Storage accounts and blobs

```bash
az storage account list --output table
az storage container list --account-name <account> --auth-mode login --output table
az storage blob list --account-name <account> --container-name <container> --auth-mode login --output table
az storage blob download --account-name <account> --container-name <container> --name <blob> --file <out> --auth-mode login
```

If a SAS URL is provided, parse:

- `sp`: permissions such as read, list, write, delete
- `sr` or `srt`: signed resource or resource types
- `se`: expiry
- `sig`: signature presence

Then test the narrowest expected action first: list container, list blob versions, or download a named blob.

## Blob versions, snapshots, and soft delete

```bash
az storage blob list \
  --account-name <account> \
  --container-name <container> \
  --include v \
  --auth-mode login \
  --output table

az storage blob download \
  --account-name <account> \
  --container-name <container> \
  --name <blob> \
  --version-id <version-id> \
  --file <out> \
  --auth-mode login
```

Deleted or overwritten blobs are common CTF pivot points; check versions before concluding a container is empty.

## Key Vault

```bash
az keyvault list --output table
az keyvault secret list --vault-name <vault> --output table
az keyvault secret show --vault-name <vault> --name <secret>
az keyvault secret list-versions --vault-name <vault> --name <secret> --output table
az keyvault secret show --vault-name <vault> --name <secret> --version <version-id>
```

Check secret versions and certificate objects. Older values often contain previous passwords, tokens, or TOTP seeds.

## Managed identity from an isolated VM/container shell

```bash
curl -H Metadata:true \
  'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/'
```

Use the token only inside authorized lab scope. Decode token claims to identify principal, tenant, audience, and expiry before making API calls.

## Validation signals

- recovered blob, secret, certificate, key material, or configuration value
- older version proves deleted or rotated data recovery
- role assignment explains why a pivot is possible
- managed-identity token maps to a principal with the required scope
