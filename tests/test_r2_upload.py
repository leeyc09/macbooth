# -*- coding: utf-8 -*-

"""Tests of the R2 upload plugin, without boto3 or network (a fake S3 client)."""

import sys
import time
import os.path as osp
import pytest

ROOT = osp.dirname(osp.dirname(osp.abspath(__file__)))
sys.path.insert(0, osp.join(ROOT, 'plugins'))
import pibooth_r2_upload as r2  # noqa: E402


class FakeS3(object):
    def __init__(self):
        self.calls = []

    def upload_file(self, path, bucket, key, ExtraArgs=None):  # noqa: N803
        self.calls.append({'path': path, 'bucket': bucket, 'key': key, 'extra': ExtraArgs})


def make_uploader(**kw):
    params = dict(endpoint_url="https://acc.r2.cloudflarestorage.com/", bucket="photobooth",
                  access_key_id="AKID", secret_access_key="SECRET",
                  key_prefix="event/", public_url="https://pics.example.com/", client=FakeS3(),
                  random_names=False)
    params.update(kw)
    return r2.R2Uploader(**params)


def test_is_configured():
    assert make_uploader().is_configured
    assert not make_uploader(access_key_id="", secret_access_key="").is_configured
    assert not make_uploader(bucket="").is_configured


def test_object_key_and_shared_url():
    up = make_uploader()
    assert up.object_key("/tmp/2026_pibooth.jpg") == "event/2026_pibooth.jpg"
    assert up.shared_url("event/2026_pibooth.jpg") == "https://pics.example.com/event/2026_pibooth.jpg"
    assert make_uploader(public_url="").shared_url("k") is None


def test_endpoint_and_prefix_are_normalized():
    up = make_uploader(endpoint_url="https://acc.r2.cloudflarestorage.com/", key_prefix="/event/")
    assert up.endpoint_url == "https://acc.r2.cloudflarestorage.com"
    assert up.key_prefix == "event/"


def test_credentials_from_environment_override(monkeypatch):
    monkeypatch.setenv("PIBOOTH_R2_ACCESS_KEY_ID", "ENVID")
    monkeypatch.setenv("PIBOOTH_R2_SECRET_ACCESS_KEY", "ENVSECRET")
    up = make_uploader(access_key_id="fileid", secret_access_key="filesecret")
    assert up.access_key_id == "ENVID" and up.secret_access_key == "ENVSECRET"


def test_upload_calls_client_and_returns_url(tmp_path):
    fake = FakeS3()
    up = make_uploader(client=fake)
    f = tmp_path / "2026-09-16_pibooth.jpg"
    f.write_bytes(b"jpegdata")
    url = up.upload(str(f))
    assert url == "https://pics.example.com/event/2026-09-16_pibooth.jpg"
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call['bucket'] == "photobooth"
    assert call['key'] == "event/2026-09-16_pibooth.jpg"
    assert call['extra'] == {'ContentType': 'image/jpeg'}


def test_missing_boto3_raises_clear_error(tmp_path, monkeypatch):
    up = make_uploader(client=None)
    monkeypatch.setitem(sys.modules, 'boto3', None)  # Force ImportError
    f = tmp_path / "p.jpg"
    f.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="boto3"):
        up.upload(str(f))


def test_random_object_keys_can_not_be_guessed():
    up = make_uploader(random_names=True)
    keys = {up.object_key("/tmp/2026-10-16-16-43-13_pibooth.JPG") for _ in range(50)}
    assert len(keys) == 50
    for key in keys:
        assert key.startswith("event/") and key.endswith(".jpg")
        name = key[len("event/"):-len(".jpg")]
        assert len(name) == 24 and all(c in "0123456789abcdef" for c in name)
        assert "2026-10-16" not in key


def test_upload_uses_the_given_key(tmp_path):
    fake = FakeS3()
    up = make_uploader(client=fake, random_names=True)
    f = tmp_path / "p.jpg"
    f.write_bytes(b"x")
    assert up.upload(str(f), "event/abc.jpg") == "https://pics.example.com/event/abc.jpg"
    assert fake.calls[0]['key'] == "event/abc.jpg"


class Cfg(object):
    def __init__(self, values):
        self.values = values

    def get(self, section, option):
        return self.values.get((section, option), "")


def test_build_uploader_reads_config():
    cfg = Cfg({("R2", "endpoint_url"): "https://acc.r2.cloudflarestorage.com",
               ("R2", "bucket"): "photobooth", ("R2", "access_key_id"): "K",
               ("R2", "secret_access_key"): "S", ("R2", "key_prefix"): "e/",
               ("R2", "public_url"): "https://pics"})
    up = r2.build_uploader(cfg)
    assert up.is_configured and up.bucket == "photobooth" and up.key_prefix == "e/"
    assert up.random_names  # Default when the option is not set
    cfg.values[("R2", "random_names")] = "False"
    assert not r2.build_uploader(cfg).random_names


