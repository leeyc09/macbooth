// Cloudflare Worker serving the share page of the pibooth pictures.
//
// The booth QR code points to /p/<key> (<key> is the R2 object key, i.e. the
// picture file name plus the optional [R2] key_prefix). The page shows the
// picture, offers a download, and lets the guest receive the link by email.
//
//   GET  /p/<key>    share page (auto-refreshes while the upload is pending)
//   GET  /i/<key>    picture, inline
//   GET  /d/<key>    picture, as a download
//   POST /api/send   {key, email} -> send the share link to that address
//
// Bindings and variables: see wrangler.example.toml and README.md. The look (colors,
// fonts, logo, texts, event info) comes from ./theme.js, generated from a
// pibooth theme by tools/build_theme.py --worker.

import THEME from './theme.js';

const KEY_RE = /^[A-Za-z0-9][A-Za-z0-9._\-/]{0,199}$/;
const IMAGE_RE = /\.(jpe?g|png|gif|webp)$/i;
const MAX_BODY = 2048;
const EMAIL_RE = /^[^\s@<>"']+@[^\s@<>"']+\.[^\s@<>"']+$/;
const PENDING_RETRIES = 20;   // ~1 minute with a 3 seconds refresh

const TEXTS = {
  ko: {
    title: '사진',
    pending: '사진을 업로드하고 있어요. 잠시 후 자동으로 새로고침됩니다.',
    notFound: '사진을 찾을 수 없어요. 사진은 촬영 후 7일 동안만 보관돼요.',
    download: '사진 저장',
    saveHint: '버튼을 누르고 "이미지 저장"을 고르면 사진 앱에 저장돼요. 사진을 길게 눌러도 저장할 수 있어요.',
    keepNotice: '사진과 영상은 7일 뒤 자동으로 지워져요. 그 전에 저장해 주세요.',
    videoTitle: '촬영 영상',
    downloadVideo: '영상 저장',
    emailEyebrow: 'Get the link',
    emailLabel: '이메일로 링크 받기',
    emailHelp: '사진 링크를 메일로 보내드려요. 나중에 PC에서도 저장할 수 있어요.',
    emailPlaceholder: 'you@example.com',
    send: '보내기',
    sending: '보내는 중…',
    sent: '메일을 보냈어요. 받은편지함(또는 스팸함)을 확인해 주세요.',
    failed: '메일을 보내지 못했어요. 잠시 후 다시 시도해 주세요.',
    invalidEmail: '이메일 주소를 확인해 주세요.',
    tooMany: '요청이 너무 많아요. 잠시 후 다시 시도해 주세요.',
    privacy: '입력한 이메일은 링크 발송에만 사용되며 저장되지 않습니다.',
    mailSubject: '{event} 사진이 도착했어요',
    mailBody: '아래 링크에서 사진을 보고 저장할 수 있어요. 링크는 7일 동안 열려요.',
    mailOpen: '사진 보기',
    mailHeading: '사진이 도착했어요',
    mailFallback: '버튼이 열리지 않으면 아래 주소를 브라우저에 붙여 넣으세요.',
    mailFooter: '포토부스에서 이 주소로 링크 받기를 요청해서 보낸 메일이에요.',
  },
  en: {
    title: 'Photo',
    pending: 'Your photo is being uploaded. This page will refresh automatically.',
    notFound: 'Photo not found. Photos are kept for 7 days after the shot.',
    download: 'Save photo',
    saveHint: 'Tap the button and choose "Save Image" to add it to Photos. You can also long-press the photo.',
    keepNotice: 'Photos and videos are deleted after 7 days. Save them before then.',
    videoTitle: 'Behind the shot',
    downloadVideo: 'Save video',
    emailEyebrow: 'Get the link',
    emailLabel: 'Get the link by email',
    emailHelp: 'We will email you the link so you can save the photo later, on any device.',
    emailPlaceholder: 'you@example.com',
    send: 'Send',
    sending: 'Sending…',
    sent: 'Email sent. Check your inbox (or spam folder).',
    failed: 'Could not send the email. Please try again later.',
    invalidEmail: 'Please check the email address.',
    tooMany: 'Too many requests. Please try again later.',
    privacy: 'Your email is only used to send this link and is not stored.',
    mailSubject: 'Your {event} photo',
    mailBody: 'View and save your photo with the link below. The link works for 7 days.',
    mailOpen: 'View photo',
    mailHeading: 'Your photo is here',
    mailFallback: 'If the button does not work, paste this address in your browser.',
    mailFooter: 'You received this email because this address was entered at the photo booth.',
  },
};

