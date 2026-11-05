# MacBooth

맥에서 돌아가는 포토부스 앱입니다. [pibooth](https://github.com/pibooth/pibooth)(Raspberry Pi용, MIT)를
포크해 macOS 전용으로 정리했습니다. Raspberry Pi 카메라(picamera2), GPIO 버튼/LED, Linux 자동시작은 빠졌고
파이썬 패키지와 설정 경로는 호환을 위해 그대로 `pibooth`를 씁니다.

## 기능

- 맥 내장 카메라, iPhone 연속성 카메라, 웹캠(OpenCV), DSLR(gPhoto2) 촬영
- 1~4컷 촬영 후 템플릿으로 합성, 테마(`pibooth/themes/droidknights`)
- 카운트다운 음성, 짧은 영상 클립(`plugins/pibooth_clip.py`)
- Cloudflare R2 업로드 + QR 공유 페이지(`plugins/pibooth_r2_upload.py`, `plugins/pibooth_qrcode.py`, `share-worker/`)
- 아이패드 리모컨, 설정 웹 페이지, 사진 공장 애니메이션(`plugins/pibooth_factory.py`, `factory/`)
- 템플릿 편집기(`admin/`, `tools/template_editor.html`)
- CUPS 프린터 출력

## 설치

```bash
python3 -m venv ~/pibooth-venv
~/pibooth-venv/bin/pip install -e ".[webcam,r2]"     # DSLR까지: ".[webcam,r2,dslr]"
~/pibooth-venv/bin/pibooth                            # 실행 (설정: ~/.config/pibooth/pibooth.cfg)
```

## 조작

| 동작 | 키보드 / 마우스 |
|---|---|
| 촬영 | `P` 또는 화면 왼쪽 클릭 |
| 출력 | `Ctrl+E` 또는 화면 오른쪽 클릭 |
| 설정 메뉴 | `Esc` (터치스크린: 네 손가락) |
| 전체 화면 | `Ctrl+F` |

## 구조

```
pibooth/              앱 본체 (패키지 이름은 원본 호환을 위해 pibooth 유지)
├─ booth.py           진입점, 메인 루프, 키보드/마우스/터치 이벤트
├─ states.py          상태 머신
├─ camera/            opencv.py(웹캠·내장·iPhone), gphoto.py(DSLR), hybrid.py(미리보기 웹캠 + 촬영 DSLR)
├─ plugins/           기본 플러그인: 카메라, 사진 합성, 화면, 프린터 + hookspecs.py(훅 정의)
├─ view/              pygame 화면 그리기
├─ config/            pibooth.cfg 기본값(parser.py)과 Esc 설정 메뉴(menu.py)
├─ themes/droidknights/  테마: 색, 폰트, 이미지, 프레임 템플릿
└─ sounds.py, language.py, printer.py, counters.py
plugins/              행사용 플러그인 (pibooth.cfg [GENERAL] plugins로 불러옴)
├─ pibooth_picture_template.py  프레임 템플릿으로 최종 사진 합성, 프레임 선택
├─ pibooth_clip.py              촬영 직전 몇 초를 MP4로 저장
├─ pibooth_r2_upload.py         사진/영상을 Cloudflare R2에 업로드 (끊기면 백그라운드 재시도)
├─ pibooth_qrcode.py            대기 화면에 공유 페이지 QR 표시
└─ pibooth_factory.py           로컬 웹 서버(:8770): 사진 공장, 설정, 아이패드 리모컨
factory/              pibooth_factory가 제공하는 웹 페이지(HTML)
share-worker/         Cloudflare Worker: QR로 열리는 사진 공유 페이지 + 이메일 발송
admin/, tools/        템플릿 편집기, 테마 빌드 도구
packaging/            PyInstaller로 MacBooth.app 빌드
tests/                pytest
```

**촬영 흐름(상태 머신)**

```
wait ──촬영──▶ choose(컷 수) ─▶ chosen ─▶ preview(카운트다운) ─▶ capture ─┐
  ▲                                       ▲                              │ 남은 컷
  │                                       └──────────────────────────────┘
  └── finish ◀── print ◀── processing(합성) ◀── layout(프레임 선택)
```

컷 수나 프레임이 하나뿐이면 `choose`/`layout`은 건너뛰고, 프린터가 없으면 `print` 없이 `finish`로 갑니다.

각 상태에서 `pibooth_*` 훅이 호출되고, 기본 플러그인과 `plugins/`의 플러그인이 이 훅을 구현합니다
(훅 목록: `pibooth/plugins/hookspecs.py`).

**사진이 손님에게 가는 경로**

```
카메라 ─▶ 합성(picture_template) ─▶ ~/Pictures/pibooth 저장
                                    ├─▶ R2 업로드(r2_upload) ─▶ share-worker 공유 페이지 ◀─ QR(qrcode)
                                    ├─▶ 사진 공장 화면(factory)
                                    └─▶ 프린터(CUPS, 선택)
```

**설정**은 `~/.config/pibooth/pibooth.cfg` 하나로 관리합니다. Esc 메뉴, `http://localhost:8770/settings`,
파일 직접 편집 중 어느 방법으로 바꿔도 같은 파일에 저장됩니다.

## 운영 배포

### 1. 공유 페이지 (처음 한 번)

R2 버킷을 만들고 `share-worker`를 배포합니다. 아래 [공유 페이지 배포](#공유-페이지-배포) 참고.

### 2. 앱 빌드

설정을 다 맞춘 맥에서 빌드합니다. 그 맥의 `pibooth.cfg`와 템플릿이 앱 안에 함께 들어갑니다.

```bash
packaging/build_mac.sh          # → dist/MacBooth.app, dist/MacBooth.zip
```

- **R2 키 같은 비밀 값도 앱에 들어갑니다.** zip은 믿을 수 있는 사람에게만 전달하세요.
  키를 앱에 넣지 않으려면 `pibooth.cfg`에서 빼고 `PIBOOTH_R2_ACCESS_KEY_ID`, `PIBOOTH_R2_SECRET_ACCESS_KEY` 환경 변수로 넘깁니다.
- Apple Silicon 전용입니다. 자세한 내용은 [packaging/README.md](packaging/README.md).

### 3. 행사장 맥에 설치

1. `MacBooth.zip`을 풀어 `/Applications`에 넣습니다.
2. 처음 실행할 때 **우클릭 → 열기**로 엽니다. 카메라 권한은 **허용**을 누릅니다.
   그래도 안 열리면 `xattr -dr com.apple.quarantine /Applications/MacBooth.app`.
3. `~/.config/pibooth/pibooth.cfg`가 없으면 빌드한 맥의 설정이 복사됩니다. 이미 있으면 그대로 둡니다.

### 4. 행사 당일 체크리스트

- [ ] 카메라 연결, 테스트 촬영 1회
- [ ] 아이패드 리모컨: 설정에서 접속 허용을 `같은 네트워크`로 바꾸고 PIN 설정 → 앱 재시작 ([factory/README.md](factory/README.md))
- [ ] 휴대폰으로 QR 스캔 → 공유 페이지에서 사진이 열리는지 확인
- [ ] 게스트 와이파이는 기기끼리 통신을 막는 경우가 많으니 소형 공유기나 핫스팟 준비
- [ ] 프린터를 쓰면 시험 출력 1장

인터넷이 끊겨도 촬영, 리모컨, 사진 공장은 계속 동작합니다. 업로드되지 않은 사진은 네트워크가 돌아오면 같은 링크로 다시 올라가서 이미 받은 QR도 그대로 쓸 수 있습니다.

## 공유 페이지 배포

`share-worker/wrangler.example.toml`은 예시 값만 든 템플릿입니다. 실제 서비스 전에 복사해서
도메인, R2 버킷, 발신 이메일을 바꾼 뒤 배포하세요. `wrangler.toml`은 git에 올라가지 않고,
예시 값이 남아 있으면 `npm run deploy`가 배포를 막습니다.

```bash
cd share-worker
cp wrangler.example.toml wrangler.toml   # 값 수정
npm run deploy
```

자세한 내용은 [share-worker/README.md](share-worker/README.md).

## 테스트

```bash
SDL_VIDEODRIVER=dummy CAM_VIDEODRIVER=dummy ~/pibooth-venv/bin/python -m pytest tests admin
```

## 문서

- [로컬 페이지(리모컨/설정)](factory/README.md)
- [공유 페이지 Worker](share-worker/README.md)
- [템플릿 스튜디오](admin/README.md)

## 라이선스

MIT. 원본 pibooth 저작권 표시는 [LICENSE](LICENSE)에 있습니다.
