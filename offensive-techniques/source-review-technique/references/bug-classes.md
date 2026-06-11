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
- **Python**: `pickle.loads(`, `yaml.load(`, `yaml.unsafe_load(`
- **Java**: `ObjectInputStream.readObject(`, `XMLDecoder.readObject(`, `XStream.fromXML(`
- **PHP**: `unserialize(`
- **C#**: `BinaryFormatter.Deserialize(`, `JsonConvert.DeserializeObject(` (with TypeNameHandling)

## 4. SQL Injection
- **Keywords**: `SELECT * FROM`, `UPDATE`, `INSERT INTO` combined with string formatting or concatenation (`+`, `%s` without parameterization).
- **ORM bypasses**: Look for raw query execution functions like `.executeRaw(`, `.rawQuery(`.

## 5. Server-Side Request Forgery (SSRF)
- **Keywords**: `curl(`, `requests.get(`, `HttpURLConnection`, `fetch(`, `urllib.request.urlopen(`
- **Taint**: Does the URL stem from a parameter, header (`X-Forwarded-Host`), or an external object?
