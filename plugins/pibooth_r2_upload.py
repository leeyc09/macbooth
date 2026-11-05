# -*- coding: utf-8 -*-

"""Pibooth plugin to upload the final picture to a Cloudflare R2 bucket.

R2 exposes an S3-compatible API, so the upload is done with ``boto3`` (install
it with ``pip install boto3``). Only the assembled final picture is uploaded,
once, right after it has been saved.

Enable the plugin with the ``[GENERAL][plugins]`` option and add an ``[R2]``
section to ``pibooth.cfg``::

    [R2]
    endpoint_url = https://<accountid>.r2.cloudflarestorage.com
    bucket = photobooth
    access_key_id = <your R2 access key id>
    secret_access_key = <your R2 secret access key>
    key_prefix = 2026-wedding/
    public_url = https://pics.example.com

For safety the credentials can be kept out of the file and given through the
environment instead (these override the configuration when set)::

    export PIBOOTH_R2_ACCESS_KEY_ID=...
    export PIBOOTH_R2_SECRET_ACCESS_KEY=...

By default the object is named with a random token (``random_names``) so the
links of the pictures can not be guessed from the capture time; the local file
keeps its name. The plugin stores the object key in ``app.previous_picture_key``
and, when ``public_url`` is set, the shared link in ``app.previous_picture_url``
so other plugins (e.g. a QR code with ``{key}`` or ``{url}``) can use them.

A session not fully uploaded (no network when it was taken) is retried in the
background every ``RETRY_DELAY`` seconds with the same key, so the QR code
already given to the guests works as soon as the network is back.
"""

import os
import re
import json
import time
import shutil
import os.path as osp
import secrets
import threading
import mimetypes

import pibooth
from pibooth.utils import LOGGER

__version__ = "1.0.0"

SECTION = "R2"


@pibooth.hookimpl
def pibooth_configure(cfg):
    """Declare the R2 configuration options."""
    cfg.add_option(SECTION, 'endpoint_url', "",
                   "R2 endpoint, e.g. https://<accountid>.r2.cloudflarestorage.com")
    cfg.add_option(SECTION, 'bucket', "",
                   "Name of the R2 bucket to upload the final pictures to")
    cfg.add_option(SECTION, 'access_key_id', "",
                   "R2 access key id (or set the PIBOOTH_R2_ACCESS_KEY_ID environment variable)")
    cfg.add_option(SECTION, 'secret_access_key', "",
                   "R2 secret access key (or set the PIBOOTH_R2_SECRET_ACCESS_KEY environment variable)")
    cfg.add_option(SECTION, 'key_prefix', "",
                   "Optional folder prefix for the uploaded object keys, e.g. 'event-2026/'")
    cfg.add_option(SECTION, 'public_url', "",
                   "Optional public base URL to build the shared link (r2.dev or a custom domain)")
    cfg.add_option(SECTION, 'random_names', True,
                   "Name the uploaded pictures with a random token so their links can not be guessed")
    cfg.add_option(SECTION, 'upload_raw', True,
                   "Also upload the raw captures (under '<picture key>/raw/')")
    cfg.add_option(SECTION, 'keep_local', 50,
                   "Number of sessions kept on the disk: the older ones are deleted (final picture, "
                   "video clip, raw captures) once all their files are uploaded; 0 to keep everything")