class App(object):
    def __init__(self, path):
        self.previous_picture_file = path
        self.previous_picture_url = None
        self.previous_picture_key = None


def test_state_processing_exit_uses_one_random_key(tmp_path, monkeypatch):
    """The key given to the QR code (set synchronously) is the uploaded one."""
    fake = FakeS3()
    monkeypatch.setattr(r2, "_UPLOADER", make_uploader(client=fake, random_names=True))
    monkeypatch.setattr(r2, "_THREADS", [])
    f = tmp_path / "2026-10-16-16-43-13_pibooth.jpg"
    f.write_bytes(b"jpeg")
    app = App(str(f))
    r2.state_processing_exit(app)
    key = app.previous_picture_key
    assert key and "2026-10-16" not in key
    assert app.previous_picture_url == "https://pics.example.com/" + key
    for thread in r2._THREADS:
        thread.join(2)
    assert [call['key'] for call in fake.calls] == [key]


def test_state_processing_exit_uploads_in_background(tmp_path, monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(r2, "_UPLOADER", make_uploader(client=fake))
    monkeypatch.setattr(r2, "_THREADS", [])
    f = tmp_path / "shot_pibooth.jpg"
    f.write_bytes(b"jpeg")
    app = App(str(f))
    r2.state_processing_exit(app)
    for _ in range(50):
        if app.previous_picture_url:
            break
        time.sleep(0.05)
    assert app.previous_picture_url == "https://pics.example.com/event/shot_pibooth.jpg"
    assert fake.calls and fake.calls[0]['key'] == "event/shot_pibooth.jpg"


def test_state_processing_exit_noop_when_not_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(r2, "_UPLOADER", make_uploader(bucket=""))
    monkeypatch.setattr(r2, "_THREADS", [])
    app = App(str(tmp_path / "x.jpg"))
    r2.state_processing_exit(app)  # Must not raise, no upload
    assert app.previous_picture_url is None


def test_url_is_set_synchronously_for_qrcode(tmp_path, monkeypatch):
    """The shared URL must be available right after the hook returns, before
    the background upload finishes, so the QR code plugin can use it."""
    class SlowS3(FakeS3):
        def upload_file(self, path, bucket, key, ExtraArgs=None):  # noqa: N803
            time.sleep(0.5)
            super().upload_file(path, bucket, key, ExtraArgs=ExtraArgs)
    monkeypatch.setattr(r2, "_UPLOADER", make_uploader(client=SlowS3()))
    monkeypatch.setattr(r2, "_THREADS", [])
    f = tmp_path / "shot_pibooth.jpg"
    f.write_bytes(b"jpeg")
    app = App(str(f))
    r2.state_processing_exit(app)
    # Immediately available, without waiting for the (slow) upload
    assert app.previous_picture_url == "https://pics.example.com/event/shot_pibooth.jpg"


def make_session(savedir, date, raws=4, clip=True):
    """Create the files pibooth saves for a session."""
    (savedir / '{}_pibooth.jpg'.format(date)).write_bytes(b'final')
    if clip:
        (savedir / '{}_pibooth.mp4'.format(date)).write_bytes(b'clip')
    rawdir = savedir / 'raw' / date
    rawdir.mkdir(parents=True)
    for i in range(raws):
        (rawdir / 'pibooth{:03}.jpg'.format(i)).write_bytes(b'raw')


def run_upload(app):
    r2.state_processing_exit(app)
    for thread in r2._THREADS:  # pylint: disable=protected-access
        thread.join(5)


def test_session_is_fully_uploaded_then_marked(tmp_path, monkeypatch):
    fake = FakeS3()
    monkeypatch.setattr(r2, "_UPLOADER", make_uploader(client=fake, random_names=True))
    monkeypatch.setattr(r2, "_THREADS", [])
    monkeypatch.setattr(r2, "_UPLOAD_RAW", True)
    monkeypatch.setattr(r2, "_KEEP_LOCAL", 50)
    date = '2026-10-16-19-00-00'
    make_session(tmp_path, date)
    app = App(str(tmp_path / '{}_pibooth.jpg'.format(date)))
    app.previous_clip_file = str(tmp_path / '{}_pibooth.mp4'.format(date))
    run_upload(app)
    key = app.previous_picture_key
    base = key[:-len('.jpg')]
    assert [c['key'] for c in fake.calls] == [key, base + '.mp4'] + \
        [base + '/raw/pibooth{:03}.jpg'.format(i) for i in range(4)]
    assert fake.calls[1]['extra'] == {'ContentType': 'video/mp4'}
    assert r2.LocalArchive(str(tmp_path), 50).is_uploaded(date)


def test_failed_upload_is_not_marked(tmp_path, monkeypatch):
    class FailingRaw(FakeS3):
        def upload_file(self, path, bucket, key, ExtraArgs=None):  # noqa: N803
            if '/raw/' in key:
                raise IOError("network down")
            super().upload_file(path, bucket, key, ExtraArgs=ExtraArgs)
    monkeypatch.setattr(r2, "_UPLOADER", make_uploader(client=FailingRaw(), random_names=True))
    monkeypatch.setattr(r2, "_THREADS", [])
    monkeypatch.setattr(r2, "_UPLOAD_RAW", True)
    monkeypatch.setattr(r2, "_KEEP_LOCAL", 50)
    date = '2026-10-16-19-00-00'
    make_session(tmp_path, date, clip=False)
    app = App(str(tmp_path / '{}_pibooth.jpg'.format(date)))
    app.previous_clip_file = None
    run_upload(app)
    assert not r2.LocalArchive(str(tmp_path), 50).is_uploaded(date)


def test_cleanup_deletes_only_old_uploaded_sessions(tmp_path):
    dates = ['2026-10-16-10-00-0{}'.format(i) for i in range(5)]
    for date in dates:
        make_session(tmp_path, date)
    archive = r2.LocalArchive(str(tmp_path), keep=2)
    for date in dates[1:]:              # The oldest one was never uploaded
        archive.mark_uploaded(date, 'k')
    assert archive.cleanup() == dates[1:3]
    left = sorted(p.name for p in tmp_path.iterdir() if p.suffix == '.jpg')
    assert left == ['{}_pibooth.jpg'.format(d) for d in (dates[0], dates[3], dates[4])]
    assert not (tmp_path / 'raw' / dates[1]).exists() and not (tmp_path / '{}_pibooth.mp4'.format(dates[2])).exists()
    assert (tmp_path / 'raw' / dates[0]).exists()                  # Not uploaded: kept
    assert r2.LocalArchive(str(tmp_path), keep=0).cleanup() == []  # 0: keep everything


def test_failed_session_is_retried_with_the_same_key(tmp_path, monkeypatch):
    class Offline(FakeS3):
        online = False

        def upload_file(self, path, bucket, key, ExtraArgs=None):  # noqa: N803
            if not self.online:
                raise IOError("network down")
            super().upload_file(path, bucket, key, ExtraArgs=ExtraArgs)
    fake = Offline()
    monkeypatch.setattr(r2, "_UPLOADER", make_uploader(client=fake, random_names=True))
    monkeypatch.setattr(r2, "_THREADS", [])
    monkeypatch.setattr(r2, "_UPLOAD_RAW", True)
    monkeypatch.setattr(r2, "_KEEP_LOCAL", 50)
    monkeypatch.setattr(r2, "_SAVEDIRS", [str(tmp_path)])
    date = '2026-10-16-19-00-00'
    make_session(tmp_path, date, raws=2)
    app = App(str(tmp_path / '{}_pibooth.jpg'.format(date)))
    app.previous_clip_file = str(tmp_path / '{}_pibooth.mp4'.format(date))
    run_upload(app)
    key = app.previous_picture_key
    archive = r2.LocalArchive(str(tmp_path), 50)
    assert not archive.is_uploaded(date) and archive.pending() == {date: key}

    assert r2.retry_pending() == 0                  # Still offline
    fake.online = True
    assert r2.retry_pending() == 1
    base = key[:-len('.jpg')]
    assert [c['key'] for c in fake.calls] == [key, base + '.mp4', base + '/raw/pibooth000.jpg',
                                              base + '/raw/pibooth001.jpg']
    assert archive.is_uploaded(date) and archive.pending() == {}
    assert r2.retry_pending() == 0                  # Nothing left


def test_session_uploaded_once_is_not_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(r2, "_UPLOADER", make_uploader(random_names=True))
    monkeypatch.setattr(r2, "_THREADS", [])
    monkeypatch.setattr(r2, "_KEEP_LOCAL", 50)
    date = '2026-10-16-19-00-00'
    make_session(tmp_path, date)
    app = App(str(tmp_path / '{}_pibooth.jpg'.format(date)))
    app.previous_clip_file = None
    run_upload(app)
    assert r2.LocalArchive(str(tmp_path), 50).pending() == {}