// Texts of the page and mail: the built-in ones, overridden by the theme ones
function textsFor(lang) {
  return { ...TEXTS[lang], ...((THEME.texts || {})[lang] || {}) };
}

function eventName(env, t) {
  return env.EVENT_NAME || (THEME.event && THEME.event.name) || t.title;
}

const LOGO = THEME.logo ? decodeDataUri(THEME.logo) : null;

function decodeDataUri(uri) {
  const [head, data] = uri.split(',', 2);
  const type = head.slice(5).split(';')[0];
  const bytes = Uint8Array.from(atob(data), (c) => c.charCodeAt(0));
  return { type, bytes };
}

// CSS custom properties from the theme tokens (neutral palette without theme)
function themeCss() {
  const c = THEME.colors || {};
  const w = THEME.web || {};
  const g = THEME.gradient && THEME.gradient.length > 1 ? THEME.gradient : null;
  const accent = c.accent || '#1d1d1b';
  const vars = {
    '--bg': c.background || '#f6f5f2',
    '--fg': c.text || '#1d1d1b',
    '--muted': c['text-muted'] || '#6b6a66',
    '--card': c.surface || '#ffffff',
    '--card-raised': c['surface-raised'] || c.surface || '#ffffff',
    '--line': c.line || '#dedcd6',
    '--accent': accent,
    '--accent-2': c['accent-2'] || accent,
    '--accent-3': c['accent-3'] || accent,
    '--accent-fg': c['on-accent'] || '#ffffff',
    '--accent-fill': g ? `linear-gradient(135deg, ${c.accent || g[0]}, ${c['accent-2'] || g[g.length - 1]})` : accent,
    '--text-fill': g ? `linear-gradient(90deg, ${g.join(', ')})` : 'none',
    '--font-body': w.font_body || '-apple-system, BlinkMacSystemFont, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif',
    '--font-display': w.font_display || 'inherit',
    '--font-mono': w.font_mono || 'ui-monospace, monospace',
    '--radius': w.radius || '12px',
    '--radius-small': w.radius_small || '10px',
  };
  return Object.entries(vars).map(([k, v]) => `${k}: ${v};`).join(' ');
}

function pickLang(request) {
  const header = request.headers.get('Accept-Language') || '';
  return header.trim().toLowerCase().startsWith('ko') ? 'ko' : 'en';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[c]);
}

export function isValidKey(key) {
  return typeof key === 'string' && KEY_RE.test(key) && IMAGE_RE.test(key) && !key.split('/').includes('..');
}

// The video clip of a picture: same object name, '.mp4' extension
export function videoKeyFor(key) {
  return key.replace(/\.[^./]+$/, '') + '.mp4';
}

function isValidVideoKey(key) {
  return typeof key === 'string' && KEY_RE.test(key) && /\.mp4$/.test(key) && !key.split('/').includes('..');
}

export function isValidEmail(email) {
  return typeof email === 'string' && email.length <= 254 && EMAIL_RE.test(email);
}

function keyFromPath(pathname, prefix) {
  try {
    const key = decodeURIComponent(pathname.slice(prefix.length));
    return isValidKey(key) ? key : null;
  } catch {
    return null;
  }
}

function encodeKey(key) {
  return key.split('/').map(encodeURIComponent).join('/');
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}

function html(body, status = 200) {
  return new Response(body, {
    status,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'no-referrer',
    },
  });
}

