# Real-Time Fraud Detection Pipeline

A production-grade, event-driven fraud detection system built on AWS. An XGBoost model trained on 284,807 real credit card transactions is deployed as a microservice on Amazon EKS, consuming live transaction streams from SQS, scoring in real time, persisting results to RDS PostgreSQL, and triggering SNS email alerts on confirmed fraud.

**Verified end-to-end:** 10,000 transactions streamed, 19 fraud cases detected, email alerts received in real time, 2,217+ results written to RDS PostgreSQL.

---

## Architecture

```
[LOCAL]
Transaction Producer (Python)
  - Reads creditcard.csv (284,807 transactions)
  - Scales Amount + Time with saved scaler.pkl
  - Streams batches to SQS

        ↓ Amazon SQS (fraud-detection-transactions)

[AWS EKS — fraud-detection-cluster]
Scoring Service (FastAPI + XGBoost)
  - SQS consumer running in background thread (long polling)
  - Loads model.pkl at startup, keeps in memory
  - Runs predict_proba() for every transaction
  - fraud_score >= 0.5 → is_fraud = True

        ↓

  ┌──────────────────────────────────┐
  │ Every transaction                │
  │ → RDS PostgreSQL (fraud_results) │
  └──────────────────────────────────┘

  ┌──────────────────────────────────┐
  │ If is_fraud = True               │
  │ → SNS → Email alert              │
  └──────────────────────────────────┘
```

---

## ML Model

- **Dataset:** Kaggle Credit Card Fraud Detection — 284,807 transactions, 492 fraud (0.17%)
- **Features:** V1-V28 (PCA-anonymized by dataset provider), Amount_scaled, Time_scaled
- **Algorithm:** XGBoost with `scale_pos_weight=577` to handle class imbalance
- **Why not SMOTE:** SMOTE improved recall but reduced precision and produced an unusable 0.98 decision threshold. Class weighting gave better overall balance.
- **Most important feature:** V14 (62.6% importance)
- **Decision threshold:** 0.5

| Model | Precision | Recall | F1 | ROC-AUC |
|-------|-----------|--------|----|---------|
| Base XGBoost | 0.92 | 0.81 | 0.86 | — |
| XGBoost + SMOTE | 0.73 | 0.89 | 0.80 | — |
| **XGBoost + Class Weight** | **0.88** | **0.85** | **0.86** | **0.9652** |
| Stacking (XGB + LightGBM) | 0.90 | 0.80 | 0.84 | 0.9736 |

The class weight model was selected for production — higher recall means fewer missed fraud cases.

---

## AWS Infrastructure (Terraform)

24 resources provisioned in a single `terraform apply`:

- VPC (10.0.0.0/16), 2 public + 2 private subnets across 2 AZs
- Internet Gateway + Route Tables
- EKS Cluster (Kubernetes 1.35) + Node Group (t3.small, min:1 max:3)
- ECR repository for Docker image
- IAM Roles for EKS cluster + node group
- **IRSA** (IAM Roles for Service Accounts) — pod-level AWS credentials, no hardcoded secrets
- RDS PostgreSQL 15 (db.t3.micro, private subnet)
- SQS queue: `fraud-detection-transactions`
- SNS topic: `fraud-detection-alerts` + email subscription

---

## Project Structure

```
realtime-fraud-detection/
├── fraud_detection.ipynb       # ML pipeline: EDA, SMOTE comparison, model training
├── scoring-service/
│   ├── main.py                 # FastAPI + SQS consumer + RDS writer + SNS alerts
│   ├── Dockerfile
│   └── requirements.txt
├── transaction-producer/
│   └── producer.py             # Reads CSV, scales features, streams to SQS
├── terraform/
│   ├── main.tf
│   ├── vpc.tf
│   ├── eks.tf
│   ├── rds.tf
│   ├── sqs.tf
│   ├── sns.tf
│   ├── variables.tf
│   └── outputs.tf
└── k8s/
    └── scoring-service.yaml    # Kubernetes Deployment + LoadBalancer Service
```

---

## Stack

- **ML:** XGBoost, scikit-learn, LightGBM
- **API:** FastAPI, Uvicorn
- **AWS:** EKS, SQS, SNS, RDS PostgreSQL, ECR, IAM
- **IaC:** Terraform
- **Container:** Docker (linux/amd64)
- **Orchestration:** Kubernetes
