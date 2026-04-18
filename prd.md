# PRD: CDK Apache Airflow

## tl;dr

AWS CDK infrastructure for running Apache Airflow on ECS with EFS shared storage, RDS PostgreSQL metadata backend, S3 XCom backend, and automated DAG deployment via GitHub Actions.

---

## Goals

- **Scalable Airflow on ECS**: Run Airflow Webserver, Scheduler, and Worker as separate ECS services with independent capacity providers
- **EFS Shared Storage**: Store DAGs and plugins on EFS so all containers share the same files
- **Cost Optimization**: Use EC2 capacity providers with auto-scaling groups; right-sized instances for webserver/scheduler vs. worker
- **CI/CD for DAGs**: GitHub Actions deploys DAGs directly to EFS, keeping all containers in sync
- **Production-Ready**: SSL termination, Route53 DNS, S3 remote logging, custom XCom backend for large payloads

## User Stories

- As a **data engineer**, I want DAGs deployed automatically from Git so I don't manually copy files
- As a **devops engineer**, I want CDK-managed infrastructure so I can reproduce and version the entire stack
- As a **platform engineer**, I want worker auto-scaling so the cluster handles load spikes without manual intervention
- As a **data engineer**, I want large XCom values stored in S3 (Parquet/JSON) so tasks don't fail on payload size limits

## Data Flow

```text
1. Developer pushes DAGs to GitHub repository
   ↓
2. GitHub Actions syncs DAGs to EFS via DataSync
   ↓
3. Airflow Scheduler detects new DAGs (polls every 15s in dev, 600s in prod)
   ↓
4. Scheduler queues task execution on Celery Workers
   ↓
5. Workers execute tasks; XCom results stored in S3 for large payloads
   ↓
6. Logs streamed to S3; Airflow UI accessible via ALB + Route53
```

## Core Components

### CDK Stack (AWS Infrastructure)

- **ECS Cluster**: Fargate capacity providers for webserver/scheduler; EC2 ASG capacity providers for workers
- **Application Load Balancer**: HTTPS termination with ACM certificate; Route53 public and private DNS
- **EFS**: Shared filesystem mounted across all Airflow containers for DAGs, plugins, and configs
- **RDS PostgreSQL**: Airflow metadata database with Secrets Manager credentials
- **S3 Buckets**: Log storage with lifecycle rules (IA after 30 days) and XCom payload storage

### Airflow Services (ECS Tasks)

- **Webserver**: Flask web UI on port 8080; health-checked via ALB target group
- **Scheduler**: Polls DAGs, queues tasks; paired with webserver in same task definition
- **Worker**: Celery executor with SQS broker; separate task definition with higher CPU/memory; auto-scaling on CPU/memory

### Custom XCom Backend

- `S3XComBackend`: Serializes large XCom values to S3 (Parquet for DataFrames, JSON for dicts); falls back to standard XCom for small values

### Configuration

- Environment-driven: `STAGE` variable controls prod vs. dev settings (DAG polling interval, auto-scaling limits, domain)
- Container definitions: Webserver (1 CPU, 2 GiB), Scheduler (1 CPU, 2 GiB), Worker (2 CPU, 4 GiB)
- Security groups imported from SSM parameters for VPC isolation

## References

- [Architecture Diagram](./diagram.puml)
- Blog post: [Scalable ETL Pipelines](https://yokharian.dev/posts/apache-airflow-architecture-design)