class R2Uploader(object):

    """Upload files to a Cloudflare R2 (S3-compatible) bucket.

    The ``client`` can be injected (for tests); otherwise it is built lazily
    with ``boto3`` on the first upload.
    """

    def __init__(self, endpoint_url, bucket, access_key_id, secret_access_key,
                 key_prefix="", public_url="", client=None, random_names=True):
        self.endpoint_url = endpoint_url.strip().rstrip('/')
        self.bucket = bucket.strip()
        self.access_key_id = (os.environ.get('PIBOOTH_R2_ACCESS_KEY_ID') or access_key_id).strip()
        self.secret_access_key = (os.environ.get('PIBOOTH_R2_SECRET_ACCESS_KEY') or secret_access_key).strip()
        self.key_prefix = key_prefix.strip().lstrip('/')
        self.public_url = public_url.strip().rstrip('/')
        self.random_names = random_names
        self._client = client

    @property
    def is_configured(self):
        """Return True when endpoint, bucket and credentials are all present."""
        return all((self.endpoint_url, self.bucket, self.access_key_id, self.secret_access_key))

    def _get_client(self):
        """Return the S3 client, building it with boto3 if needed."""
        if self._client is None:
            try:
                import boto3  # pylint: disable=import-outside-toplevel
                from botocore.config import Config  # pylint: disable=import-outside-toplevel
            except ImportError as ex:
                raise RuntimeError("'boto3' is required to upload to R2 (pip install boto3)") from ex
            self._client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name='auto',
                config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}))
        return self._client

    def object_key(self, filename):
        """Return a new object key for the given local file name: a random
        token (96 bits) with the file extension, or the file name itself.
        """
        if self.random_names:
            name = secrets.token_hex(12) + osp.splitext(filename)[1].lower()
        else:
            name = osp.basename(filename)
        return self.key_prefix + name

    def shared_url(self, key):
        """Return the public URL of an uploaded object, or None if no public
        base URL is configured."""
        return self.public_url + '/' + key if self.public_url else None

    def upload(self, path, key=None):
        """Upload the file at ``path`` to the bucket under ``key`` (a new one
        if not given). Return the shared URL (or the object key when no
        public URL is set).

        :raises: any boto3/botocore error on failure
        """
        key = key or self.object_key(path)
        content_type = mimetypes.guess_type(key)[0] or 'application/octet-stream'
        self._get_client().upload_file(
            path, self.bucket, key, ExtraArgs={'ContentType': content_type})
        return self.shared_url(key) or key


# Module-level state (pibooth registers the plugin module, so the hooks must be
# module-level functions, not methods of an instance).
_UPLOADER = None
_THREADS = []
_UPLOAD_RAW = True
_KEEP_LOCAL = 0
_SAVEDIRS = []
_ACTIVE = set()                 # Sessions being uploaded (never twice at once)
_ACTIVE_LOCK = threading.Lock()
_STOP = threading.Event()
RETRY_DELAY = 60                # Seconds between two retries of the failed uploads

SESSION_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})_pibooth\.jpg$')


class LocalArchive(object):

    """The sessions saved by pibooth in a pictures directory: the final
    picture ``<date>_pibooth.jpg``, the video clip ``<date>_pibooth.mp4`` and
    the raw captures ``raw/<date>/``. The fully uploaded sessions are recorded
    in a manifest; only those ones may be deleted, the oldest first, keeping
    the ``keep`` newest sessions on the disk.
    """

    MANIFEST = '.r2-uploaded.json'
    PENDING = '.r2-pending.json'    # Sessions to upload, with their key
    _lock = threading.Lock()

    def __init__(self, savedir, keep):
        self.savedir = savedir
        self.keep = keep
        self.manifest = osp.join(savedir, self.MANIFEST)
        self.pending_file = osp.join(savedir, self.PENDING)

    def _load(self, path=None):
        try:
            with open(path or self.manifest, encoding='utf-8') as fp:
                return json.load(fp)
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _save(path, data):
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, indent=1)
        os.replace(tmp, path)

    def mark_pending(self, session, key):
        """Record the key of a session before uploading it (kept until uploaded)."""
        with self._lock:
            data = self._load(self.pending_file)
            data[session] = key
            self._save(self.pending_file, data)

    def pending(self):
        """Return {session: key} of the sessions not fully uploaded yet."""
        return self._load(self.pending_file)

    def mark_uploaded(self, session, key):
        with self._lock:
            data = self._load()
            data[session] = {'key': key, 'time': int(time.time())}
            self._save(self.manifest, data)
            pending = self._load(self.pending_file)
            if pending.pop(session, None) is not None:
                self._save(self.pending_file, pending)

    def is_uploaded(self, session):
        return session in self._load()

    def sessions(self):
        """Return the sessions (capture dates) of the directory, oldest first."""
        return sorted(m.group(1) for m in map(SESSION_RE.match, os.listdir(self.savedir)) if m)

    def files(self, session):
        base = osp.join(self.savedir, session + '_pibooth')
        return [base + '.jpg', base + '.mp4', osp.join(self.savedir, 'raw', session)]

    def cleanup(self):
        """Delete the uploaded sessions older than the ``keep`` newest ones.
        Return the deleted sessions.
        """
        if self.keep <= 0:
            return []
        with self._lock:
            uploaded = self._load()
            deleted = []
            for session in self.sessions()[:-self.keep]:
                if session not in uploaded:
                    continue  # Never delete what is not safely uploaded
                for path in self.files(session):
                    if osp.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    elif osp.isfile(path):
                        os.remove(path)
                deleted.append(session)
        if deleted:
            LOGGER.info("Deleted %s old uploaded session(s) from '%s'", len(deleted), self.savedir)
        return deleted


