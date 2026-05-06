# Real-Time Fraud Detection Pipeline

End-to-end ML pipeline that detects credit card fraud in real time — trained on 284,807 real transactions, deployed on AWS EKS, consuming live streams from SQS, persisting every result to RDS PostgreSQL, and triggering email alerts the moment fraud is confirmed.

A full demonstration of how a bank's fraud detection system works: from raw data and model training all the way to production infrastructure. The same architecture applies to any high-volume classification problem — anomaly detection, risk scoring, content moderation.

**Verified:** 10,000 transactions streamed → 19 fraud cases detected → email alerts received in real time → 2,217+ rows written to RDS PostgreSQL.

**What this covers:**
- Imbalanced dataset handling — why class weighting beats SMOTE in practice
- ML model deployment as a FastAPI microservice on Kubernetes
- Event-driven pipeline with SQS (producer → queue → consumer)
- Full AWS infrastructure provisioned with Terraform in a single command
- IRSA for secure pod-level AWS access without hardcoded credentials

---

## How it works

```
creditcard.csv (284,807 transactions)
        │
        ▼
  Transaction Producer  ──  Scales Amount + Time with saved scaler.pkl
        │                    Streams batches to SQS (0.01s delay)
        ▼
  Amazon SQS  ──  fraud-detection-transactions queue
        │
        ▼
  Scoring Service (EKS)  ──  FastAPI + XGBoost
        │                     SQS consumer (long polling, background thread)
        │                     predict_proba() on every transaction
        │                     fraud_score >= 0.5 → is_fraud = True
        │
        ├──▶  RDS PostgreSQL  ──  Every transaction result persisted
        │
        └──▶  SNS Email Alert  ──  Triggered on confirmed fraud only
```

---

## ML Model

Trained on [Kaggle Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud) — 284,807 transactions, 492 fraud (0.17%).

**Why `scale_pos_weight` over SMOTE:**
SMOTE improved recall but produced a 0.98 decision threshold — the model only flagged fraud when 98% confident. Class weighting penalizes missed fraud 577x without generating synthetic samples, giving a better overall balance.

| Model | Precision | Recall | F1 | ROC-AUC |
|-------|-----------|--------|----|---------|
| Base XGBoost | 0.92 | 0.81 | 0.86 | — |
| XGBoost + SMOTE | 0.73 | 0.89 | 0.80 | — |
| **XGBoost + Class Weight** | **0.88** | **0.85** | **0.86** | **0.9652** |
| Stacking (XGB + LightGBM) | 0.90 | 0.80 | 0.84 | 0.9736 |

Class weight model selected — higher recall means fewer missed fraud cases.

---

## Setup

**Requirements:** Python 3.9+, AWS CLI, Terraform, Docker, kubectl, eksctl

```bash
# 1. Clone
git clone https://github.com/erdemcetinn/realtime-fraud-detection-pipeline
cd realtime-fraud-detection-pipeline

# 2. Train the model (generates model.pkl and scaler.pkl)
pip install -r scoring-service/requirements.txt
# Run fraud_detection.ipynb top to bottom

# 3. Provision AWS infrastructure
cd terraform
terraform init
terraform apply

# 4. Build and push Docker image
cd ../scoring-service
docker build --platform linux/amd64 -t scoring-service .
docker tag scoring-service <ECR_URL>/scoring-service:latest
docker push <ECR_URL>/scoring-service:latest

# 5. Deploy to EKS
aws eks update-kubeconfig --name fraud-detection-cluster --region us-east-1
kubectl apply -f ../k8s/scoring-service.yaml

# 6. Stream transactions
cd ../transaction-producer
pip install -r requirements.txt
python producer.py --csv creditcard.csv --limit 10000 --skip 5000
```

---

## Key Features

**IRSA (IAM Roles for Service Accounts)** — Pod gets AWS credentials via IAM role bound to its Kubernetes service account. No hardcoded secrets, no environment variables with credentials.

**Long polling SQS consumer** — `WaitTimeSeconds=20` minimizes empty receives. Consumer runs in a background thread so FastAPI continues serving HTTP requests simultaneously.

**Scaler consistency** — `scaler.pkl` is saved during training and loaded by the producer at inference time. Both use identical normalization parameters.

**Idempotent DB init** — `CREATE TABLE IF NOT EXISTS` runs at startup. Safe to restart the pod at any time.

**linux/amd64 Docker build** — Apple Silicon Macs build ARM images by default. EKS nodes are x86_64. `--platform linux/amd64` flag ensures compatibility.

---

## Infrastructure

24 AWS resources provisioned with a single `terraform apply`:

| Resource | Details |
|----------|---------|
| VPC | 10.0.0.0/16, 2 public + 2 private subnets, 2 AZs |
| EKS | Kubernetes 1.35, t3.small nodes (min:1 max:3) |
| RDS | PostgreSQL 15, db.t3.micro, private subnet |
| SQS | fraud-detection-transactions queue |
| SNS | fraud-detection-alerts topic + email subscription |
| ECR | Docker image registry |
| IAM | IRSA roles for pod-level SQS + SNS access |

---

## Project Structure

```
.
├── fraud_detection.ipynb       # EDA, SMOTE vs class weight comparison, model training
├── scoring-service/
│   ├── main.py                 # FastAPI + SQS consumer + RDS writer + SNS alerts
│   ├── Dockerfile
│   └── requirements.txt
├── transaction-producer/
│   └── producer.py             # CSV reader → scale → SQS sender
├── terraform/
│   ├── vpc.tf
│   ├── eks.tf
│   ├── rds.tf
│   ├── sqs.tf
│   ├── sns.tf
│   └── outputs.tf
└── k8s/
    └── scoring-service.yaml    # Deployment + LoadBalancer Service
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML | XGBoost, scikit-learn, LightGBM |
| API | FastAPI, Uvicorn |
| Compute | AWS EKS (Kubernetes) |
| Queue | AWS SQS |
| Alerts | AWS SNS |
| Database | AWS RDS PostgreSQL |
| Container Registry | AWS ECR |
| Infrastructure | Terraform |
| Auth | IRSA (IAM Roles for Service Accounts) |
