# 디자인 시스템과 Claude로 디자인 바꾸기

MacBooth의 인쇄 프레임, 부스 화면, 공유 페이지, 관리 페이지 디자인을 **디자인 시스템**을 기준으로
**Claude**에게 맡겨 바꾸는 방법입니다. 사람이 직접 고칠 때도 같은 순서를 따르면 됩니다.

- [1. 디자인이 어디서 오는가](#1-디자인이-어디서-오는가)
- [2. Claude 준비](#2-claude-준비)
- [3. 기본 작업 순서](#3-기본-작업-순서)
- [4. 작업별 방법과 요청 예시](#4-작업별-방법과-요청-예시)
- [5. 배포](#5-배포)
- [6. 주의할 점](#6-주의할-점)

## 1. 디자인이 어디서 오는가

```
DroidKnights Design System/        브랜드 원본: 색·폰트 토큰, 로고, 마스코트, 브랜드 가이드
        │  (값을 옮겨 적음)
        ▼
pibooth/themes/droidknights/theme.json     부스 디자인의 유일한 설정 파일
        │  tools/build_theme.py
        ▼
생성물 ─┬─ templates/droidknights-4.json, -1.json     인쇄 프레임 (4컷, 1컷)
        ├─ assets/booth-background.jpg 외 2개           부스 화면 배경, 일러스트
        └─ share-worker/src/theme.js                   공유 페이지 색·폰트·문구
```

| 파일 | 고치는 방법 |
|---|---|
| `DroidKnights Design System/` | 브랜드가 바뀔 때 디자인 시스템 쪽에서 갱신 (가이드: `readme.md`, 토큰: `tokens/*.css`) |
| `pibooth/themes/<테마>/theme.json` | **직접 고침.** 색, 폰트, 이미지 이름, 화면 문구, 행사 정보, 공유 페이지 문구, 프레임 목록 |
| `pibooth/themes/<테마>/assets/` 의 로고·마스코트 | 직접 교체 (디자인 시스템 `assets/`에서 복사) |
| 생성물 (위 그림) | **직접 고치지 않음.** `theme.json`을 고치고 다시 빌드 |
| 프레임 모양 자체 (배경 그리는 방식, 배치) | `tools/build_theme.py`의 `galaxy` 스타일 코드 |
| `factory/*.html` (설정·리모컨·사진 공장) | 테마를 따르지 않음. 파일 위쪽 CSS 변수(`--blue` 등)를 직접 고침 |

**토큰 → theme.json 대응** (디자인 시스템 값이 바뀌면 오른쪽도 같이 바꿉니다)

| 디자인 시스템 (`tokens/`) | `theme.json` |
|---|---|
| `--dk-space` `--dk-navy` `--dk-navy-2` | `colors.space` `colors.navy` `colors.navy-2` |
| `--dk-blue` `--dk-purple` `--dk-lavender` | `colors.blue` `colors.purple` `colors.lavender` |
| `--dk-text` `--dk-text-dim` `--dk-text-muted` | `colors.text` `colors.text-dim` `colors.text-muted` |
| `--dk-grad` `--dk-grad-brand` | `gradients.text` `gradients.brand` |
| Space Grotesk / Noto Sans KR / Roboto Mono | `fonts.display` / `fonts.heading`·`fonts.body` / `fonts.mono` |
| `--dk-radius-card` 등 웹 값 | `web.radius` 등 (공유 페이지용) |
| `assets/logo-*.png`, `assets/mascot/*.png` | `assets.logo`, `assets.mascot_*` (테마 폴더로 복사한 파일) |

## 2. Claude 준비

### Claude Code (권장)

레포 폴더에서 Claude Code를 열면 아래 두 스킬이 자동으로 잡힙니다.

| 스킬 | 내용 |
|---|---|
| `droidknights-design` | 디자인 시스템 브랜드 가이드 (`.claude/skills/droidknights-design` → `DroidKnights Design System/`) |
| `macbooth-design` | 이 문서의 작업 순서: 어떤 파일을 고치고, 빌드하고, 미리보기로 확인하는지 (`.claude/skills/macbooth-design/SKILL.md`) |

요청할 때 "디자인 시스템 기준으로", "macbooth-design 순서대로"라고 붙이면 Claude가 브랜드 규칙을 읽고
고친 뒤 미리보기 이미지를 직접 열어 확인합니다. 스킬을 직접 부르려면 `/macbooth-design`, `/droidknights-design`.

### Claude 앱(claude.ai)에서 시안 잡기

코드를 고치기 전에 디자인 방향만 먼저 보고 싶을 때 씁니다.

1. `DroidKnights Design System` 폴더를 zip으로 묶어 Claude 앱 **설정 → 기능 → 스킬**에 올리거나, 대화에 파일로 첨부합니다.
2. "이 디자인 시스템으로 4×6 세로 포토부스 인쇄 프레임 시안 3개 만들어줘. 사진 4칸, 아래에 로고·행사명·날짜"처럼 요청해
   HTML 시안을 받습니다.
3. 마음에 드는 시안 이미지를 Claude Code 대화에 붙이고 "이 시안처럼 프레임 바꿔줘"라고 요청합니다(아래 4-3).

## 3. 기본 작업 순서

어떤 변경이든 이 순환을 반복합니다. Claude에게 맡기면 Claude가 같은 순서로 진행합니다.

```bash
# 1) theme.json(또는 스타일 코드, 템플릿 JSON) 수정

# 2) 생성물 다시 만들기
~/pibooth-venv/bin/python tools/build_theme.py droidknights --worker share-worker/src/theme.js

# 3) 미리보기: 프레임 + 부스 화면을 이미지로 저장 (preview/ 는 git에 안 올라감)
~/pibooth-venv/bin/python tools/preview_theme.py droidknights --out preview --screens
#    → preview/droidknights-4.jpg, droidknights-1.jpg   실제 합성 엔진으로 만든 인쇄 결과 (2400×3600)
#    → preview/screen-wait.png, -choose, -layout, -processing   부스 화면 (1600×900)

# 4) 테스트
SDL_VIDEODRIVER=dummy ~/pibooth-venv/bin/python -m pytest tests/test_theme.py tests/test_layout.py
(cd share-worker && npm test)

# 5) 실제 부스로 최종 확인
~/pibooth-venv/bin/pibooth
```

`build_theme.py`는 같은 입력이면 같은 파일을 만듭니다. 아무것도 안 바꾸고 빌드했을 때 `git status`가 깨끗하면 정상입니다.

## 4. 작업별 방법과 요청 예시

### 4-1. 문구·행사 정보 바꾸기

- **부스 화면 문구:** `theme.json` → `texts.ko` (`intro` "사진 찍기", `choose` "몇 컷으로 찍을까요?", `processing`, `finished` 등)
- **프레임에 들어가는 행사 정보:** `event` (`eyebrow`, `label`, `tagline`, `date`, `place`, `hashtag`)
- **공유 페이지·메일 문구:** `share.texts.ko`

> 요청 예시: "행사 날짜를 2027.06.20 SUN, 장소를 COEX, SEOUL로 바꾸고 대기 화면 문구를 '사진 찍고 가세요!'로 바꿔줘.
> 빌드하고 미리보기 확인해줘."

### 4-2. 색·폰트 바꾸기

디자인 시스템 토큰이 바뀌었거나 색을 조정할 때입니다. `colors`의 이름(`blue`, `space` …)을 바꾸면
`booth`, `qrcode`, 프레임, 공유 페이지가 그 이름을 참조하므로 한 곳만 고치면 됩니다.

- 폰트 파일은 테마 폴더 `fonts/`에 넣고 `fonts`에 경로를 적습니다. 이름만 적으면(`NotoSansKR-Black`) 앱에 들어 있는 폰트를 씁니다.
- 한글이 들어가는 곳(`booth.font`, `fonts.heading`/`body`)은 한글 글리프가 있는 폰트여야 합니다.

> 요청 예시: "디자인 시스템 tokens/colors.css가 바뀌었어. theme.json 색을 토큰과 맞추고, 바뀐 값 목록을 보여줘.
> 프레임이랑 부스 화면 미리보기로 확인해줘."

### 4-3. 인쇄 프레임 디자인 바꾸기

바꾸는 정도에 따라 세 가지 방법이 있습니다.

| 원하는 변경 | 방법 |
|---|---|
| 색, 로고, 마스코트, 행사 문구만 | `theme.json`과 `assets/`만 고치고 빌드 (4-1, 4-2, 4-4) |
| 배치·장식을 바꾸되 4컷/1컷 자동 생성은 유지 | `tools/build_theme.py`의 `galaxy` 스타일 코드 수정 (또는 새 스타일 추가) |
| 완전히 새 프레임 하나 | 템플릿 JSON을 새로 만들어 테마 `templates/`에 넣고 `theme.json`의 `templates` 목록에 추가 |

**새 프레임 JSON 만들기**

- 사람이 그릴 때: 템플릿 스튜디오(`admin/run.sh`)에서 만들고 **Save to pibooth**로 저장한 뒤,
  그 파일을 테마 `templates/`로 옮겨 `theme.json`의 `templates`에 추가합니다.
- Claude에게 맡길 때: 형식은 `plugins/pibooth_picture_template.py`의 `JsonTemplate` 설명에 있습니다.
  좌표는 0~1 비율, 세로 출력은 2400×3600 px입니다. 배경 이미지와 스티커는 data URI로 넣습니다.

> 요청 예시: "첨부한 시안처럼 2컷 가로 프레임을 하나 만들어줘. 사진 두 칸은 둥근 모서리, 아래에 마스코트(wave)와
> 해시태그. droidknights 테마 templates에 추가하고 미리보기로 확인해줘."

> 요청 예시: "galaxy 스타일에서 4컷 프레임 사진 칸 사이 간격을 넓히고, 사진 테두리 글로우를 약하게 해줘.
> 1컷 프레임은 그대로 두고, 바뀌기 전/후 미리보기를 나란히 보여줘."

테마에 `templates`가 있으면 `pibooth.cfg`의 `[PICTURE] template`보다 **테마 쪽이 우선**합니다.
특정 행사에서 일부 프레임만 쓰려면 설정 페이지의 **고정 프레임 / 제외할 프레임**을 씁니다.

### 4-4. 로고·마스코트 바꾸기

1. 디자인 시스템 `assets/`(또는 새로 받은 파일)에서 테마 `assets/`로 복사합니다. 마스코트는 투명 PNG입니다.
2. `theme.json`의 `assets`에서 이름에 연결합니다. 부스 화면 일러스트는 `pictograms`(어느 화면에 어떤 이미지),
   영상 워터마크는 `clip.watermark`가 이 이름을 씁니다.
3. 빌드 후 미리보기로 확인합니다. 앱 아이콘은 테마의 `assets/app-icon.png` 파일이며 앱을 다시 빌드할 때 반영됩니다.

> 요청 예시: "촬영 화면 오른쪽 마스코트(`pictograms`의 `capture_right.png`)를 point에서 cheer로 바꾸고,
> 영상 워터마크를 wordmark로 바꿔줘."

### 4-5. 새 행사 테마 만들기

다른 행사(다른 디자인 시스템)를 위한 테마입니다.

1. 새 디자인 시스템 폴더를 레포에 넣습니다. `SKILL.md`가 있으면 `.claude/skills/`에 링크를 걸어 스킬로 씁니다.
2. Claude에게 요청합니다.

   > "새 디자인 시스템 `<폴더>`를 읽고 `pibooth/themes/<이름>` 테마를 만들어줘. droidknights 테마를 복사해서
   > 색·폰트·로고·마스코트·행사 정보·문구를 새 브랜드로 바꾸고, 빌드하고, 프레임과 부스 화면 미리보기를 보여줘.
   > 디자인 시스템 규칙에 어긋나는 부분이 있으면 알려줘."

3. 미리보기를 보며 고칩니다. 원하는 모양이 `galaxy` 스타일과 많이 다르면 `build_theme.py`에 새 스타일을 추가하고
   `theme.json`의 `build.style`을 그 이름으로 바꿉니다.
4. 설정 페이지에서 테마를 고르거나 `[GENERAL] theme = <이름>`. 관리 페이지(`factory/*.html`) 색도 바꿀지 정합니다(4-6).

### 4-6. 관리 페이지·리모컨·공유 페이지

- **공유 페이지**는 `theme.js`(빌드 생성물)를 따르므로 `theme.json`만 고치고 빌드합니다. 화면 구조는 `share-worker/src/index.js`.
- **설정·리모컨·사진 공장**(`factory/*.html`)은 테마를 따르지 않습니다. 각 파일 위쪽의 CSS 변수와 `factory/assets/`를 고칩니다.
  확인은 부스를 켜고 `http://localhost:8770/settings`, `/remote`, `/`를 열어 봅니다. 사진 공장은 부스 없이
  `python3 -m http.server 8780 -d factory`로 띄워 `http://localhost:8780/`을 열면 샘플 사진으로 데모가 돕니다.

> 요청 예시: "리모컨 페이지 색을 새 테마 색에 맞추고, 버튼 문구를 '4컷 찍기' 대신 '네 컷'으로 바꿔줘.
> 브라우저로 열어서 아이패드 가로 크기 스크린샷으로 확인해줘."

## 5. 배포

| 바뀐 것 | 해야 할 일 |
|---|---|
| `theme.json`, 테마 이미지, 프레임 | 부스 맥: 개발 환경이면 재시작, 앱이면 `packaging/build_mac.sh`로 다시 빌드해 배포 |
| `share-worker/src/theme.js` | `cd share-worker && npm run deploy` |
| `factory/*.html` | 앱 다시 빌드 (앱 안에 들어감) |

## 6. 주의할 점

- **생성물은 손으로 고치지 않습니다.** 다음 빌드 때 덮어써집니다(`theme.js` 첫 줄에도 표시).
- **브랜드 규칙**(디자인 시스템 `readme.md`): 어두운 우주 남색 바탕, 그라데이션은 파랑→보라 계열만, 마스코트는
  색을 바꾸지 않고 한 화면에 하나, 이모지 대신 ✦ 기호. Claude에게 "디자인 시스템 규칙 위반이 없는지 확인해줘"라고 함께 요청하세요.
- **인쇄 크기:** 프레임은 4×6인치(2400×3600 px)로 인쇄됩니다. 가장자리 가까이에 글자나 로고를 두면 잘릴 수 있습니다.
- **한글 글자 넘침:** 문구를 길게 바꾸면 화면에서 넘칠 수 있습니다. 미리보기의 부스 화면으로 확인하세요.
- **비밀 값:** 디자인 작업 중에 `pibooth.cfg`의 R2 키나 `wrangler.toml` 실제 값을 커밋하지 않도록 주의합니다.
