# pibooth share page (Cloudflare Worker)

A small Cloudflare Worker that gives every booth picture its own share page.
The booth QR code opens the page on the guest's phone, where they can:

- **See** the picture and **save** it.
- **Get the link by email**: they type their address, the Worker sends the link
  through [Amazon SES](https://aws.amazon.com/ses/), [Resend](https://resend.com)
  or [Brevo](https://www.brevo.com). The
  address is only used to send the mail and is not stored.

The pictures are read straight from the R2 bucket filled by the
`plugins/pibooth_r2_upload.py` plugin, so the bucket does not need public access.

```
booth ──upload──▶ R2 bucket ◀──binding── Worker (photo.example.com)
  │                                        ▲
  └── QR: https://photo.example.com/p/<picture> ── guest phone
```

| Route | Purpose |
|---|---|
| `GET /p/<key>` | Share page. While the upload is still running it refreshes every 3 seconds (for about a minute). |
| `GET /i/<key>` | The picture, inline. |
| `GET /d/<key>` | The picture, as a download. |
| `POST /api/send` | `{"key", "email"}`: mail the share link. Rate limited per IP. |

`<key>` is the R2 object key: the picture file name, preceded by the `[R2]
key_prefix` when one is set.

## Setup

1. **Mail provider** (pick one):
   - *Amazon SES* (about $0.10 per 1,000 mails, out of the sandbox): verify
     your domain (3 DKIM CNAME records), then create an IAM user allowed only
     `ses:SendEmail` on `identity/<domain>` and `identity/*@<domain>`, and an
     access key for it. Never use root keys.
   - *Resend* (free: 100 mails/day, 3,000/month): add and verify your domain
     (the DNS records are added in one click when the domain is on Cloudflare),
     then create an API key.
   - *Brevo* (free: 300 mails/day): verify a sender address (and preferably
     your domain), then create an API key.

2. **Configure** `wrangler.toml`, copied from the template (`cp wrangler.example.toml wrangler.toml`,
   not committed): the share domain in `routes`, the bucket name
   (same as `[R2] bucket`), `EVENT_NAME`, `FROM_EMAIL` (an address of the
   verified domain/sender) and, for SES, `AWS_REGION`. When several providers
   are configured, SES is used first, then Resend, then Brevo.

3. **Deploy**:

   ```bash
   cd share-worker
   npx wrangler login
   npx wrangler secret put AWS_ACCESS_KEY_ID       # Amazon SES, with
   npx wrangler secret put AWS_SECRET_ACCESS_KEY   # AWS_REGION in wrangler.toml
   # or: npx wrangler secret put RESEND_API_KEY (or BREVO_API_KEY)
   npm run deploy    # refuses while wrangler.toml still has an example value
   ```

4. **Point the booth QR code to the page** in `pibooth.cfg`:

   ```ini
   [QRCODE]
   prefix_url = https://photo.example.com/p/{key}
   ```

   `{key}` is the uploaded object key (random by default with `[R2] random_names`,
   `[R2] key_prefix` included). With `random_names = False`, `{picture}` (the
   local file name) also works, with the key prefix written before it:
   `https://photo.example.com/p/2026-wedding/{picture}`.

## Limits

- Picture names come from the capture time, so share links can be guessed by
  someone walking through timestamps (the same is true of a public R2 bucket).
- `key_prefix` may only use letters, digits and `. _ - /`.
- Only image keys (`.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`) are served.
- Mails: 30 per minute per IP, 3 per minute per recipient, and only from the
  share page itself (`Origin` check).

## Development

```bash
npm test            # unit tests (Node 18+, no dependency)
npx wrangler dev    # local server with a remote/preview bucket
```
