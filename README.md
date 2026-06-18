# CUSTOMER-BEHAVIOR-PIPELINE
## Overview
Customer-behavior-pipeline ingests simulated customer events, processes them, trains machine learning models to predict behavior (e.g., churn, engagement), and exposes model inference and management endpoints via FastAPI.
## Features
* REST API for inference, training, and status
* Data ingestion and preprocessing pipeline
* Synthetic data generator for experiments
* Configurable training pipeline (train, evaluate, save)
* Model versioning and simple persistence
* Basic logging and metrics endpoints
* Unit tests and example requests
## Architecture
* FastAPI app: endpoints for ingestion, training, evaluation, inference, and health
* Data layer: simulated data generator, ingestion queue, preprocessing
* Training pipeline: dataset builder, feature engineering, model trainer, evaluator
* Persistence: model store (filesystem by default), artifacts, and logs
## Run the API
### "File"
## Project layout
app/
└── main.py # FastAPI app and router registration
api/
└── endpoints.py # Inference, train, eval, ingest, health endpoints
core/
├── config.py # app settings
└── logging.py
data/
├── generator.py # synthetic data generator
├── ingest.py # ingestion helpers
└── preprocess.py # feature engineering
models/
├── trainer.py # training loop and hyperparams
├── evaluator.py
├── store.py # save/load models
├── schemas.py # Pydantic models for requests/responses
└──tasks.py # background job orchestration
tests/
requirements.txt
README.md

# Data pipeline
1. Synthetic data generation (configurable personas, sessions, events)
2. Ingestion endpoint writes to in-memory queue or storage
3. Preprocessing: cleaning, sessionization, feature extraction, label generation
4. Dataset split: train/val/test with reproducible seeds
5. Persist processed datasets for reproducibility