function layout(lang, title, content, head = '') {
  return `<!doctype html>
<html lang="${lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>${escapeHtml(title)}</title>
${THEME.web && THEME.web.fonts_css ? `<link rel="stylesheet" href="${escapeHtml(THEME.web.fonts_css)}">` : ''}
${LOGO ? '<link rel="icon" href="/theme/logo.png">' : ''}
${head}
<style>
  :root { ${themeCss()} }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--fg); font: 16px/1.55 var(--font-body); }
  main { max-width: 560px; margin: 0 auto; padding: 24px 16px 48px; }
  header { text-align: center; margin: 4px 0 20px; }
  header img { display: block; width: 168px; height: auto; margin: 0 auto 10px; }
  .eyebrow { font: 600 12px/1.4 var(--font-display); letter-spacing: .22em; text-transform: uppercase; color: var(--accent-3); margin: 0; }
  h1 { font: 900 22px/1.3 var(--font-display); margin: 6px 0 0; }
  img.photo { display: block; width: 100%; height: auto; border-radius: var(--radius); background: var(--card); box-shadow: 0 12px 30px color-mix(in srgb, var(--accent) 40%, transparent), 0 24px 60px color-mix(in srgb, var(--accent-2) 35%, transparent); }
  .btn { display: block; width: 100%; padding: 14px; border: 0; border-radius: 999px; background: var(--accent-fill); color: var(--accent-fg); font: inherit; font-weight: 700; text-align: center; text-decoration: none; cursor: pointer; }
  .btn:disabled { opacity: .6; cursor: default; }
  video.clip { display: block; width: 100%; height: auto; border-radius: var(--radius-small); margin-bottom: 12px; background: var(--bg); }
  .card { margin-top: 16px; padding: 16px; border-radius: var(--radius); background: var(--card); border: 1px solid var(--line); }
  label { display: block; font-weight: 700; margin-bottom: 8px; }
  .mail { position: relative; padding: 22px 20px 18px; background: radial-gradient(120% 90% at 0% 0%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 60%), var(--card); }
  .mail .eyebrow { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
  .mail label { font: 900 20px/1.35 var(--font-body); margin: 0; letter-spacing: -.01em; }
  .mail .help { color: var(--muted); font-size: 14px; margin: 6px 0 16px; }
  .mail .row { display: flex; flex-wrap: wrap; gap: 10px; }
  .field { position: relative; flex: 1 1 220px; }
  .field svg { position: absolute; left: 16px; top: 50%; width: 20px; height: 20px; transform: translateY(-50%); color: var(--muted); pointer-events: none; transition: color .24s; }
  .field input { width: 100%; height: 52px; padding: 0 16px 0 46px; border: 1px solid var(--line); border-radius: 999px; background: var(--card-raised); color: var(--fg); font: 500 16px var(--font-body); outline: none; transition: border-color .24s, box-shadow .24s; }
  .field input::placeholder { color: var(--muted); opacity: .8; }
  .field input:focus { border-color: var(--accent); box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent) 28%, transparent); }
  .field:focus-within svg { color: var(--accent-3); }
  .mail .btn { flex: 0 0 auto; width: auto; height: 52px; padding: 0 26px; display: inline-flex; align-items: center; justify-content: center; gap: 10px; box-shadow: 0 6px 18px color-mix(in srgb, var(--accent) 35%, transparent); transition: transform .14s, box-shadow .24s, opacity .24s; }
  .mail .btn:not(:disabled):active { transform: scale(.97); }
  .mail .btn .arrow { font-family: var(--font-mono); font-weight: 400; }
  @media (max-width: 420px) { .mail .btn { flex: 1 1 100%; } }
  .mail .status { display: none; align-items: center; gap: 8px; margin: 14px 0 0; padding: 10px 14px; border-radius: 12px; font-size: 14px; font-weight: 700; background: color-mix(in srgb, var(--fg) 6%, transparent); }
  .mail .status:not(:empty) { display: flex; }
  .mail .status[data-kind=ok] { color: #2BE38A; background: color-mix(in srgb, #2BE38A 12%, transparent); }
  .mail .status[data-kind=err] { color: #FF5C7A; background: color-mix(in srgb, #FF5C7A 12%, transparent); }
  .mail .privacy { display: flex; gap: 6px; align-items: flex-start; color: var(--muted); font-size: 12px; margin: 14px 0 0; }
  .mail .privacy svg { flex: 0 0 auto; width: 14px; height: 14px; margin-top: 2px; }
  .muted { color: var(--muted); font-size: 13px; margin: 10px 0 0; }
  .status { min-height: 1.5em; margin: 10px 0 0; font-size: 14px; }
  footer { margin-top: 28px; text-align: center; font: 500 12px/1.6 var(--font-mono); color: var(--muted); }
</style>
</head>
<body><main>${content}${footerHtml()}</main></body>
</html>`;
}

