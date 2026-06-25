import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # Database configuration
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 5432))
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "") 
    DB_NAME = os.environ.get("DB_NAME", "supply_chain_db")
    DB_SSLMODE = os.environ.get("DB_SSLMODE", "require")
    
    # SQLAlchemy Connection URI
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSLMODE}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    if not JWT_SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY environment variable must be set.")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    DATASET_PATH = os.path.join(BASE_DIR, "dataset", "DataCoSupplyChainDataset.csv")
    MODEL_PATH = os.path.join(BASE_DIR, "ml", "risk_classifier.joblib")
    ENCODER_PATH = os.path.join(BASE_DIR, "ml", "encoders.joblib")
    
    # Ensure directories exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
