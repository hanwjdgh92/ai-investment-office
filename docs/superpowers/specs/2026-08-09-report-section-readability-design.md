# Report 섹션 가독성 개선 Design Spec

**작성일:** 2026-08-09
**배경:** 오피스 화면(`office/template.html`) 하단의 `Report` 섹션(애널리스트/리서치/트레이딩 코멘트 피드)이
`aside.console`(320px 고정폭 사이드바)에 배치돼 있어, 긴 한글 문단이 좁은 폭 안에서 줄바꿈이 잦고
작은 글씨(0.86rem)로 빽빽하게 표시된다. 사용자가 이 섹션을 "너무 보기 힘들다"고 지적했다.

## 목표

- `Report` 섹션의 텍스트를 읽기 편하게 만든다.
- 근본 원인인 좁은 폭(320px 사이드바 제약)을 없애 문단이 넓게 펼쳐지게 한다.
- 글자 크기·줄간격을 키워 밀도를 낮춘다.

## 범위 밖 (Non-goals)

- `Report` 섹션의 내용 구조 변경(문단 텍스트를 불릿/카드로 재구성 등) — 이번엔 레이아웃·타이포그래피만.
- 오피스맵(픽셀아트 타일맵) 영역 디자인 변경.
- 데스크별 접기/펼치기(`<details class="feed-group">`) 동작 변경 — 그대로 유지.

## 아키텍처

- `office/template.html`만 수정 (신규 파일 없음).
- `.layout`(현재 `grid-template-columns: 1fr 320px`, 오피스맵+사이드바 나란히 배치)을 단일 컬럼으로
  변경 — 오피스맵이 위, `Report`가 그 아래 전체폭을 차지하는 구조로 바뀐다.
  - 기존에도 860px 이하 화면에서는 이미 단일 컬럼으로 자동 전환됐다(`@media (max-width: 860px)`).
    이번 변경은 그 레이아웃을 모든 화면 폭에서 기본값으로 만드는 것과 같다 — 기존 미디어쿼리 규칙은
    제거하거나 무의미해지므로 정리한다.
- `aside.console`의 사이드바 전용 스타일(`max-height: 560px; overflow-y: auto`)을 제거 — 페이지
  자연 스크롤에 맡기고 내부 스크롤 박스를 없앤다.
- 타이포그래피:
  - `.feed-item .ftext`: `font-size` 0.86rem → 1rem, `line-height` 1.7 추가.
  - `.feed-item .fhead`(애널리스트명+시각): `font-size` 0.75rem → 0.8rem.
  - `.feed-item` 내부 padding/margin을 소폭 확대(예: padding 8px 10px → 12px 14px, margin-bottom
    10px → 14px)해 항목 간 여백도 함께 늘린다.

## 테스트 전략

이 저장소는 자동 테스트 프레임워크가 없다(기존 계획들과 동일 컨벤션). 수동 실행 확인으로 검증한다:

1. `python scripts\generate_office.py` 재실행 → `office\index.html` 정적 스냅샷 갱신.
2. 정적 스냅샷(`office/index.html`)을 브라우저로 열어 확인: 오피스맵 아래 `Report`가 전체폭으로
   펼쳐지고, 문단이 이전보다 넓게 표시되며 글자가 커졌는지 확인.
3. `python scripts\serve_office.py`로 라이브 버전도 동일하게 확인.
4. 860px 이하 좁은 창(모바일 폭)에서도 레이아웃이 깨지지 않는지 확인(기존에도 단일 컬럼이었으므로
   회귀 위험 낮음).
5. 라이트/다크 테마 둘 다 확인(`--panel-bg`, `--border` 등 기존 CSS 변수 그대로 사용하므로 회귀
   위험 낮음).