function headerHtml(title) {
  const ev = THEME.event || {};
  return `<header>
${LOGO ? `<img src="/theme/logo.png" alt="${escapeHtml(title)}">` : ''}
${ev.eyebrow ? `<p class="eyebrow">✦ ${escapeHtml(ev.eyebrow)}</p>` : ''}
<h1>${escapeHtml(title)}</h1>
</header>`;
}

function footerHtml() {
  const ev = THEME.event || {};
  const parts = [ev.date, ev.place, ev.hashtag].filter(Boolean).map(escapeHtml);
  return parts.length ? `<footer>${parts.join(' · ')}</footer>` : '';
}

function pendingPage(lang, env, url, retry) {
  const t = textsFor(lang);
  if (retry >= PENDING_RETRIES) {
    return html(layout(lang, t.notFound, `<h1>${escapeHtml(t.notFound)}</h1>`), 404);
  }
  const next = new URL(url);
  next.searchParams.set('r', String(retry + 1));
  const refresh = `<meta http-equiv="refresh" content="3;url=${escapeHtml(next.pathname + next.search)}">`;
  return html(layout(lang, eventName(env, t),
    `${headerHtml(eventName(env, t))}<p>${escapeHtml(t.pending)}</p>`, refresh));
}

function sharePage(lang, env, key, video = null) {
  const t = textsFor(lang);
  const title = eventName(env, t);
  const path = encodeKey(key);
  const messages = {
    sending: t.sending, sent: t.sent, failed: t.failed, invalid: t.invalidEmail, tooMany: t.tooMany,
  };
  const content = `
${headerHtml(title)}
<img class="photo" src="/i/${path}" alt="${escapeHtml(title)}">
<div class="card"><a class="btn" href="/d/${path}" data-share="/i/${path}" data-type="image/jpeg">${escapeHtml(t.download)}</a><p class="muted">${escapeHtml(t.saveHint)}</p><p class="muted">${escapeHtml(t.keepNotice)}</p></div>
${video ? `<div class="card video">
  <label>${escapeHtml(t.videoTitle)}</label>
  <video class="clip" src="/v/${encodeKey(video)}" poster="/i/${path}" autoplay muted loop playsinline preload="auto"></video>
  <a class="btn" href="/vd/${encodeKey(video)}" data-share="/v/${encodeKey(video)}" data-type="video/mp4">${escapeHtml(t.downloadVideo)}</a>
</div>` : ''}
<form class="card mail" id="send" novalidate>
  <p class="eyebrow">✦ ${escapeHtml(t.emailEyebrow)}</p>
  <label for="email">${escapeHtml(t.emailLabel)}</label>
  <p class="help">${escapeHtml(t.emailHelp)}</p>
  <div class="row">
    <div class="field">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/></svg>
      <input id="email" name="email" type="email" required autocomplete="email" inputmode="email" autocapitalize="off" spellcheck="false" placeholder="${escapeHtml(t.emailPlaceholder)}">
    </div>
    <button class="btn" type="submit">${escapeHtml(t.send)}<span class="arrow" aria-hidden="true">→</span></button>
  </div>
  <p class="status" id="status" role="status" aria-live="polite"></p>
  <p class="privacy"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg><span>${escapeHtml(t.privacy)}</span></p>
</form>
<script>
  const KEY = ${JSON.stringify(key).replace(/</g, '\\u003c')};
  const MSG = ${JSON.stringify(messages).replace(/</g, '\\u003c')};
  // Save to Photos: the share sheet of iOS offers "Save Image"/"Save Video".
  // The files are fetched in advance because iOS only opens the share sheet
  // right after the tap.
  const files = {};
  const canShareFiles = !!(navigator.canShare && window.File) &&
    navigator.canShare({ files: [new File([''], 'x.jpg', { type: 'image/jpeg' })] });
  function loadFile(link) {
    if (!files[link.dataset.share]) {
      const name = decodeURIComponent(link.getAttribute('href').split('/').pop());
      files[link.dataset.share] = fetch(link.dataset.share)
        .then((res) => (res.ok ? res.blob() : Promise.reject(new Error(res.status))))
        .then((blob) => { const file = new File([blob], name, { type: link.dataset.type }); files[link.dataset.share] = file; return file; });
      files[link.dataset.share].catch(() => { delete files[link.dataset.share]; });
    }
    return files[link.dataset.share];
  }
  if (canShareFiles) {
    document.querySelectorAll('[data-share]').forEach((link) => {
      loadFile(link);
      link.addEventListener('click', async (event) => {
        event.preventDefault();
        try {
          const file = files[link.dataset.share] instanceof File ? files[link.dataset.share] : await loadFile(link);
          await navigator.share({ files: [file] });
        } catch (err) {
          if (err.name !== 'AbortError') location.href = link.href;   // Fall back to the download
        }
      });
    });
  }
  const form = document.getElementById('send');
  const status = document.getElementById('status');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button');
    if (!form.email.checkValidity()) {
      status.dataset.kind = 'err';
      status.textContent = MSG.invalid;
      form.email.focus();
      return;
    }
    button.disabled = true;
    status.dataset.kind = '';
    status.textContent = MSG.sending;
    try {
      const res = await fetch('/api/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: KEY, email: form.email.value.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      status.dataset.kind = res.ok ? 'ok' : 'err';
      status.textContent = res.ok ? MSG.sent : (MSG[data.error] || MSG.failed);
      if (res.ok) form.reset();
    } catch (err) {
      status.dataset.kind = 'err';
      status.textContent = MSG.failed;
    } finally {
      button.disabled = false;
    }
  });
</script>`;
  return html(layout(lang, title, content));
}

