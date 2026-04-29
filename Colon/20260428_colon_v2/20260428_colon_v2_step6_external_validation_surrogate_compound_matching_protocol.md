# Step6 외부검증 — 표기 불일치 시 대리 화합물(surrogate) 규칙

PRISM·ClinicalTrials 등 공개 표에는 후보 약물명이 없어 **직접 명칭 매칭이 불가**한 경우에 적용한다.

## 적용 순위

1. **직접 매칭**: 동일 표기, 공식 동의어, 염(salt) 형태, 별칭 JSON(`colon_validation_drug_aliases.json`)으로 해결.
2. **대리 매칭**: 아래 조건을 만족하는 **다른 화합물**을 근거와 함께 지정한다.

## 대리 화합물 선정 조건 (반드시 만족)

- **동일 primary target**: 예측 파이프라인의 `TARGET` 열과 동일 유전자·단백질 표적을 PRISM/선택 DB에서 명시하는 후보.
- **또는 동일 MOA 계열**: `TARGET_PATHWAY`(또는 동등 분류)가 동일하고, 동일 약리 클래스(예: TOP1 억제, BCL2 family 억제)로 문헌·DB에서 확인 가능한 경우.

우선순위는 **동일 target > 동일 pathway 내 동일 MOA class**이다.

## 금지·주의

- 문자열 유사도만으로 무관한 화합물을 연결하지 않는다.
- 서로 다른 표적·다른 pathway인데 이름만 비슷한 경우 대리로 쓰지 않는다.

## 기록 항목 (감사·재현용)

대리를 사용할 때마다 다음을 결과 테이블 또는 부록에 남긴다.

| 필드 | 내용 |
|------|------|
| `candidate_drug` | 모델이 예측한 원래 약물명 |
| `surrogate_drug` | 외부 DB에서 실제로 매칭한 약물명 |
| `surrogate_source` | 예: PRISM secondary/primary, ClinicalTrials intervention 문자열 등 |
| `surrogate_id` | 가능하면 `broad_id`(PRISM), `NCT`/약물 문자열 등 식별자 |
| `match_basis` | `same_target` 또는 `same_moa_pathway` |
| `evidence_note` | 표적/MOA 근거 한 줄(예: 둘 다 TOP1 inhibitor) |

## 예시 (이번 코호트에서의 참고)

- **TOP1 계열**: 후보가 라이브러리 미포함이면, 동일 스크린 내 다른 TOP1 저해제(예: 스크린에 존재하는 irinotecan/topotecan 계열)를 대리로 두되, 위 표를 채운다.
- **BCL2 계열**: Sabutoclax 미포함 시, 같은 스크린에 존재하는 동일 계열(navitoclax/obatoclax 등)은 **별도 행**으로 surrogate 매칭을 기록할 수 있다(원약물 행을 surrogate로 덮어쓰지 않음).

---

이 규칙은 메인 프로토콜 문서(`20260420_colon_protocol.md` 등)의 Step6 절에 요약 링크로 포함하는 것을 권장한다.
