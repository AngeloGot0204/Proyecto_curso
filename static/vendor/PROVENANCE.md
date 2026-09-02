# Vendored third-party JavaScript

These three libraries were loaded from public CDNs (`unpkg.com`,
`cdn.jsdelivr.net`) on authenticated wizard screens, with no `integrity`
attribute and — in Dexie's case — a floating major version. A compromised
CDN, a compromised upstream npm package, or a malicious 3.x release would
have executed arbitrary JavaScript in a logged-in user's browser, with full
access to the DOM, the CSRF token, and every value being captured.
`crossorigin="anonymous"` does not prevent that: it enables CORS, not
integrity checking. See `SECURITY-REPORT.md` F-02.

Vendoring them here removes the runtime dependency on a third party
entirely, which is stronger than pinning a hash: there is no request to
verify. It also fixes a second, non-security problem the CDN caused — a
first visit without signal never obtained Dexie, so the offline layer could
not initialize on exactly the device it exists for.

Files are **byte-identical to upstream**; nothing was reformatted or
re-minified, so the checksums below verify against the source URLs. Follows
the provenance convention `static/css/tokens.css` already established for
the self-hosted IBM Plex Mono fonts (release tag + per-file SHA-256 +
licence).

## Manifest

| File | Package | Version | Licence |
|---|---|---|---|
| `dexie.js` | [dexie](https://dexie.org) | 3.2.7 | Apache-2.0 |
| `heic2any.min.js` | [heic2any](https://github.com/alexcorvi/heic2any) | 0.0.4 | MIT |
| `browser-image-compression.js` | [browser-image-compression](https://github.com/Donaldcwl/browser-image-compression) | 2.0.2 | MIT |

### Source URLs

```
https://unpkg.com/dexie@3.2.7/dist/dexie.js
https://cdn.jsdelivr.net/npm/heic2any@0.0.4/dist/heic2any.min.js
https://cdn.jsdelivr.net/npm/browser-image-compression@2.0.2/dist/browser-image-compression.js
```

### SHA-256

```
fd9b01ab42221a1da3543ea3393f11ad6ceb32634251215895399fac93d1f520  dexie.js
0963cfa50e9e1e7e6af929a40a81e3e898a673f1270eafa6917dd137e4968164  heic2any.min.js
c6713a21756570af4c230f706faac4f0187845928bd14fd5910210d1cdc6fb87  browser-image-compression.js
```

Verify with `sha256sum static/vendor/*.js` (or `Get-FileHash -Algorithm SHA256`).

Attribution and licence text for Dexie and browser-image-compression ship
inside their own file headers, which are preserved verbatim. `heic2any` is
distributed minified without a header; it is MIT-licensed, © Alex Corvi,
per its repository.

## Upgrading

1. Download the new version from the same registry, to the same filename.
2. Update the version and SHA-256 rows above.
3. Run the suite — `reportes/tests/test_estatico.py` asserts that no
   template loads a script from a foreign origin, so a reintroduced CDN tag
   fails there rather than in production.
