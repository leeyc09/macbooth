# MacBooth 앱 패키징

```bash
packaging/build_mac.sh
```

- 결과: `dist/MacBooth.app`, 다른 맥으로 옮길 때는 `dist/MacBooth.zip`
- 플러그인(`plugins/`)과 로컬 페이지(`factory/`)는 앱 안에 들어가고, 항상 앱 안의 사본을 씁니다.
- 설정은 그대로 `~/.config/pibooth/pibooth.cfg`를 씁니다.
- 빌드한 맥의 설정(`pibooth.cfg`, `translations.cfg`, 템플릿 `*.json`)이 앱 안에 들어갑니다. 홈 폴더 경로는 `~/`로 바뀌고 `counters.json`과 백업은 빠집니다.
  다른 맥에서 처음 실행할 때 `~/.config/pibooth/pibooth.cfg`가 없으면 이 설정을 복사해서 씁니다. 이미 있으면 그대로 둡니다.
  다른 폴더의 설정을 넣으려면 `PIBOOTH_CONFIG=<폴더> packaging/build_mac.sh`
- **R2 키 같은 비밀 값도 앱에 들어갑니다.** 앱과 zip은 믿을 수 있는 사람에게만 전달하세요.
- 처음 실행할 때 카메라 권한을 묻습니다. **허용**을 누르세요.
- 다른 맥에서 "확인되지 않은 개발자" 경고가 뜨면 앱을 **우클릭 → 열기**로 엽니다.
  안 되면 터미널에서 `xattr -dr com.apple.quarantine /Applications/MacBooth.app`
- 빌드한 맥과 같은 CPU(Apple Silicon)에서만 실행됩니다.