def raw_key(picture_key, name):
    """Return the object key of a raw capture of a picture."""
    return osp.splitext(picture_key)[0] + '/raw/' + name


def build_uploader(cfg):
    """Return an :py:class:`R2Uploader` built from the configuration."""
    return R2Uploader(
        cfg.get(SECTION, 'endpoint_url'),
        cfg.get(SECTION, 'bucket'),
        cfg.get(SECTION, 'access_key_id'),
        cfg.get(SECTION, 'secret_access_key'),
        cfg.get(SECTION, 'key_prefix'),
        cfg.get(SECTION, 'public_url'),
        random_names=_get_bool(cfg, 'random_names'))


def _get_bool(cfg, option, default=True):
    """Return a boolean option (True when not set)."""
    value = str(cfg.get(SECTION, option)).strip().lower()
    return default if not value else value in ('true', '1', 'yes', 'on')


@pibooth.hookimpl
def pibooth_startup(cfg):
    """Build the uploader from the configuration and report its state."""
    global _UPLOADER, _UPLOAD_RAW, _KEEP_LOCAL
    _UPLOADER = build_uploader(cfg)
    _SAVEDIRS[:] = cfg.gettuple('GENERAL', 'directory', 'path')
    _UPLOAD_RAW = _get_bool(cfg, 'upload_raw')
    try:
        _KEEP_LOCAL = int(cfg.get(SECTION, 'keep_local') or 0)
    except ValueError:
        _KEEP_LOCAL = 0
    if _UPLOADER.is_configured:
        LOGGER.info("R2 upload enabled: bucket '%s' at %s", _UPLOADER.bucket, _UPLOADER.endpoint_url)
        for savedir in _SAVEDIRS:
            if osp.isdir(savedir):
                LocalArchive(savedir, _KEEP_LOCAL).cleanup()
        _STOP.clear()
        threading.Thread(target=_retry_loop, name="r2-retry", daemon=True).start()
    else:
        LOGGER.warning("R2 upload disabled: set endpoint_url, bucket and the credentials "
                       "in the [R2] section (or the PIBOOTH_R2_* environment variables)")


def clip_key(picture_key):
    """Return the object key of the video clip of a picture (same name, .mp4)."""
    return osp.splitext(picture_key)[0] + '.mp4'


def upload_session(path, key, clip=None):
    """Upload a final picture, its video clip and its raw captures, then mark
    the session uploaded (it may then be deleted from the disk). Return the
    URL of the picture, or None if it failed (or is being uploaded).
    """
    match = SESSION_RE.match(osp.basename(path))
    session = match.group(1) if match else path
    with _ACTIVE_LOCK:
        if session in _ACTIVE:
            return None
        _ACTIVE.add(session)
    try:
        return _upload_session(path, key, clip, match)
    finally:
        with _ACTIVE_LOCK:
            _ACTIVE.discard(session)


