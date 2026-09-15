# Harness Packs

Harness packs should extend Conciencia by composing existing primitives:

- agents;
- harnesses;
- workflows;
- missions;
- tools;
- evidence;
- approvals;
- reports.

They must not become duplicated applications with separate mission or approval
models.

## Candidate Packs

Conciencia Media:

research -> concept -> copy -> visual -> review -> approval -> schedule -> publish -> measure

Conciencia Growth:

signals -> research -> qualification -> evidence -> CRM -> outreach approval -> measurement

## V1 Contract

A pack should contribute:

- workflow definitions;
- harness specifications and tool policy;
- agent capability requirements;
- approval gates;
- report/evidence conventions;
- command registry metadata.

Execution remains owned by `mission_service` and `workflow_engine`.
