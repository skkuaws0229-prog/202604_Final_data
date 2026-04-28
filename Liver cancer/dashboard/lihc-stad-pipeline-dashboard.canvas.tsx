import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useCanvasState,
} from "cursor/canvas";

type StageKey = "overview" | "step45" | "step6" | "step7" | "paths";
type TierFilter = "all" | "tier1" | "tier2" | "tier3" | "tier4";

const step6SourceRows = [
  ["PRISM", "OK", "30"],
  ["ClinicalTrials", "OK", "17"],
  ["GEO", "OK", "7"],
  ["OpenTargets", "OK", "13"],
  ["COSMIC", "OK", "8"],
  ["CPTAC", "EXCLUDED_BY_REQUEST", "0"],
];

const top15TierRows = [
  ["tier1", "0", "HCC-approved and ADMET PASS"],
  ["tier2", "5", "ADMET PASS but not HCC-approved"],
  ["tier3", "8", "ADMET WARNING with multi-source support"],
  ["tier4", "2", "ADMET WARNING with limited support"],
];

const top15DetailRows = [
  ["1", "Topotecan", "tier2", "7.50", "5", "1", "1", "1", "1", "1"],
  ["2", "Irinotecan", "tier2", "6.40", "5", "1", "1", "1", "1", "1"],
  ["3", "Camptothecin", "tier2", "6.25", "5", "1", "1", "1", "1", "1"],
  ["4", "Vinorelbine", "tier2", "7.25", "2", "1", "1", "0", "0", "0"],
  ["5", "Vinblastine", "tier2", "7.00", "2", "1", "1", "0", "0", "0"],
  ["6", "Temsirolimus", "tier3", "5.50", "4", "1", "1", "0", "1", "1"],
  ["7", "Rapamycin", "tier3", "5.50", "2", "1", "1", "0", "0", "0"],
  ["8", "Staurosporine", "tier3", "5.25", "2", "1", "1", "0", "0", "0"],
  ["9", "Bosutinib", "tier3", "5.25", "4", "1", "1", "0", "1", "1"],
  ["10", "Bleomycin", "tier3", "5.00", "2", "1", "1", "0", "0", "0"],
  ["11", "Elesclomol", "tier3", "5.00", "2", "1", "1", "0", "0", "0"],
  ["12", "MG-132", "tier3", "5.00", "3", "1", "0", "1", "1", "0"],
  ["13", "Lestaurtinib", "tier3", "5.00", "3", "1", "0", "0", "1", "1"],
  ["14", "Bleomycin (50 uM)", "tier4", "5.00", "1", "1", "0", "0", "0", "0"],
  ["15", "CCT-018159", "tier4", "5.00", "1", "1", "0", "0", "0", "0"],
];

const keyPathRows = [
  ["S3 Liver Root", "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/"],
  ["S3 Raw Source", "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/raw_source/"],
  ["S3 FE Data", "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/fe_data/"],
  ["S3 Generated", "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/generated/"],
  ["S3 Protocol Files", "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/protocol_used_files/"],
  ["Ensemble Directive", "s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/protocol_used_files/docs/LIHC_ensemble_directive.md"],
  ["Step4/5 Ensemble Summary", "results/20260428_liver_step4_cv5_gc_sc/lihc_directive_ensemble_summary.json"],
  ["Step4/5 Top30 With Names", "results/20260428_liver_step4_cv5_gc_sc/lihc_top30_directive_ensemble_with_names.csv"],
  ["Step6 External Summary", "external_validation/20260428_liver_step4_cv5_gc_sc/external_validation_lihc_cptac_excluded_summary.json"],
  ["Step6 External Table", "external_validation/20260428_liver_step4_cv5_gc_sc/top30_external_validation_lihc_cptac_excluded.csv"],
  ["Step7 ADMET Summary", "results/stad_admet_summary.json"],
  ["Step7 Final Top15 (Base)", "results/lihc_final_top15.csv"],
  ["Step7 Final Top15 (Tier1-4)", "results/lihc_step7_final_top15_tier4.csv"],
  ["Execution Report", "reports/LIHC_STAD_execution_report_20260428.md"],
  ["Operational Protocol", "reports/LIHC_STAD_operational_protocol_20260428.md"],
];

function StageButtons({
  stage,
  setStage,
}: {
  stage: StageKey;
  setStage: (next: StageKey) => void;
}) {
  const items: Array<{ id: StageKey; label: string }> = [
    { id: "overview", label: "Overview" },
    { id: "step45", label: "Step4/5" },
    { id: "step6", label: "Step6" },
    { id: "step7", label: "Step7" },
    { id: "paths", label: "File Locations" },
  ];
  return (
    <Row gap={8} wrap>
      {items.map((item) => (
        <Button
          key={item.id}
          onClick={() => setStage(item.id)}
          variant={stage === item.id ? "primary" : "outline"}
        >
          {item.label}
        </Button>
      ))}
    </Row>
  );
}