def _upload_session(path, key, clip, match):
    try:
        url = _UPLOADER.upload(path, key)
        LOGGER.info("Uploaded final picture to R2: %s", url)
    except Exception as ex:  # pylint: disable=broad-except
        LOGGER.error("R2 upload failed for '%s': %s", osp.basename(path), ex)
        return None
    complete = True
    if clip and osp.isfile(clip):
        try:
            LOGGER.info("Uploaded video clip to R2: %s", _UPLOADER.upload(clip, clip_key(key)))
        except Exception as ex:  # pylint: disable=broad-except
            LOGGER.error("R2 upload failed for '%s': %s", osp.basename(clip), ex)
            complete = False

    if not match:
        return url
    archive = LocalArchive(osp.dirname(path), _KEEP_LOCAL)
    rawdir = osp.join(archive.savedir, 'raw', match.group(1))
    if _UPLOAD_RAW and osp.isdir(rawdir):
        names = sorted(name for name in os.listdir(rawdir) if name.lower().endswith('.jpg'))
        for name in names:
            try:
                _UPLOADER.upload(osp.join(rawdir, name), raw_key(key, name))
            except Exception as ex:  # pylint: disable=broad-except
                LOGGER.error("R2 upload failed for raw capture '%s': %s", name, ex)
                complete = False
        if names and complete:
            LOGGER.info("Uploaded %s raw capture(s) to R2", len(names))

    # The session may be deleted from the disk only once everything is uploaded
    if complete and (_UPLOAD_RAW or not osp.isdir(rawdir)):
        archive.mark_uploaded(match.group(1), key)
        archive.cleanup()
    return url


def retry_pending():
    """Upload again the sessions not fully uploaded. Return their number."""
    count = 0
    for savedir in _SAVEDIRS:
        if not osp.isdir(savedir):
            continue
        for session, key in sorted(LocalArchive(savedir, _KEEP_LOCAL).pending().items()):
            if _STOP.is_set():
                return count
            base = osp.join(savedir, session + '_pibooth')
            if not osp.isfile(base + '.jpg'):
                continue  # Deleted by hand
            LOGGER.info("Retrying the R2 upload of session %s", session)
            if upload_session(base + '.jpg', key, base + '.mp4'):
                count += 1
    return count


def _retry_loop():
    while not _STOP.wait(RETRY_DELAY):
        try:
            retry_pending()
        except Exception as ex:  # pylint: disable=broad-except
            LOGGER.error("R2 retry failed: %s", ex)


@pibooth.hookimpl
def state_processing_exit(app):
    """Upload the freshly built final picture (then its video clip, if the
    clip plugin saved one) in the background."""
    if not _UPLOADER or not _UPLOADER.is_configured:
        return
    path = getattr(app, 'previous_picture_file', None)
    if not path or not osp.isfile(path):
        LOGGER.warning("R2 upload skipped: final picture file not found")
        return

    # Set the key and the shared link synchronously (they are known before the
    # upload finishes) so a QR code drawn right after this hook already points
    # to the picture.
    key = _UPLOADER.object_key(path)
    app.previous_picture_key = key
    shared = _UPLOADER.shared_url(key)
    if shared:
        app.previous_picture_url = shared

    clip = getattr(app, 'previous_clip_file', None)
    match = SESSION_RE.match(osp.basename(path))
    if match:  # Keep the key: the upload is retried with it if it fails
        LocalArchive(osp.dirname(path), _KEEP_LOCAL).mark_pending(match.group(1), key)

    def _worker():
        url = upload_session(path, key, clip)
        if url:
            app.previous_picture_url = url

    thread = threading.Thread(target=_worker, name="r2-upload", daemon=True)
    _THREADS[:] = [t for t in _THREADS if t.is_alive()]
    _THREADS.append(thread)
    thread.start()


@pibooth.hookimpl
def pibooth_cleanup():
    """Wait briefly for the pending uploads to finish."""
    _STOP.set()
    for thread in _THREADS:
        thread.join(timeout=10)
