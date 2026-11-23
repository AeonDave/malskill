# Android traffic and custom protocols

Load when HTTPS interception still leaves opaque application data, a runtime hook must be correlated with a request, or a mobile finding crosses into a backend protocol.

## Establish the observed boundary

Record package/split hashes, OS API, target SDK, process, network stack, endpoint, test account and session. Keep the original package as a control when instrumentation or re-signing changes behavior. Treat proxy absence, TLS rejection and undecodable application bytes as separate failures.

| Observation | Next check | Insufficient conclusion |
|---|---|---|
| No request in the proxy | App action executed, process, routing, direct sockets, protocol and proxy support | The app uses pinning |
| TLS fails | Certificate chain, hostname, trust configuration, custom pinner, client certificate and native stack | Any Java trust hook will fix it |
| TLS succeeds, body is opaque | Content encoding, serializer, compression, application encryption and field-level transformations | TLS interception failed |
| A hook fires | Actual overload/call stack, direction, session and request correlation | The whole protocol is understood |
| A local method accepts input | Unmodified request accepted by the backend and its resulting state | Server authorization was bypassed |

For Android's configured trust stack, apps targeting API 24+ do not trust user-added CAs by default; inspect domain/base configuration. For a build you control, `debug-overrides` applies only when debuggable and can trust a test CA. A separate pinner or native/custom stack may enforce different checks. See [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config).

Trust options for the lab, lowest impact first: a debug build's `debug-overrides`; a repackaged NSC that trusts the test CA ([patch and sign](../../../offensive-coding/smali-dex-patching/references/apktool-rebuild-and-signing.md)); a rooted device or emulator with the lab CA installed as a system CA. On Android 14+ the store lives in the immutable APEX `/apex/com.android.conscrypt/cacerts` and overlaying it fails: mount a tmpfs over `/system/etc/security/cacerts`, populate it with the existing certs plus the new `<subject_hash_old>.0` file, then bind it over the APEX path inside zygote and each running app with `nsenter --mount=/proc/<pid>/ns/mnt -- /bin/mount --bind`. It lasts until reboot. See [HTTP Toolkit: Android 14 system CA](https://httptoolkit.com/blog/android-14-install-system-ca-certificate/).

On recent runtimes, include these in the diagnosis:

