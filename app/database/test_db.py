from database import engine
import sqlalchemy as sa

def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(sa.text("SELECT 1"))
            print("Database connection successful!")
            return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()
