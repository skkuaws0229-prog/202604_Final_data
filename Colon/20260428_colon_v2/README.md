# 20260428_colon_v2 — 대장암(CRC) 재현 패키지

## 문서

| 문서 | 내용 |
|------|------|
| [재현 프로토콜](20260428_colon_v2_reproduction_protocol.md) | Step4–7 입력·출력·명령어 |
| [파이프라인 보고서](reports/20260428_colon_v2_pipeline_report_step6_step7.md) | Step6·7 요약·지표·산출물 인덱스 |
| [대리 화합물 규칙](20260428_colon_v2_step6_external_validation_surrogate_compound_matching_protocol.md) | Step6 표기 불일치 시 surrogate 매칭 |
| [S3 재현 번들 안내](S3_REPRODUCTION_MANIFEST.md) | `s3://say2-4team/.../Colon/` 동기화 방법·공유 입력 경로 |

## 최종 추천 (Step7, ADMET 22 assay 반영)

- `20260428_colon_v2_step7_top15_crc_tier1234_admet22assay_choi_protocol.csv`
- `20260428_colon_v2_step7_summary_admet22assay_choi_protocol.json`

## 실행

```bash
bash scripts/20260428_colon_v2_step7_run.sh
```
