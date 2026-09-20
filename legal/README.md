# 법적 고지 페이지

틱톡 개발자 포털이 **Terms of Service URL** 과 **Privacy Policy URL** 을
필수로 요구하고, 그 URL 은 **소유권이 검증된 주소**여야 합니다.
`github.com/...` 링크는 우리 소유가 아니라 검증되지 않습니다.

그래서 GitHub Pages 로 `budongjw.github.io` 아래에 서비스합니다.

## 구성

| 파일 | 용도 |
|---|---|
| `terms.md` / `privacy.md` | 원문. **고칠 때는 여기를 고칩니다** |
| `terms.html` / `privacy.html` | 위에서 생성한 게시용 페이지 |
| `index.html` | 두 문서로 가는 입구 |
| `_style.css` | 공용 스타일 (다크 모드 포함) |

`.md` 를 고쳤으면 `.html` 도 다시 만들어야 합니다 —
생성 스크립트는 커밋 기록에 있습니다.

## 틱톡 URL 검증

1. 앱 화면 오른쪽 위 **URL properties**
2. **URL prefix** 로 `https://budongjw.github.io/saltube/legal/` 추가
3. 틱톡이 주는 **서명 파일**을 내려받아 이 폴더에 넣고 푸시
4. **Verify** 클릭

DNS TXT 방식도 있지만 github.io 는 우리 도메인이 아니므로 쓸 수 없습니다.
서명 파일 방식만 가능합니다.

## 주의

여기 적힌 내용은 **도구가 실제로 하는 일과 일치해야 합니다.**
심사에서 설명과 동작이 다르면 반려됩니다.
도구 동작을 바꾸면 이 문서도 같이 고치세요.
