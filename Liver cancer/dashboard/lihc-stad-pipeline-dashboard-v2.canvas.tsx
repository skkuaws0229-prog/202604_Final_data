import { Grid, H1, H2, Pill, Row, Stack, Stat, Table, Text } from "cursor/canvas";

const readinessRows = [
  ["Candidate Pool", "READY", "results/lihc_candidate_pool_v2.csv"],
  ["Step4 v2 results", "READY", "STAD → results/20260428_liver_step4_v2/"],
  ["Metrics review CSV", "READY", "STAD → reports/step4_metrics_review_20260428_liver_step4_v2*.csv"],
  ["Directive ensemble + Top30 tier", "READY", "ensemble_lihc_v2_* + prepare_lihc_v2_top30_dedup_tiered.py"],
  ["S3 repro bundle uploaded", "READY", "s3://…/Liver/generated/repro_20260428_liver_step4_v2_20260429/"],
  ["Step6 external validation", "PARTIAL", "소스 미비 시 PENDING_DATA — sources/ 채우면 OK"],
  ["Step7 ADMET + Top15", "OPTIONAL", "bash scripts/run_liver_oneclick_v2.sh"],
];

const pathRows = [
  ["v2 Protocol", "reports/LIHC_STAD_operational_protocol_20260428_v2.md"],
  ["v2 Execution Report", "reports/LIHC_STAD_execution_report_20260428_v2.md"],
  ["v2 Runbook", "reports/LIVER_ONECLICK_RUNBOOK_v2.md"],
  ["S3 repro handoff", "reports/LIHC_V2_S3_REPRO_HANDOFF.md"],
  ["Package script", "scripts/package_lihc_v2_repro_bundle.sh"],
  ["Upload script", "scripts/upload_lihc_v2_repro_to_s3.sh"],
  ["v2 One-click", "scripts/run_liver_oneclick_v2.sh"],
];

export default function LihcStadPipelineDashboardV2() {
  return (
    <Stack gap={16}>
      <H1>LIHC-STAD v2 Dashboard</H1>
      <Row gap={8}>
        <Pill tone="info">Track: v2</Pill>
        <Pill tone="warning">No Overwrite Policy</Pill>
        <Pill tone="positive">Stage: Step4 complete + S3 repro bundle</Pill>
      </Row>
      <Grid columns={4} gap={12}>
        <Stat label="Result tag" value="20260428_liver_step4_v2" />
        <Stat label="S3 bundle (example)" value="repro_*_20260429" />
        <Stat label="Files in bundle" value="212" />
        <Stat label="Tier1 anchor" value="Sorafenib (optional)" />
      </Grid>
      <H2>Readiness</H2>
      <Table headers={["Item", "Status", "Detail"]} rows={readinessRows} />
      <H2>Key paths</H2>
      <Table headers={["Artifact", "Path"]} rows={pathRows} />
      <Text size="small" tone="secondary">
        STAD root lives alongside this package under 20260421_new_pre_project_biso_STAD. v1 dashboards remain unchanged.
      </Text>
    </Stack>
  );
}
