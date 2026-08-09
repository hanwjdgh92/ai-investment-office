# Report 섹션 가독성 개선 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 오피스 화면(`office/template.html`)의 `Report` 섹션을 320px 사이드바에서 전체폭 레이아웃으로
바꾸고 글자 크기·줄간격을 키워 가독성을 개선한다.

**Architecture:** `.layout`의 2컬럼 그리드(`1fr 320px`)를 단일 컬럼으로 바꿔 오피스맵 아래에 `Report`가
전체폭으로 오도록 하고, `aside.console`의 사이드바 전용 스크롤 스타일을 제거한다. `.feed-item` 계열
타이포그래피(폰트 크기/줄간격/여백)를 키운다. 순수 CSS 변경, HTML 마크업/JS 로직 변경 없음
(DOM 순서가 이미 오피스맵→Report라 단일 컬럼 전환 시 자동으로 그 순서로 쌓인다).

**Tech Stack:** 순수 CSS(프레임워크 없음), 기존 파일만 수정.

## Global Constraints

- 스펙: `docs/superpowers/specs/2026-08-09-report-section-readability-design.md`
- 이 저장소는 자동 테스트 프레임워크가 없다 — 각 스텝은 "수동 실행 확인"으로 검증한다.
- 대상 파일은 `office/template.html` 하나뿐이다. `office/index.html`은 `generate_office.py`가
  `template.html`로부터 재생성하는 산출물이므로 직접 수정하지 않고 스크립트로 재생성한다.
- 데스크별 접기/펼치기(`<details class="feed-group">`) 동작, 오피스맵 픽셀아트 영역, `Report` 내용
  구조(문단 텍스트)는 변경하지 않는다 — 레이아웃과 타이포그래피만 바꾼다.

---

### Task 1: `office/template.html` — Report 레이아웃 전체폭 전환 + 타이포그래피 확대

**Files:**
- Modify: `office/template.html:83-84` (`.layout` 그리드)
- Modify: `office/template.html:210-214` (`aside.console` 스타일)
- Modify: `office/template.html:227-230` (`.feed-item` 계열 타이포그래피)

**Interfaces:** 없음 (CSS 전용 변경, HTML 마크업/JS 인터페이스 변경 없음)

- [ ] **Step 1: `.layout` 그리드를 단일 컬럼으로 변경**

`office/template.html` 83~84줄:
```css
  .layout { display: grid; grid-template-columns: 1fr 320px; gap: 20px; align-items: start; }
  @media (max-width: 860px) { .layout { grid-template-columns: 1fr; } }
```
을 아래로 교체 (이제 모든 화면 폭에서 단일 컬럼이므로 미디어쿼리는 불필요해져 제거):
```css
  .layout { display: grid; grid-template-columns: 1fr; gap: 20px; align-items: start; }
```

- [ ] **Step 2: `aside.console`에서 사이드바 전용 스크롤 제약 제거**

`office/template.html` 210~214줄:
```css
  aside.console {
    border-radius: 20px; border: 1px solid var(--border); background: var(--panel-bg);
    padding: 16px; max-height: 560px; overflow-y: auto; backdrop-filter: blur(6px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
  }
```
을 아래로 교체 (`max-height`/`overflow-y` 제거 — 사이드바가 아니므로 내부 스크롤 불필요, 페이지
자연 스크롤에 맡긴다. 패딩도 넓어진 폭에 맞춰 소폭 확대):
```css
  aside.console {
    border-radius: 20px; border: 1px solid var(--border); background: var(--panel-bg);
    padding: 20px 24px; backdrop-filter: blur(6px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.08);
  }
```

- [ ] **Step 3: `.feed-item` 타이포그래피 확대**

`office/template.html` 227~230줄:
```css
  .feed-group .feed-item { margin: 10px 0 0; }
  .feed-item { border-left: 3px solid var(--accent); border-radius: 8px; padding: 8px 10px; margin-bottom: 10px; background: var(--bg-bottom); }
  .feed-item .fhead { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-sub); margin-bottom: 4px; }
  .feed-item .ftext { font-size: 0.86rem; white-space: pre-wrap; }
```
을 아래로 교체:
```css
  .feed-group .feed-item { margin: 14px 0 0; }
  .feed-item { border-left: 3px solid var(--accent); border-radius: 8px; padding: 12px 14px; margin-bottom: 14px; background: var(--bg-bottom); }
  .feed-item .fhead { display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-sub); margin-bottom: 6px; }
  .feed-item .ftext { font-size: 1rem; line-height: 1.7; white-space: pre-wrap; }
```

- [ ] **Step 4: 정적 스냅샷 재생성**

Run: `python scripts\generate_office.py`
Expected: `office\index.html`이 갱신된 시각으로 다시 저장된다 (`saved: ...office\index.html` 출력).

- [ ] **Step 5: 정적 스냅샷 브라우저 확인**

`office\index.html`을 브라우저로 연다.
Expected: 오피스맵(픽셀아트 타일맵)이 위, `Report` 섹션이 그 아래 전체폭으로 표시된다. `Report`
내부 문단 텍스트가 이전보다 넓은 폭에 큰 글씨(1rem)·넓은 줄간격으로 표시되고, 더 이상 자체 스크롤
박스(내부 스크롤바)가 없다 — 페이지 전체 스크롤로 Report 끝까지 보인다.

- [ ] **Step 6: 라이브 서버로 확인 (기존 기능 회귀 없는지 포함)**

Run: `python scripts\serve_office.py`
Expected: 브라우저가 자동으로 열리고 동일한 레이아웃이 보인다. "지금 분석 받기" 버튼, "⚙ 관심종목
관리" 패널 토글이 이전과 동일하게 정상 동작한다(레이아웃 변경이 이 두 기능의 JS 로직을 건드리지
않았으므로 회귀 없어야 함). 데스크별 `<details>` 그룹 펼치기/접기도 정상 동작한다.

- [ ] **Step 7: 좁은 화면 폭에서 확인**

브라우저 창을 860px 이하로 좁혀서 확인 (또는 개발자 도구 반응형 모드).
Expected: 기존에도 이 폭에서는 단일 컬럼이었으므로 레이아웃이 깨지지 않는다 — 오피스맵/Report 모두
정상적으로 전체폭에 맞춰 표시된다.

- [ ] **Step 8: 라이트/다크 테마 확인**

OS 다크모드 전환 또는 브라우저 개발자 도구로 `prefers-color-scheme` 토글.
Expected: `--panel-bg`, `--border`, `--text-sub`, `--accent` 등 기존 CSS 변수를 그대로 사용하므로
두 테마 모두 배경/글자색이 깨지지 않는다.

- [ ] **Step 9: Commit**

```bash
git add office/template.html office/index.html
git commit -m "fix: Report 섹션을 전체폭 레이아웃으로 전환하고 가독성 개선"
```

---

### Task 2: 엔드투엔드 최종 확인

**Files:** 없음 (검증 전용)

- [ ] **Step 1: `git status`로 의도한 파일만 변경됐는지 확인**

Run: `git status --short`
Expected: 변경 목록이 깨끗하다(Task 1의 커밋 이후 추가 변경 없음). `office/template.html`,
`office/index.html` 외 다른 파일은 건드리지 않았어야 한다.

- [ ] **Step 2: 스펙 목표 재확인**

`docs/superpowers/specs/2026-08-09-report-section-readability-design.md`의 "목표" 3개 항목
(텍스트 읽기 편함, 320px 제약 제거, 글자 크기·줄간격 확대)을 Step 5~8의 확인 결과와 하나씩
대조해 모두 충족했는지 확인한다.
