// Tests of the share Worker with a fake R2 bucket and a mocked fetch.
// Run with: cd share-worker && npm test

import { test, beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import worker, { isValidKey, isValidEmail, signAwsRequest } from '../src/index.js';

const KEY = '2026-10-06-12-00-00_pibooth.jpg';

function makeEnv(overrides = {}) {
  const objects = new Map([[KEY, 'JPEGDATA'], ['event/a_pibooth.jpg', 'JPEG2']]);
  return {
    EVENT_NAME: 'Test Wedding',
    FROM_EMAIL: 'photo@example.com',
    RESEND_API_KEY: 're_test',
    BUCKET: {
      async head(key) { return objects.has(key) ? { key } : null; },
      async get(key) {
        return objects.has(key) ? { body: objects.get(key), httpMetadata: { contentType: 'image/jpeg' } } : null;
      },
    },
    ...overrides,
  };
}

function get(path, headers = {}) {
  return new Request(`https://photo.example.com${path}`, { headers });
}

function post(body, headers = {}) {
  return new Request('https://photo.example.com/api/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Origin: 'https://photo.example.com', ...headers },
    body: typeof body === 'string' ? body : JSON.stringify(body),
  });
}

let realFetch;
let mailCalls;

beforeEach(() => {
  realFetch = globalThis.fetch;
  mailCalls = [];
  globalThis.fetch = async (url, init) => {
    mailCalls.push({ url, init, body: JSON.parse(init.body) });
    return new Response('{"id":"1"}', { status: 200 });
  };
});

afterEach(() => {
  globalThis.fetch = realFetch;
});

test('key and email validation', () => {
  assert.ok(isValidKey(KEY));
  assert.ok(isValidKey('event/2026/a.jpg'));
  assert.ok(!isValidKey('../secret'));
  assert.ok(!isValidKey('a/../b'));
  assert.ok(!isValidKey('/abs'));
  assert.ok(!isValidKey('a b.jpg'));
  assert.ok(!isValidKey(''));
  assert.ok(!isValidKey(undefined));
  assert.ok(!isValidKey('config/secret.json'));
  assert.ok(isValidKey('a.PNG'));
  assert.ok(isValidEmail('guest@example.com'));
  assert.ok(!isValidEmail('guest@example'));
  assert.ok(!isValidEmail('a@b.c<script>'));
  assert.ok(!isValidEmail('x'.repeat(250) + '@a.com'));
});

test('share page shows the picture, download and email form', async () => {
  const res = await worker.fetch(get(`/p/${KEY}`, { 'Accept-Language': 'ko-KR,ko;q=0.9' }), makeEnv());
  assert.equal(res.status, 200);
  const body = await res.text();
  assert.match(body, new RegExp(`src="/i/${KEY}"`));
  assert.match(body, new RegExp(`href="/d/${KEY}"`));
  assert.match(body, /이메일로 링크 받기/);
  assert.match(body, /Test Wedding/);
});

test('share page with a key prefix', async () => {
  const res = await worker.fetch(get('/p/event/a_pibooth.jpg'), makeEnv());
  assert.equal(res.status, 200);
  assert.match(await res.text(), /src="\/i\/event\/a_pibooth.jpg"/);
});

test('pending page refreshes while the upload is not finished, then gives up', async () => {
  let res = await worker.fetch(get('/p/missing_pibooth.jpg'), makeEnv());
  assert.equal(res.status, 200);
  assert.match(await res.text(), /http-equiv="refresh" content="3;url=\/p\/missing_pibooth.jpg\?r=1"/);

  res = await worker.fetch(get('/p/missing_pibooth.jpg?r=20'), makeEnv());
  assert.equal(res.status, 404);
});

test('invalid keys are rejected', async () => {
  for (const path of ['/p/..%2Fx', '/i/a%20b.jpg', '/d/%E0%A4%A']) {
    const res = await worker.fetch(get(path), makeEnv());
    assert.equal(res.status, 404, path);
  }
});

test('picture is served inline and as a download', async () => {
  let res = await worker.fetch(get(`/i/${KEY}`), makeEnv());
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('Content-Type'), 'image/jpeg');
  assert.equal(res.headers.get('Content-Disposition'), null);
  assert.equal(await res.text(), 'JPEGDATA');

  res = await worker.fetch(get('/d/event/a_pibooth.jpg'), makeEnv());
  assert.equal(res.headers.get('Content-Disposition'), 'attachment; filename="a_pibooth.jpg"');

  res = await worker.fetch(get('/i/missing.jpg'), makeEnv());
  assert.equal(res.status, 404);
});

