import boto3
import pandas as pd
import json
import time
import uuid
import argparse
import joblib
import os

QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/452383571300/fraud-detection-transactions"
DELAY_SECONDS = 0.01

# Path to the scaler saved during model training (one directory up from producer)
SCALER_PATH = os.path.join(os.path.dirname(__file__), '..', 'scaler.pkl')


def load_transactions(csv_path: str, limit: int, skip: int) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    # Use the scaler saved during training so Amount/Time are normalized
    # with the exact same parameters the model was trained on
    scaler = joblib.load(SCALER_PATH)
    df[['Amount_scaled', 'Time_scaled']] = scaler.transform(df[['Amount', 'Time']])

    df = df.drop(columns=["Amount", "Time", "Class"])
    return df.iloc[skip:skip + limit]


def send_transaction(sqs, features: list) -> None:
    message = {
        "transaction_id": str(uuid.uuid4()),
        "features": features
    }
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(message)
    )
    print(f"Sent: {message['transaction_id']}")


def run(csv_path: str, limit: int, skip: int) -> None:
    sqs = boto3.client("sqs", region_name="us-east-1")
    df = load_transactions(csv_path, limit, skip)

    print(f"Sending {len(df)} transactions to SQS...")
    for _, row in df.iterrows():
        send_transaction(sqs, row.tolist())
        time.sleep(DELAY_SECONDS)

    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="creditcard.csv")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--skip", type=int, default=0)
    args = parser.parse_args()

    run(args.csv, args.limit, args.skip)
