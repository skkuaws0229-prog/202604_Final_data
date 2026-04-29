# STAD Step 2-3 완료 공지 (2026-04-21)

## ✅ 완료 단계
- **Step 2** 전처리 + depmap 재필터링
- **Step 3** FE (AWS Batch, exit code 0)

## 📦 산출물 (S3)

기반 경로: `s3://say2-4team/20260408_new_pre_project_biso/20260421_new_pre_project_biso_STAD/`

- `data/` — Step 2 산출 (labels, drug_features, depmap, GDSC2, LINCS)
- `fe_output/20260421_stad_fe_v1/features/features.parquet` (shape: 5,118 × 17,925)
- `fe_output/20260421_stad_fe_v1/pair_features/pair_features_newfe_v2.parquet`
- `fe_output/20260421_stad_fe_v1/reports/fe_report_20260421_stad_fe_v1.html`

## 🔑 주요 발견 1: LINCS AGS-only 한계

STAD의 LINCS evidence는 GSE92742의 **AGS cell line만** 사용 가능.
3중 검증으로 확정됨 (2026-04-21).

- 해석은 DepMap/GDSC/PRISM 축 중심
- LINCS는 AGS 보조 신호로만 사용

상세: `STAD_reproduction_protocol.md` §5 "알려진 제한 사항"

## 🔑 주요 발견 2: STAD 고유 depmap 재필터링 필요

Colon/Lung에서는 우연히 문제 없었으나, STAD는 labels와 DepMap 표기 불일치로
FE sample join이 ~60%까지 떨어지는 이슈 발견.

**원인:** Colon은 수동으로 depmap_long을 축소했으나(differences.md 기록), 
STAD는 이 단계가 빠져 있었음.

**해결:** 신규 스크립트 `scripts/filter_stad_depmap_to_labels.py` 작성, 
`run_step2_stad.sh`에 통합 (Colon의 수동 작업을 자동화).

**개선 효과:**
- features_rows: 3,721 → 5,118 (+37.5%)
- sample join: 61.4% → 83.3%
- 4 cells (MKN7, NUGC4, RF48, TGBC11TKB)는 DepMap CRISPR 부재로 정당한 drop

상세: `STAD_reproduction_protocol.md` §2.1, §7.1

## 💡 다른 팀원에게 공유할 사항

### Colon/Lung 담당자
Colon이 "수동으로" 재필터링한 작업은 신규 스크립트로 자동화 가능합니다.
향후 다른 암종 확장 시 `filter_{cancer}_depmap_to_labels.py` 패턴으로 재사용 권장.

STAD 스크립트는 이미 검증됐으니 Colon/Lung에 역으로 적용해도 동일 결과가 나올 것입니다.
(단, Colon/Lung의 기존 FE는 이미 정상 동작 중이므로 당장 수정할 필요는 없음)

### 향후 새 암종 담당자
다음 단계 진입 시 반드시 확인:
1. Step 2 QC 경고의 **지표 이름**을 정확히 읽고 타암종과 동일 지표로 비교
2. "패턴 비슷"으로 넘기지 말 것 — 하루 날리는 원인
3. `labels_cells_in_depmap / labels_unique_cells` 비율이 낮으면 (<50%) 
   진입 금지, 원인 규명 먼저
4. Nextflow awsbatch 실행 시 `-work-dir` 옵션 필수

상세: `STAD_reproduction_protocol.md` §7 "과거 이슈 및 재발 방지"

## 📋 다음 단계 의존성

- **Step 3.5~5 (학습/앙상블/Top30)**: 대장암에서 진행 중, 완료 후 STAD 이식 예정
- **Step 6 (외부 검증)**: Top30 CSV 3종이 필요하므로 Step 3.5~5 완료 대기
- **Step 6 raw 데이터**: 이미 준비 완료 (GSE62254/15459/84437, COSMIC STAD, CPTAC PDC 매니페스트)

## 📚 참조 문서 (읽기 순서)

1. `configs/CONTEXT.md` — 프로젝트 정책, 경로, 절대 규칙 (단일 진실 소스)
2. `README.md` — 현재 상태, 빠른 실행 순서
3. `STAD_reproduction_protocol.md` — 전체 재현 절차
   - §2.1: depmap 재필터링 (STAD 고유)
   - §6.1~6.3: 단계별 체크리스트
   - §7: 과거 이슈 및 재발 방지
4. **검증 리포트** (문제 추적 시):
   - `reports/step2_stad_depmap_refilter.json` — depmap 재필터 매핑
   - `reports/step2_integrated_qc_report.json` — Step 2 통합 QC
   - `reports/step3_row_drop_analysis.json` — 최초 증상 진단
   - `reports/step3_fe_gdsc_parquet_check.json` — 최종 원인 확정
5. **LINCS 검증**:
   - `reports/lincs/stad_lincs_cell_id_qc.json` (1차)
   - `reports/lincs/stad_lincs_gse70138_verification.json` (2차)
   - `reports/lincs/stad_lincs_alias_deep_check.json` (3차)

## 🔧 커밋 / GitHub

- 저장소: `skkuaws0215/20260415_preproject_choi_protocol_v1_bisotest`
- 브랜치: `main`
- 관련 신규/변경 파일:
  - `scripts/filter_stad_depmap_to_labels.py` (신규)
  - `scripts/step2_qc.py` (수정: data/depmap/ 검증 추가)
  - `scripts/run_step2_stad.sh` (수정: depmap 재필터링 단계 추가)
  - `README.md`, `STAD_reproduction_protocol.md`, `configs/CONTEXT.md` (문서 업데이트)
  - `reports/lincs/stad_lincs_gse70138_verification.json` (신규)
  - `reports/step2_stad_depmap_refilter.json` (신규)
  - 기타 진단 리포트 6종 (step3_*.json)

---

**공지 작성자**: 자동 생성 (Cursor + Claude)
**공지 시점**: 2026-04-21
**질문/이슈**: 관련 `reports/` 문서 우선 확인 후, 해결 안 되면 팀 논의
