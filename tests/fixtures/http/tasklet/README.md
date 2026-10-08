Synthetic "Tasklet" website for discover tests, one folder per host. The test server routes by the
`Host` header. Never put real third-party content here.

- tasklet.example: robots disallows /admin/ and /private/; sitemap index → pages + docs (gzipped at
  test time) + blog; homepage links include disallowed, off-site and redirecting URLs.
- docs.tasklet.example: own robots + sitemap.
- status.tasklet.example: no robots.txt (404 → allowed).
- developers.tasklet.example: robots.txt 403 → everything disallowed.
- api.tasklet.example: server error on / (probe not live). Other probed subdomains do not resolve.