// Parse a single 'bytes=start-end' range against the object size
function parseRange(header, size) {
  const match = /^bytes=(\d*)-(\d*)$/.exec(header || '');
  if (!match || (!match[1] && !match[2])) {
    return null;
  }
  let start = match[1] ? parseInt(match[1], 10) : size - parseInt(match[2], 10);
  let end = match[1] && match[2] ? parseInt(match[2], 10) : size - 1;
  start = Math.max(0, start);
  end = Math.min(end, size - 1);
  return start <= end ? { start, end } : 'invalid';
}

// Serve an object of the bucket, with HTTP ranges (needed by the video player
// of iOS Safari) and as a download when asked.
async function serveObject(env, request, key, download, defaultType) {
  const head = await env.BUCKET.head(key);
  if (!head) {
    return new Response('Not found', { status: 404 });
  }
  const headers = new Headers();
  headers.set('Content-Type', (head.httpMetadata && head.httpMetadata.contentType) || defaultType);
  headers.set('Cache-Control', 'public, max-age=86400');
  headers.set('X-Content-Type-Options', 'nosniff');
  headers.set('Accept-Ranges', 'bytes');
  if (download) {
    headers.set('Content-Disposition', `attachment; filename="${key.split('/').pop()}"`);
  }
  const range = parseRange(request.headers.get('Range'), head.size);
  if (range === 'invalid') {
    headers.set('Content-Range', `bytes */${head.size}`);
    return new Response(null, { status: 416, headers });
  }
  if (request.method === 'HEAD') {
    headers.set('Content-Length', String(head.size));
    return new Response(null, { headers });
  }
  if (range) {
    const object = await env.BUCKET.get(key, { range: { offset: range.start, length: range.end - range.start + 1 } });
    headers.set('Content-Range', `bytes ${range.start}-${range.end}/${head.size}`);
    headers.set('Content-Length', String(range.end - range.start + 1));
    return new Response(object.body, { status: 206, headers });
  }
  const object = await env.BUCKET.get(key);
  return new Response(object.body, { headers });
}

