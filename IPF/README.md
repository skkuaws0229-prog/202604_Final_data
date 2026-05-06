# IPF Drug Repurposing ??Final Data for DB/Frontend

## 媛쒖슂
- 吏덊솚: Idiopathic Pulmonary Fibrosis (IPF)
- 紐⑹쟻: Neo4j, Vector DB, FastAPI ?꾨줎?몄뿏???곕룞??理쒖쥌 寃곌낵 ?곗씠??- ?뚯씠?꾨씪?? v1.0 2A Boosting 3-Ensemble + CT-CLIP Image Modal
- ?좎쭨: 2026-05-04 ~ 2026-05-05

## ?붾젆?좊━ ?ㅻ챸

### 0.Image_modal_IPF/
CT-CLIP 湲곕컲 ?대?吏 紐⑤떖 寃곌낵. OSIC 176紐??섏옄 clustering + ?쎈Ъ stratification 媛??

### 1.Drug_results/
?듭떖 ?쎈Ъ 異붿쿇 ?곗씠?? ?꾨줎?몄뿏?쒖뿉??吏곸젒 ?쎈뒗 ?뚯씪??
- ipf_final_15_tiered.csv: 理쒖쥌 15媛??쎈Ъ (Tier 遺꾨쪟 ?ы븿)
- ipf_top30_clinical_reranked.csv: ?꾩긽 蹂닿컯??Top30
- ipf_admet_22assay_results.csv: ADMET 22 assay ?꾩껜 寃곌낵
- ipf_reference_drugs.csv: ?뚯씠?꾨씪?몄뿉 ?녿뒗 IPF 愿???쎈Ъ 李멸퀬 紐⑸줉

### 2.External_validation/
?몃?寃利?寃곌낵. GSE110147 + GSE150910 held-out ?됯?.

### 3.Model_metadata/
紐⑤뜽 媛以묒튂, ?꾨줈?좎퐳, ?쎈Ъ-?寃?留ㅽ븨 ??硫뷀??곗씠??

### 4.Cluster_drug_mapping/
?대?吏 紐⑤떖 clustering 寃곌낵 횞 ?쎈Ъ MoA 媛??留ㅽ븨.

## 二쇱슂 ?섏튂
- ?몃?寃利?Spearman: 0.94
- 理쒖쥌 ?쎈Ъ: 15媛?(Tier1: 1, Tier2: 7, Tier4: 7)
- ?대?吏 ?대윭?ㅽ꽣: K=2 (preserved-FVC vs fibrotic)
- ADMET Hard Fail: 2媛??쒖닔 ?덈씫, 3媛?Clinical Context ?좎?
