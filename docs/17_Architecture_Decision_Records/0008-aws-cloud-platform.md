# ADR-0008 — Cloud Platform: AWS + EKS + Helm

**Status:** Superseded by [ADR-0014](./0014-cost-minimized-open-source-stack.md)
**Date:** 2026-08-10
**Superseded:** 2026-08-10
**Related:** [ADR-0001](./0001-nextjs-fastapi-stack.md) · [12_DevOps_Architecture](../12_DevOps_Architecture.md)
**Resolves:** OD-3 (cloud provider), OD-4 (manifest tooling)

## Context
The platform needs a cloud provider and a Kubernetes manifest strategy. The choice cascades into identity (OD-2), managed data services, and hosting (OD-7). The design (docs/12) requires three environments (dev/staging/prod), OTel observability, and containerized deployment.

## Decision
- **Cloud provider: AWS.** EKS for Kubernetes; managed services where the design calls for them (see Consequences).
- **Manifest tooling: Helm.** All workloads deployed via Helm charts with environment overlays.
- Temporal and Keycloak (see ADR-0009, ADR-0010) are installed from their official upstream Helm charts.

## Consequences
### Positive
- Broadest managed-service coverage: RDS (Postgres), OpenSearch (escape hatch for OD-5), S3 (snapshots/reports), ECR, EKS, Bedrock (embeddings, ADR-0012), Managed Prometheus/Grafana.
- Helm is the de-facto standard for EKS; Temporal and Keycloak ship official charts, avoiding re-implementation.
- SAP workloads are well supported on AWS should the product later integrate SAP BTP-side.
### Negative / Trade-offs
- AWS is not the strongest SAP-on-cloud ecosystem (Azure has the leading SAP partnership); acceptable because SAIE observes the SAP ecosystem rather than running SAP itself.
- Managed services add per-environment cost and IAM surface to govern.
- Operator/maintenance overhead of EKS is higher than a fully serverless approach; justified by the stateful orchestration (Temporal) and worker fleet.
### Neutral
- Helm is used with kustomize-free overlays per environment (values files + sealed secrets).
- Cloud-specific services are confined behind adapters (search, storage, secrets) so the platform stays portable.