test('send mails the share link through Resend', async () => {
  const res = await worker.fetch(post({ key: KEY, email: ' guest@example.com ' }, { 'Accept-Language': 'ko' }), makeEnv());
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { ok: true });
  assert.equal(mailCalls.length, 1);
  const call = mailCalls[0];
  assert.equal(call.url, 'https://api.resend.com/emails');
  assert.equal(call.init.headers.Authorization, 'Bearer re_test');
  assert.deepEqual(call.body.to, ['guest@example.com']);
  assert.equal(call.body.from, 'Test Wedding <photo@example.com>');
  assert.match(call.body.subject, /Test Wedding/);
  assert.match(call.body.text, new RegExp(`https://photo.example.com/p/${KEY}`));
});

test('SigV4 signature matches botocore', async () => {
  // Reference produced with botocore.auth.SigV4Auth for the same request
  const headers = await signAwsRequest({
    accessKeyId: 'AKIDEXAMPLE', secretAccessKey: 'wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY',
    region: 'ap-northeast-2', service: 'ses',
  }, 'https://email.ap-northeast-2.amazonaws.com/v2/email/outbound-emails',
  JSON.stringify({ hello: '세계' }), new Date('2026-10-16T05:29:33Z'));
  assert.equal(headers['X-Amz-Date'], '20261016T052933Z');
  assert.equal(headers.Authorization, 'AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20261016/ap-northeast-2/ses/aws4_request, '
    + 'SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date, '
    + 'Signature=58679e1d5128c9b352378addcbbbfb6fa4e9d6a99917a08292f68828f74db9ae');
});

test('send uses Amazon SES when the AWS keys are set (before Resend)', async () => {
  const env = makeEnv({ AWS_ACCESS_KEY_ID: 'AKIDEXAMPLE', AWS_SECRET_ACCESS_KEY: 'secret', FROM_NAME: '포토부스' });
  const res = await worker.fetch(post({ key: KEY, email: 'guest@example.com' }), env);
  assert.equal(res.status, 200);
  assert.equal(mailCalls.length, 1);
  const { url, init, body } = mailCalls[0];
  assert.equal(url, 'https://email.ap-northeast-2.amazonaws.com/v2/email/outbound-emails');
  assert.match(init.headers.Authorization, /^AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE\/\d{8}\/ap-northeast-2\/ses\/aws4_request, /);
  assert.equal(body.FromEmailAddress, `=?UTF-8?B?${Buffer.from('포토부스').toString('base64')}?= <photo@example.com>`);
  assert.deepEqual(body.Destination, { ToAddresses: ['guest@example.com'] });
  assert.match(body.Content.Simple.Body.Text.Data, new RegExp(`https://photo.example.com/p/${KEY}`));
  assert.equal(body.Content.Simple.Subject.Charset, 'UTF-8');
});

test('SES region and ASCII sender name', async () => {
  const env = makeEnv({ AWS_ACCESS_KEY_ID: 'A', AWS_SECRET_ACCESS_KEY: 'S', AWS_REGION: 'us-east-1' });
  await worker.fetch(post({ key: KEY, email: 'guest@example.com' }), env);
  assert.equal(mailCalls[0].url, 'https://email.us-east-1.amazonaws.com/v2/email/outbound-emails');
  assert.equal(mailCalls[0].body.FromEmailAddress, '"Test Wedding" <photo@example.com>');
});

test('send uses Brevo when only its key is set', async () => {
  const env = makeEnv({ RESEND_API_KEY: undefined, BREVO_API_KEY: 'xkeysib' });
  const res = await worker.fetch(post({ key: KEY, email: 'guest@example.com' }), env);
  assert.equal(res.status, 200);
  assert.equal(mailCalls[0].url, 'https://api.brevo.com/v3/smtp/email');
  assert.equal(mailCalls[0].init.headers['api-key'], 'xkeysib');
  assert.deepEqual(mailCalls[0].body.to, [{ email: 'guest@example.com' }]);
});