function buildMail(lang, env, link, image = null) {
  const t = textsFor(lang);
  const event = eventName(env, t);
  const subject = t.mailSubject.replace('{event}', event);
  const text = `${t.mailBody}\n\n${link}\n\n${t.keepNotice}\n`;
  const c = THEME.colors || {};
  const ev = THEME.event || {};
  const bg = c.background || '#f6f5f2';
  const card = c.surface || '#ffffff';
  const line = c.line || '#dedcd6';
  const fg = c.text || '#1d1d1b';
  const dim = c['text-dim'] || c['text-muted'] || '#6b6a66';
  const muted = c['text-muted'] || '#6b6a66';
  const accent = c.accent || '#1d1d1b';
  const accent3 = c['accent-3'] || accent;
  const onAccent = c['on-accent'] || '#ffffff';
  const gradient = c['accent-2'] ? `background-image:linear-gradient(135deg,${accent},${c['accent-2']});` : '';
  const font = "'Noto Sans KR','Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif";
  const mono = "'Roboto Mono',Menlo,Consolas,monospace";
  const origin = new URL(link).origin;
  const logo = LOGO ? `<img src="${escapeHtml(origin)}/theme/logo.png" width="150" alt="${escapeHtml(event)}" style="display:block;margin:0 auto;border:0;width:150px;height:auto">` : '';
  const eyebrow = [ev.label || ev.eyebrow].filter(Boolean).map(escapeHtml)[0];
  const info = [ev.date, ev.place, ev.hashtag].filter(Boolean).map(escapeHtml).join(' &middot; ');
  const photo = image ? `<tr><td style="padding:0 0 24px"><a href="${escapeHtml(link)}" style="text-decoration:none">
<img src="${escapeHtml(image)}" width="456" alt="${escapeHtml(event)}" style="display:block;width:100%;max-width:456px;height:auto;border:0;border-radius:14px"></a></td></tr>` : '';
  const body = `<!doctype html><html lang="${lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark light"><meta name="supported-color-schemes" content="dark light"><title>${escapeHtml(subject)}</title></head>
<body style="margin:0;padding:0;background:${bg}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">${escapeHtml(t.mailBody)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:${bg}" bgcolor="${bg}">
<tr><td align="center" style="padding:36px 16px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:520px;font-family:${font};color:${fg}">
${logo ? `<tr><td align="center" style="padding:0 0 28px">${logo}</td></tr>` : ''}
<tr><td style="background:${card};border:1px solid ${line};border-radius:22px;padding:28px 32px 30px" bgcolor="${card}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
${eyebrow ? `<tr><td style="padding:0 0 10px;font-family:${font};font-size:12px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:${accent3}">&#10022; ${eyebrow}</td></tr>` : ''}
<tr><td style="padding:0 0 10px;font-family:${font};font-size:26px;line-height:1.3;font-weight:900;color:${fg}">${escapeHtml(t.mailHeading)}</td></tr>
<tr><td style="padding:0 0 24px;font-family:${font};font-size:15px;line-height:1.65;color:${dim}">${escapeHtml(t.mailBody)}</td></tr>
${photo}
<tr><td align="center" style="padding:0 0 22px">
<a href="${escapeHtml(link)}" style="display:inline-block;padding:16px 40px;background:${accent};${gradient}color:${onAccent};border-radius:999px;text-decoration:none;font-family:${font};font-size:17px;font-weight:700">${escapeHtml(t.mailOpen)} &rarr;</a>
</td></tr>
<tr><td style="padding:14px 16px;border-radius:12px;background:${bg};font-family:${font};font-size:13px;line-height:1.55;color:${accent3}" bgcolor="${bg}">&#9201; ${escapeHtml(t.keepNotice)}</td></tr>
</table></td></tr>
<tr><td align="center" style="padding:22px 8px 0;font-family:${font};font-size:12px;line-height:1.6;color:${muted}">${escapeHtml(t.mailFallback)}<br>
<a href="${escapeHtml(link)}" style="color:${dim};word-break:break-all">${escapeHtml(link)}</a></td></tr>
${info ? `<tr><td align="center" style="padding:24px 8px 0;font-family:${mono};font-size:11px;letter-spacing:1px;color:${muted}">${info}</td></tr>` : ''}
<tr><td align="center" style="padding:10px 8px 0;font-family:${font};font-size:11px;line-height:1.6;color:${muted}">${escapeHtml(t.mailFooter)}</td></tr>
</table></td></tr></table></body></html>`;
  return { subject, text, html: body };
}

const encoder = new TextEncoder();

function toHex(bytes) {
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

async function sha256(text) {
  return toHex(await crypto.subtle.digest('SHA-256', encoder.encode(text)));
}

async function hmac(key, data) {
  const raw = typeof key === 'string' ? encoder.encode(key) : key;
  const cryptoKey = await crypto.subtle.importKey('raw', raw, { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return new Uint8Array(await crypto.subtle.sign('HMAC', cryptoKey, encoder.encode(data)));
}

// AWS Signature Version 4 headers for a JSON POST request
export async function signAwsRequest({ accessKeyId, secretAccessKey, region, service }, url, body, now = new Date()) {
  const amzDate = now.toISOString().replace(/[:-]|\.\d{3}/g, '');
  const date = amzDate.slice(0, 8);
  const { host, pathname } = new URL(url);
  const payloadHash = await sha256(body);
  const signedHeaders = 'content-type;host;x-amz-content-sha256;x-amz-date';
  const canonicalRequest = [
    'POST', pathname, '',
    `content-type:application/json\nhost:${host}\nx-amz-content-sha256:${payloadHash}\nx-amz-date:${amzDate}\n`,
    signedHeaders, payloadHash,
  ].join('\n');
  const scope = `${date}/${region}/${service}/aws4_request`;
  const stringToSign = ['AWS4-HMAC-SHA256', amzDate, scope, await sha256(canonicalRequest)].join('\n');
  let key = await hmac(`AWS4${secretAccessKey}`, date);
  for (const part of [region, service, 'aws4_request']) {
    key = await hmac(key, part);
  }
  const signature = toHex(await hmac(key, stringToSign));
  return {
    'Content-Type': 'application/json',
    'X-Amz-Date': amzDate,
    'X-Amz-Content-Sha256': payloadHash,
    Authorization: `AWS4-HMAC-SHA256 Credential=${accessKeyId}/${scope}, SignedHeaders=${signedHeaders}, Signature=${signature}`,
  };
}

// RFC 2047 encoded display name (SES rejects raw non-ASCII in the From header)
function encodeDisplayName(name) {
  const clean = name.replace(/["\\\r\n]/g, '');
  if (/^[\x20-\x7e]*$/.test(clean)) {
    return `"${clean}"`;
  }
  return `=?UTF-8?B?${btoa(String.fromCharCode(...encoder.encode(clean)))}?=`;
}

export async function sendMail(env, to, mail) {
  const fromName = env.FROM_NAME || env.EVENT_NAME || (THEME.event && THEME.event.name) || 'Photo Booth';
  if (env.AWS_ACCESS_KEY_ID && env.AWS_SECRET_ACCESS_KEY) {
    const region = env.AWS_REGION || 'ap-northeast-2';
    const url = `https://email.${region}.amazonaws.com/v2/email/outbound-emails`;
    const charset = 'UTF-8';
    const body = JSON.stringify({
      FromEmailAddress: `${encodeDisplayName(fromName)} <${env.FROM_EMAIL}>`,
      Destination: { ToAddresses: [to] },
      Content: {
        Simple: {
          Subject: { Data: mail.subject, Charset: charset },
          Body: { Text: { Data: mail.text, Charset: charset }, Html: { Data: mail.html, Charset: charset } },
        },
      },
    });
    const headers = await signAwsRequest({
      accessKeyId: env.AWS_ACCESS_KEY_ID, secretAccessKey: env.AWS_SECRET_ACCESS_KEY, region, service: 'ses',
    }, url, body);
    return fetch(url, { method: 'POST', headers, body });
  }
  if (env.RESEND_API_KEY) {
    return fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${env.RESEND_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: `${fromName} <${env.FROM_EMAIL}>`, to: [to], subject: mail.subject, html: mail.html, text: mail.text,
      }),
    });
  }
  if (env.BREVO_API_KEY) {
    return fetch('https://api.brevo.com/v3/smtp/email', {
      method: 'POST',
      headers: { 'api-key': env.BREVO_API_KEY, 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        sender: { name: fromName, email: env.FROM_EMAIL }, to: [{ email: to }],
        subject: mail.subject, htmlContent: mail.html, textContent: mail.text,
      }),
    });
  }
  throw new Error('No mail provider configured (set the AWS_* keys, RESEND_API_KEY or BREVO_API_KEY)');
}

