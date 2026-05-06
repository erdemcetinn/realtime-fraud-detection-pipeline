import os
import json
import threading
import joblib
import numpy as np
import boto3
import psycopg2
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(title="Fraud Detection Scoring Service")

model = joblib.load("model.pkl")

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "")
RDS_HOST = os.getenv("RDS_HOST", "")
RDS_USER = os.getenv("RDS_USER", "fraudadmin")
RDS_PASSWORD = os.getenv("RDS_PASSWORD", "")
RDS_DB = os.getenv("RDS_DB", "frauddb")

sqs = boto3.client("sqs", region_name="us-east-1")
sns = boto3.client("sns", region_name="us-east-1")


class Transaction(BaseModel):
    transaction_id: str
    features: List[float]


class ScoreResponse(BaseModel):
    transaction_id: str
    fraud_score: float
    is_fraud: bool


def get_db_connection():
    return psycopg2.connect(
        host=RDS_HOST,
        user=RDS_USER,
        password=RDS_PASSWORD,
        dbname=RDS_DB
    )


def init_db() -> None:
    if not RDS_HOST:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fraud_results (
            id SERIAL PRIMARY KEY,
            transaction_id VARCHAR(64),
            fraud_score FLOAT,
            is_fraud BOOLEAN,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_result(result: ScoreResponse) -> None:
    if not RDS_HOST:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO fraud_results (transaction_id, fraud_score, is_fraud) VALUES (%s, %s, %s)",
        (result.transaction_id, result.fraud_score, result.is_fraud)
    )
    conn.commit()
    cur.close()
    conn.close()


def predict(transaction_id: str, features: list) -> ScoreResponse:
    arr = np.array(features).reshape(1, -1)
    fraud_score = float(model.predict_proba(arr)[0][1])
    is_fraud = fraud_score >= 0.5
    return ScoreResponse(
        transaction_id=transaction_id,
        fraud_score=round(fraud_score, 4),
        is_fraud=is_fraud
    )


def send_fraud_alert(result: ScoreResponse) -> None:
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="Fraud Alert",
        Message=f"Fraud detected: transaction_id={result.transaction_id}, score={result.fraud_score}"
    )


def process_message(message: dict) -> None:
    body = json.loads(message["Body"])
    result = predict(body["transaction_id"], body["features"])
    print(f"Processed: {result.transaction_id} | score={result.fraud_score} | fraud={result.is_fraud}")
    save_result(result)
    if result.is_fraud and SNS_TOPIC_ARN:
        send_fraud_alert(result)


def sqs_consumer() -> None:
    if not SQS_QUEUE_URL:
        return
    while True:
        response = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20
        )
        for message in response.get("Messages", []):
            process_message(message)
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=message["ReceiptHandle"]
            )


@app.on_event("startup")
def start_consumer() -> None:
    init_db()
    if SQS_QUEUE_URL:
        thread = threading.Thread(target=sqs_consumer, daemon=True)
        thread.start()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/score", response_model=ScoreResponse)
def score(transaction: Transaction):
    return predict(transaction.transaction_id, transaction.features)