- Certificate Transparency is available as an opt-in on Android 16; Android 17 enables it by default for target 37+. Inspect the effective domain policy: user/custom trust anchors normally disable verification unless explicitly overridden. A CT rejection is distinct from pinning: on Android 17 a lab CA installed in the system store fails for target 37+ apps with `SSLPeerUnverifiedException: Certificate transparency failed` (`NOT_ENOUGH_SCTS`), unless the proxy issues SCTs from log providers trusted on the device or the app's NSC opts out. User-added CAs are exempt from CT but are not trusted by apps targeting 24+. See [Android 17 certificate transparency](https://httptoolkit.com/blog/android-17-certificate-transparency/).
- For a proxy reached through the LAN, check whether local-network permission applies and is granted. Android 17 enforces `ACCESS_LOCAL_NETWORK` for target 37+; a denied connection need not have reached TLS. See [Android 17 network changes](https://developer.android.com/about/versions/17/behavior-changes-17).
- Encrypted Client Hello is used for target 37+ when the app's network library and the server support it, and sent as GREASE otherwise: passive capture and SNI-based routing lose the hostname for those connections, an explicit proxy still sees it in `CONNECT`. Network Security Configuration gains a `<domainEncryption>` element.

Load [Frida mobile instrumentation](../../../offensive-tools/rev/frida/references/android-ios.md) for tool/runtime setup and for the hook point per stack with its limit: default Conscrypt trust, app-supplied managers, NSC `<pin-set>`, OkHttp, native engines. Record this baseline before any hook is loaded. Select the narrow boundary actually used: serializer, request builder or crypto call. Avoid starting with process-wide string logging; it can distort timing and collect unrelated credentials.

## Recover transformations without changing semantics

1. Capture one harmless test action end to end, then repeat it in a fresh session. Identify which fields are stable, per-request, per-session or account-dependent.
2. Follow bytes through each observed transformation. Record order, byte offsets, lengths, charset where justified, binary framing and content encoding. A MIME type or recognizable prefix is a hypothesis until a parser accepts the data.
3. To locate the method that builds a payload, enter a unique marker in the UI and hook `StringBuilder`/`StringBuffer` `toString` filtered to that marker, logging `Log.getStackTraceString(new Exception())`. Remove the hook once the site is known; an unfiltered string trace distorts timing.
4. Pair runtime events with a scoped request/operation identifier. Cipher objects can be reused and hash codes can collide; a global key list or timestamp alone is not reliable correlation.
5. For a crypto boundary, record the actual transformation, operation mode and parameter type. `Cipher` has no public op-mode getter: take it from the first `init` argument per cipher instance. A key whose `getEncoded()` returns null is unextractable, not empty. Do not treat every other mode as decrypt or cast every parameter object to an IV type. Keep authentication tags and additional authenticated data with the operation when applicable.
6. Cover the overloads and streaming calls actually exercised. A hook on only `doFinal(byte[])` misses `update`, output-buffer and `ByteBuffer` variants. No Java hook hit does not exclude native crypto or another process; a non-exportable key does not imply a failed operation. See [Cipher](https://developer.android.com/reference/javax/crypto/Cipher) and [Android Keystore](https://developer.android.com/privacy-and-security/keystore).
7. Preserve original return values, exceptions and buffer positions. Capture binary data as bytes with explicit lengths; do not UTF-8-decode keys or arbitrary ciphertext. Retain only data needed for the controlled test.
8. Validate a decoder/encoder with a captured fixture. Round-trip byte-for-byte for deterministic encodings; with randomness or fresh nonces, verify decoded structure and protocol acceptance instead of requiring identical ciphertext. A locally valid transformation still needs a fresh-session check.

Output a transformation map such as `request object → serializer → application envelope → HTTP body`, with evidence for each arrow. Mark unresolved transformations explicitly. Keep reproduction fixtures separate from live credentials.

## Validate the server-side claim

Once a client-side command or field reaches a backend, load [web-exploit-technique](../../web-exploit-technique/SKILL.md) for the relevant server-side test. Do not infer server trust from client validation, embedded command names or a runtime patch.

- Trace externally controlled input through parsing, normalization and authorization to the operation actually executed. Confirm that session/MAC/nonce handling accepts the request without changing its authorization context.
- Use a harmless marker and controlled test resource to demonstrate the claimed boundary. Distinguish local method execution, server-side script evaluation, OS command execution and Android-device compromise; evidence for one does not establish the next.
- When egress is unknown, climb the ladder: echo in the response, then an HTTP callback, then the DNS lookup of a unique label. DNS labels hold 63 octets and names 255, and UDP queries can be lost or reordered: chunk, number the chunks and resend. A callback proves only the observation tied to that request; DNS resolution alone does not establish network reachability or OS command execution. Use server-side logs where available to resolve ambiguity.
- Preserve expected rejection controls and the unchanged app behavior. Report reproducible impact and remaining assumptions, not the name of a suspected vulnerability class.

The [Voorivex case report](https://blog.voorivex.team/from-an-android-hook-to-rce-5000-bounty) is an example of a mobile client exposing a backend protocol. Its reported server-side execution is not an Android platform RCE. The linked [hooks at revision 38aa763](https://github.com/VoorivexTeam/from-an-Android-Hook-to-RCE-5000-bounty/tree/38aa76391d03bc69c26a5eaeec2c2b835221d6a8/hooks) are historical examples: review their runtime/API assumptions before reuse; a universal trust-bypass claim is not a coverage guarantee.