test('send rejects bad input without mailing', async () => {
  const env = makeEnv();
  const cases = [
    [post('not json'), 400, 'failed'],
    [post({ key: KEY, email: 'nope' }), 400, 'invalid'],
    [post({ key: '../x', email: 'guest@example.com' }), 400, 'failed'],
    [post({ key: 'missing.jpg', email: 'guest@example.com' }), 404, 'failed'],
  ];
  for (const [req, status, error] of cases) {
    const res = await worker.fetch(req, env);
    assert.equal(res.status, status);
    assert.equal((await res.json()).error, error);
  }
  assert.equal(mailCalls.length, 0);
});

test('send is rate limited per IP', async () => {
  const seen = [];
  const env = makeEnv({ SEND_LIMITER: { async limit({ key }) { seen.push(key); return { success: false }; } } });
  const res = await worker.fetch(post({ key: KEY, email: 'guest@example.com' }, { 'CF-Connecting-IP': '1.2.3.4' }), env);
  assert.equal(res.status, 429);
  assert.equal((await res.json()).error, 'tooMany');
  assert.deepEqual(seen, ['1.2.3.4']);
  assert.equal(mailCalls.length, 0);
});

test('send refuses other origins and big bodies', async () => {
  const body = { key: KEY, email: 'guest@example.com' };
  assert.equal((await worker.fetch(post(body, { Origin: 'https://evil.example' }), makeEnv())).status, 403);
  const noOrigin = new Request('https://photo.example.com/api/send', { method: 'POST', body: JSON.stringify(body) });
  assert.equal((await worker.fetch(noOrigin, makeEnv())).status, 403);
  assert.equal((await worker.fetch(post(body, { 'Content-Length': '5000' }), makeEnv())).status, 413);
  assert.equal(mailCalls.length, 0);
});

test('send is rate limited per recipient', async () => {
  const seen = [];
  const env = makeEnv({
    SEND_LIMITER: { async limit() { return { success: true }; } },
    RECIPIENT_LIMITER: { async limit({ key }) { seen.push(key); return { success: false }; } },
  });
  const res = await worker.fetch(post({ key: KEY, email: 'Guest@Example.com' }), env);
  assert.equal(res.status, 429);
  assert.match(seen[0], /^[0-9a-f]{64}$/);  // hashed, not the raw address
  assert.equal(mailCalls.length, 0);
});

test('provider failure is reported as failed', async () => {
  globalThis.fetch = async () => new Response('bad', { status: 422 });
  const errors = console.error;
  console.error = () => {};
  try {
    const res = await worker.fetch(post({ key: KEY, email: 'guest@example.com' }), makeEnv());
    assert.equal(res.status, 502);
    assert.equal((await res.json()).error, 'failed');

    const noProvider = makeEnv({ RESEND_API_KEY: undefined });
    assert.equal((await worker.fetch(post({ key: KEY, email: 'guest@example.com' }), noProvider)).status, 502);
  } finally {
    console.error = errors;
  }
});

test('the page and the mail use the theme', async () => {
  const theme = (await import('../src/theme.js')).default;
  const page = await (await worker.fetch(get(`/p/${KEY}`), makeEnv({ EVENT_NAME: undefined }))).text();
  assert.match(page, new RegExp(`--bg: ${theme.colors.background}`));
  assert.match(page, new RegExp(`<h1>${theme.event.name}</h1>`));
  assert.match(page, /src="\/theme\/logo.png"/);
  assert.match(page, new RegExp(theme.event.hashtag));

  const logo = await worker.fetch(get('/theme/logo.png'), makeEnv());
  assert.equal(logo.status, 200);
  assert.equal(logo.headers.get('Content-Type'), 'image/png');
  const bytes = new Uint8Array(await logo.arrayBuffer());
  assert.deepEqual([...bytes.slice(1, 4)], [0x50, 0x4e, 0x47]);  // 'PNG'

  await worker.fetch(post({ key: KEY, email: 'guest@example.com' }, { 'Accept-Language': 'ko' }), makeEnv({ EVENT_NAME: undefined }));
  const mail = mailCalls[0].body;
  assert.equal(mail.from, `${theme.event.name} <photo@example.com>`);
  assert.match(mail.html, new RegExp(`background:${theme.colors.background}`));
  assert.match(mail.html, /https:\/\/photo.example.com\/theme\/logo.png/);
  assert.equal(mail.text.split('\n')[0], theme.texts.ko.mailBody);
});

