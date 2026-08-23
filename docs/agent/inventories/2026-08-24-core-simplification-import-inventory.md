# Core simplification import inventory

This inventory records the current migration drains before the direct-run
façade is introduced. It is source-only evidence: no external raw-data path or
generated-output path is recorded here.

## Search evidence

- Date: 2026-08-23
- Command:

  ```powershell
  rg -l -g '*.py' -e 'run_pipeline' -e 'canonical_experiments' -e 'analysis_evidence' -e 'project_workflow' -e 'agent_workflow' -e 'core\.joint|from polynexus\.core import joint|import rag|from rag' polynexus\cli polynexus\core polynexus\gui rag
  ```

- Follow-up symbol confirmation used scoped `rg -n -C 1` searches against the
  paths named below.

| Area | Current producer | Current consumers | First migration action |
| --- | --- | --- | --- |
| Single run | `polynexus/core/engine.py`: `BaseEngine.run_pipeline` | `polynexus/cli/run_single_service.py`: `run_single`; `polynexus/gui/main_window_workers.py`: `AnalysisWorker.run` | Route both through `ComputeRunService.run_direct`. |
| Canonical conversion | `polynexus/core/canonical_experiments.py`: `CanonicalExperiment`, `default_converter_registry` | `polynexus/core/agent_workflow/tpae.py`: `TpaeCharacterizationWorkflow`; `polynexus/core/agent_workflow/service.py`: `AgentWorkflowService`; `polynexus/core/project_workflow/adapters.py`: technique adapters | Keep unchanged in this slice; replace the status model in a dedicated conversion task. |
| Evidence/review | `polynexus/core/analysis_evidence.py`: `AnalysisEvidence`; `polynexus/core/engine.py`: `AnalysisResult.analysis_evidence` | `polynexus/core/agent_workflow/service.py`: `AgentWorkflowService._run_step`; `polynexus/core/project_workflow/evidence.py` and `writing_metrics.py`; `polynexus/gui/results_review_service.py` and `scientific_review_presentation.py` | Do not import from `core.compute`; drain in a later deletion batch. |
| Paper workflow | `polynexus/core/project_workflow`: `ProjectWorkflowService`, evidence and figure-index contracts | `polynexus/cli/run_project_workflow_service.py`: `run_project_workflow`; `polynexus/gui/evidence_package_view.py`: `EvidencePackageView`; `polynexus/gui/plot_gallery_service.py`: `FigureIndexEntry` | Do not modify in this slice. |
| Agent workflow | `polynexus/core/agent_workflow`: `AgentWorkflowService` | `polynexus/cli/run_agent_workflow_service.py`: `run_agent_workflow` | Do not modify in this slice. |
| Joint/RAG | `polynexus/core/joint`: `JointCoordinator`; `rag/advisor.py`: `Advisor` | `polynexus/gui/main_window_workers.py`: `JointHubWorker.run` and `SAXSOrientationAdvisoryWorker.run`; related GUI joint entry paths are in `polynexus/gui/main_window.py`, `main_window_joint_diagnostics_mixin.py`, and `widgets/joint_analysis_hub.py` | Do not modify in this slice. |

## Protected import rule

The planned `polynexus.core.compute` package is a direct-run façade only. It
must not import evidence/review, paper workflow, agent workflow, Joint, or RAG
modules while the listed consumers are migrated independently.