async function handleSend(request, env, url) {
  // Only the share page itself may send (blocks cross-site form posts)
  if (request.headers.get('Origin') !== url.origin) {
    return json({ error: 'failed' }, 403);
  }
  if (parseInt(request.headers.get('Content-Length') || '0', 10) > MAX_BODY) {
    return json({ error: 'failed' }, 413);
  }
  let payload;
  try {
    payload = await request.json();
  } catch {
    return json({ error: 'failed' }, 400);
  }
  const key = payload && payload.key;
  const email = payload && typeof payload.email === 'string' ? payload.email.trim() : '';
  if (!isValidKey(key)) {
    return json({ error: 'failed' }, 400);
  }
  if (!isValidEmail(email)) {
    return json({ error: 'invalid' }, 400);
  }
  // Per IP (guests of a venue often share one) and per recipient (hashed)
  const limits = [
    [env.SEND_LIMITER, () => request.headers.get('CF-Connecting-IP') || 'unknown'],
    [env.RECIPIENT_LIMITER, () => sha256(email.toLowerCase())],
  ];
  for (const [limiter, makeKey] of limits) {
    if (limiter && !(await limiter.limit({ key: await makeKey() })).success) {
      return json({ error: 'tooMany' }, 429);
    }
  }
  if (!(await env.BUCKET.head(key))) {
    return json({ error: 'failed' }, 404);
  }

  const link = `${url.origin}/p/${encodeKey(key)}`;
  const mail = buildMail(pickLang(request), env, link, `${url.origin}/i/${encodeKey(key)}`);
  try {
    const res = await sendMail(env, email, mail);
    if (!res.ok) {
      console.error('Mail provider error', res.status, await res.text());
      return json({ error: 'failed' }, 502);
    }
  } catch (err) {
    console.error('Mail sending failed', err);
    return json({ error: 'failed' }, 502);
  }
  return json({ ok: true });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const lang = pickLang(request);
    const { pathname } = url;

    if (request.method === 'POST' && pathname === '/api/send') {
      return handleSend(request, env, url);
    }
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return new Response('Method not allowed', { status: 405 });
    }

    for (const [prefix, download] of [['/i/', false], ['/d/', true]]) {
      if (pathname.startsWith(prefix)) {
        const key = keyFromPath(pathname, prefix);
        return key ? serveObject(env, request, key, download, 'image/jpeg') : new Response('Not found', { status: 404 });
      }
    }

    for (const [prefix, download] of [['/v/', false], ['/vd/', true]]) {
      if (pathname.startsWith(prefix)) {
        let key = null;
        try {
          key = decodeURIComponent(pathname.slice(prefix.length));
        } catch {
          key = null;
        }
        return isValidVideoKey(key)
          ? serveObject(env, request, key, download, 'video/mp4')
          : new Response('Not found', { status: 404 });
      }
    }

    if (pathname === '/theme/logo.png') {
      return LOGO
        ? new Response(LOGO.bytes, { headers: { 'Content-Type': LOGO.type, 'Cache-Control': 'public, max-age=86400' } })
        : new Response('Not found', { status: 404 });
    }

    if (pathname.startsWith('/p/')) {
      const key = keyFromPath(pathname, '/p/');
      if (!key) {
        return html(layout(lang, textsFor(lang).notFound, `<h1>${escapeHtml(textsFor(lang).notFound)}</h1>`), 404);
      }
      if (!(await env.BUCKET.head(key))) {
        const retry = parseInt(url.searchParams.get('r') || '0', 10) || 0;
        return pendingPage(lang, env, url, retry);
      }
      const video = (await env.BUCKET.head(videoKeyFor(key))) ? videoKeyFor(key) : null;
      return sharePage(lang, env, key, video);
    }

    return new Response('Not found', { status: 404 });
  },
};