function videoEnv() {
  const video = '0123456789';
  const env = makeEnv();
  const { head, get } = env.BUCKET;
  env.BUCKET = {
    async head(key) {
      if (key === '2026-10-06-12-00-00_pibooth.mp4') return { key, size: video.length, httpMetadata: { contentType: 'video/mp4' } };
      return head(key);
    },
    async get(key, options) {
      if (key !== '2026-10-06-12-00-00_pibooth.mp4') return get(key, options);
      const range = options && options.range;
      return { body: range ? video.slice(range.offset, range.offset + range.length) : video };
    },
  };
  return env;
}

test('the share page shows the video clip when it was uploaded', async () => {
  const page = await (await worker.fetch(get(`/p/${KEY}`), videoEnv())).text();
  assert.match(page, /<video class="clip" src="\/v\/2026-10-06-12-00-00_pibooth.mp4"[^>]*autoplay muted loop playsinline/);
  assert.match(page, /href="\/vd\/2026-10-06-12-00-00_pibooth.mp4"/);
  const noVideo = await (await worker.fetch(get(`/p/${KEY}`), makeEnv())).text();
  assert.doesNotMatch(noVideo, /<video/);
});

test('the video is served with HTTP ranges (iOS player)', async () => {
  const env = videoEnv();
  const path = '/v/2026-10-06-12-00-00_pibooth.mp4';
  let res = await worker.fetch(get(path), env);
  assert.equal(res.status, 200);
  assert.equal(res.headers.get('Accept-Ranges'), 'bytes');
  assert.equal(res.headers.get('Content-Type'), 'video/mp4');
  assert.equal(await res.text(), '0123456789');

  res = await worker.fetch(get(path, { Range: 'bytes=0-1' }), env);
  assert.equal(res.status, 206);
  assert.equal(res.headers.get('Content-Range'), 'bytes 0-1/10');
  assert.equal(await res.text(), '01');

  res = await worker.fetch(get(path, { Range: 'bytes=-3' }), env);
  assert.equal(res.headers.get('Content-Range'), 'bytes 7-9/10');
  assert.equal(await res.text(), '789');

  res = await worker.fetch(get(path, { Range: 'bytes=20-' }), env);
  assert.equal(res.status, 416);

  res = await worker.fetch(new Request(`https://photo.example.com${path}`, { method: 'HEAD' }), env);
  assert.equal(res.headers.get('Content-Length'), '10');

  res = await worker.fetch(get('/vd/2026-10-06-12-00-00_pibooth.mp4'), env);
  assert.equal(res.headers.get('Content-Disposition'), 'attachment; filename="2026-10-06-12-00-00_pibooth.mp4"');
});

test('only mp4 keys are served as video', async () => {
  for (const path of ['/v/x.jpg', '/v/..%2Fx.mp4', '/vd/%E0%A4%A', '/v/missing.mp4']) {
    assert.equal((await worker.fetch(get(path), videoEnv())).status, 404, path);
  }
});

test('unknown routes and methods', async () => {
  assert.equal((await worker.fetch(get('/'), makeEnv())).status, 404);
  const put = new Request(`https://photo.example.com/p/${KEY}`, { method: 'PUT' });
  assert.equal((await worker.fetch(put, makeEnv())).status, 405);
});

test('the save buttons open the share sheet (Save to Photos on iOS)', async () => {
  const res = await worker.fetch(get(`/p/${KEY}`), makeEnv());
  const page = await res.text();
  assert.match(page, new RegExp(`href="/d/${KEY}" data-share="/i/${KEY}" data-type="image/jpeg"`));
  assert.match(page, /navigator\.share\(\{ files: \[file\] \}\)/);
  // The inline script is valid JavaScript
  const script = page.slice(page.indexOf('<script>') + 8, page.indexOf('</script>'));
  assert.doesNotThrow(() => new Function(script));
});

test('the email shows the photo, the button and the 7 days notice', async () => {
  await worker.fetch(post({ key: KEY, email: 'guest@example.com' }, { 'Accept-Language': 'ko' }), makeEnv());
  const mail = mailCalls[0].body;
  assert.match(mail.html, new RegExp(`<img src="https://photo.example.com/i/${KEY}"`));
  assert.match(mail.html, new RegExp(`href="https://photo.example.com/p/${KEY}"`));
  assert.match(mail.html, /7일 뒤 자동으로 지워져요/);
  assert.match(mail.text, /7일 뒤 자동으로 지워져요/);
});
