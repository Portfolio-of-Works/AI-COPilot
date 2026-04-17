import os
import urllib.parse
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# --- ENVIRONMENT VARIABLES ---
# This pulls the values from your system or Cloud Run settings.
# If it can't find them, it uses 'postgres' as a default for user and name.
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")  # No default for security!
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME", "postgres")

# Check if we actually got the secrets before building the URL
if not DB_PASS or not DB_HOST:
    # During local development, you might want a print warning
    print("Warning: DB_PASS or DB_HOST not set in environment variables.")

# 2. This safely "cleans" your password for the URL
safe_pass = urllib.parse.quote_plus(DB_PASS) if DB_PASS else ""

# 3. This builds the connection string
DATABASE_URL = f"postgresql://{DB_USER}:{safe_pass}@{DB_HOST}:5432/{DB_NAME}"

# 1. Start the Database Engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Define the Table Schema (The "Filing Cabinet")
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), index=True)  # Links messages to a specific user session
    user_message = Column(Text, nullable=False)  # What the auditor asked
    ai_response = Column(Text, nullable=False)   # What Dialogflow answered
    timestamp = Column(DateTime, default=datetime.utcnow) # When it happened

# 3. Create the tables in the database
def init_db():
    Base.metadata.create_all(bind=engine)

# 4. Helper function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()