# Common Bug Classes and Sink Patterns

**Load when**: Scanning a codebase and needing precise keywords/sinks to feed into structural search (grep) to initiate data-flow evaluation.

## 1. Command Injection (OS injection)
- **C/C++**: `system(`, `popen(`, `exec(`, `execl(`, `execvp(`
- **Python**: `subprocess.run(`, `os.system(`, `os.popen(`, `pty.spawn(`
- **Java**: `Runtime.getRuntime().exec(`, `ProcessBuilder(`
- **Node.js**: `child_process.exec(`, `spawn(`

## 2. Path Traversal & Arbitrary File Read/Write
- **Keywords**: `open(`, `fopen(`, `FileReader(`, `fs.readFile(`, `include(`, `require(`
- **Red flags**: Direct concatenation with parameters, e.g., `open(base_path + user_input)`

## 3. Deserialization
- **Python**: `pickle.loads(`, `yaml.load(` without `SafeLoader`, `yaml.unsafe_load(`, `jsonpickle.decode(`
- **Java**: `ObjectInputStream.readObject(`, `XMLDecoder.readObject(`, `XStream.fromXML(`
  - **SnakeYAML < 2.0** (CVE-2022-1471): `new Yaml().load(`, `new Yaml(new Constructor(...)).load(` — arbitrary class instantiation.
  - **Jackson polymorphic**: `enableDefaultTyping(`, `@JsonTypeInfo(use = Id.CLASS)` on attacker-controlled fields.
- **PHP**: `unserialize(`, `phar://` stream wrappers reaching filesystem sinks.
- **Ruby**: `Marshal.load(`, `YAML.load(` (aliases `YAML.unsafe_load(`), `Oj.load(` with default mode.
- **C#**: `BinaryFormatter.Deserialize(`, `SoapFormatter.Deserialize(`, `NetDataContractSerializer.ReadObject(`, `LosFormatter.Deserialize(`, `JsonConvert.DeserializeObject(` with `TypeNameHandling.All`/`Objects`/`Auto`, `JavaScriptSerializer` with a custom `SimpleTypeResolver`.

## 4. SQL Injection
- **Keywords**: `SELECT * FROM`, `UPDATE`, `INSERT INTO` combined with string formatting or concatenation (`+`, `%s`, f-strings, template literals) without parameterization.
- **ORM raw-escape sinks** (parameterized by default — dangerous only when the query text itself is built from tainted input):
  - **Prisma**: `$queryRawUnsafe(`, `$executeRawUnsafe(`; also `$queryRaw` / `$executeRaw` when the template argument is built with `Prisma.raw(` or plain string concat instead of a tagged literal.
  - **TypeORM**: `.query(`, `createQueryBuilder().where("col = '" + x + "'")`, `.orderBy(userInput)` (identifier injection).
  - **Sequelize**: `sequelize.query(` with a plain string, `{ replacements }` bypassed by manual concat, `where: literal(userInput)`.
  - **SQLAlchemy**: `text(f"...{x}...")`, `connection.execute(f"...")`, `.filter(text(...))`, `.order_by(text(userInput))`.
  - **Django ORM**: `Model.objects.raw(`, `.extra(where=[..], select={..})`, `RawSQL(`.
  - **MongoDB**: `$where: userInput`, `mapReduce({ scope: userInput })`, `db.eval(` (legacy).

## 5. Server-Side Request Forgery (SSRF)
- **Keywords**: `curl(`, `requests.get(`, `HttpURLConnection`, `fetch(`, `axios.get(`, `got(`, `undici.request(`, `urllib.request.urlopen(`, `http.NewRequest(`, `WebClient.DownloadString(`, `HttpClient.GetAsync(`.
- **Taint**: Does the URL stem from a parameter, header (`X-Forwarded-Host`, `X-Forwarded-For`, `Referer`), webhook config, or a persisted external object?
- **Cloud-metadata gadgets** (highest impact): `169.254.169.254` (AWS/GCP/Azure/OpenStack), `fd00:ec2::254` (IMDSv6), `metadata.google.internal`, `100.100.100.200` (Alibaba). Check for IMDSv2 token flow bypass via full response proxying and `X-Forwarded-For`-based allowlists.
- **Allowlist/blocklist bypass gadgets**: `127.1`, `2130706433` (decimal), `0x7f000001` (hex), `017700000001` (octal), `[::1]`, `[::ffff:127.0.0.1]`, `localhost.<attacker.tld>`, DNS rebinding, redirect chains (302 → internal), URL parser confusion (`http://a@evil@target/`, backslash-vs-slash, unicode dots).
- **Node.js**: `ip` package `isPrivate`/`isPublic` (CVE-2023-42282 — `0x7f.1` bypass), stale versions of `private-ip`, `netmask`.

## 6. Front-End Sinks (XSS / DOM Manipulation)
- **Angular**: `bypassSecurityTrustHtml`, `[innerHTML]`, `$eval`, `$evalAsync`
- **React**: `dangerouslySetInnerHTML`
- **Native JS**: `document.write(`, `eval(`, `setTimeout(`

## 7. PHP Specific Sources and Sinks
- **Sources**: `$_GET`, `$_POST`, `$_REQUEST`, `$_SERVER`, `php://input`
- **Sinks**: `echo`, `print`, `system(`, `exec(`, `passthru(`, `eval(`, `unserialize(`

## 8. Prototype Pollution (Node.js)
- **Deep-merge / set-by-path sinks**: `_.merge(`, `_.mergeWith(`, `_.defaultsDeep(`, `_.set(`, `_.setWith(`, `_.zipObjectDeep(` (lodash); `object-path`, `set-value`, `mixin-deep`, `dot-prop`, `deepmerge`, `hoek.applyToDefaults`, `jQuery.extend(true, ...)`.
- **Direct assignment**: `obj[userKey] = value`, `Object.assign({}, req.body)`, `Object.setPrototypeOf(`, `Reflect.set(`.
- **Tainted keys to grep**: `__proto__`, `constructor`, `prototype`.
- **Impact bridges**: EJS/Pug/Handlebars options, `child_process.spawn` `env`/`shell` options, Express `res.render` locals, `mongoose` schema options — a polluted `Object.prototype` reaches these to gain RCE / auth bypass.

## 9. Java Reachability / Native-Image Metadata Abuse
- **Config files** (GraalVM `native-image`): `reflect-config.json`, `serialization-config.json`, `resource-config.json`, `jni-config.json`, `proxy-config.json`, `predefined-classes-config.json` (also unified `reachability-metadata.json`).
- **Risk**: An attacker with commit/PR access to these files (supply chain, poisoned dependency, forgotten tracing-agent output) can register arbitrary classes for reflective/serial construction, silently keeping deserialization gadget chains (e.g. `ysoserial`-style) reachable in the final native image even after the library itself is patched.
- **Grep**: `"name"\s*:\s*"[A-Za-z_.$]+"` entries pointing at `sun.*`, `javax.management.*`, `org.apache.commons.*`, `com.sun.rowset.*`, custom `readObject`/`InvocationHandler` classes.