function OverviewSection() {
  return (
    <Stack gap={12}>
      <Grid columns={4} gap={12}>
        <Stat label="Result Tag" value="20260428_liver_step4_cv5_gc_sc" />
        <Stat label="Top30 Input" value="30" />
        <Stat label="Final Top15" value="15" />
        <Stat label="CPTAC Mode" value="Excluded" />
      </Grid>
      <Card>
        <CardHeader title="Run Scope" />
        <CardBody>
          <Stack gap={8}>
            <Text>Protocol code axis: STAD</Text>
            <Text>Training/validation data axis: LIHC (liver)</Text>
            <Text>External validation mode: CPTAC excluded by request</Text>
            <Text>Step7 recommendation rule: HCC approval criteria (not gastric)</Text>
            <Text>S3 handoff root: s3://say2-4team/20260408_new_pre_project_biso/202604_Final_data/Liver/</Text>
          </Stack>
        </CardBody>
      </Card>
    </Stack>
  );
}

function Step45Section() {
  return (
    <Stack gap={12}>
      <Grid columns={3} gap={12}>
        <Stat label="OOF Eval Mode" value="groupcv_oof" />
        <Stat label="OOF Spearman" value="0.5754" />
        <Stat label="Ensemble Models" value="6 weighted members" />
      </Grid>
      <Card>
        <CardHeader title="Step4/5 Summary" />
        <CardBody>
          <Stack gap={8}>
            <Text>Directive source: LIHC_ensemble_directive.md (S3 protocol docs)</Text>
            <Text>Ensemble: LIHC_directive_weighted_v1</Text>
            <Text>Top30 deduplicated by tradename rule</Text>
            <Text>Primary outputs stored under result tag folder</Text>
          </Stack>
        </CardBody>
      </Card>
    </Stack>
  );
}

function Step6Section() {
  return (
    <Stack gap={12}>
      <H2>Step6 External Validation</H2>
      <Table
        headers={["Source", "Status", "Supported Rows (Top30)"]}
        rows={step6SourceRows}
      />
      <Text size="small" tone="secondary">
        Mode: CPTAC excluded, other sources active and mapped.
      </Text>
    </Stack>
  );
}

function Step7Section({
  tierFilter,
  setTierFilter,
}: {
  tierFilter: TierFilter;
  setTierFilter: (next: TierFilter) => void;
}) {
  const filteredRows =
    tierFilter === "all"
      ? top15DetailRows
      : top15DetailRows.filter((row) => row[2] === tierFilter);

  const filterButtons: Array<{ id: TierFilter; label: string }> = [
    { id: "all", label: "All" },
    { id: "tier1", label: "Tier1" },
    { id: "tier2", label: "Tier2" },
    { id: "tier3", label: "Tier3" },
    { id: "tier4", label: "Tier4" },
  ];

  return (
    <Stack gap={12}>
      <Grid columns={4} gap={12}>
        <Stat label="ADMET Assays" value="22" />
        <Stat label="PASS / WARNING / FAIL" value="5 / 22 / 3" />
        <Stat label="ADMET Gate Pass+Warn" value="27 / 30" />
        <Stat label="HCC Approved in Top15" value="0" />
      </Grid>
      <Table headers={["Tier", "Count", "Rule Note"]} rows={top15TierRows} />
      <Row gap={8} wrap>
        {filterButtons.map((item) => (
          <Button
            key={item.id}
            onClick={() => setTierFilter(item.id)}
            variant={tierFilter === item.id ? "primary" : "outline"}
          >
            {item.label}
          </Button>
        ))}
      </Row>
      <Table
        headers={[
          "Rank",
          "Drug",
          "Tier",
          "Safety",
          "Ext.Support",
          "PRISM",
          "CT",
          "GEO",
          "OT",
          "COSMIC",
        ]}
        rows={filteredRows}
      />
      <Text size="small" tone="secondary">
        CSV download paths: `results/lihc_step7_final_top15_tier4.csv`, `results/lihc_final_top15.csv`, `results/stad_drugs_with_admet.csv`
      </Text>
    </Stack>
  );
}

function PathSection() {
  return (
    <Stack gap={12}>
      <H2>Output Locations</H2>
      <Table headers={["Artifact", "Path"]} rows={keyPathRows} />
    </Stack>
  );
}

export default function LihcStadPipelineDashboard() {
  const [stage, setStage] = useCanvasState<StageKey>("lihc-stad-stage", "overview");
  const [tierFilter, setTierFilter] = useCanvasState<TierFilter>("lihc-stad-tier-filter", "all");
  return (
    <Stack gap={16}>
      <H1>LIHC-STAD Pipeline Dashboard</H1>
      <Row gap={8} align="center">
        <Pill tone="info">Protocol: STAD</Pill>
        <Pill tone="info">Data: LIHC</Pill>
        <Pill tone="warning">CPTAC: Excluded</Pill>
      </Row>
      <StageButtons stage={stage} setStage={setStage} />
      <Divider />
      {stage === "overview" && <OverviewSection />}
      {stage === "step45" && <Step45Section />}
      {stage === "step6" && <Step6Section />}
      {stage === "step7" && <Step7Section tierFilter={tierFilter} setTierFilter={setTierFilter} />}
      {stage === "paths" && <PathSection />}
    </Stack>
  );
}
