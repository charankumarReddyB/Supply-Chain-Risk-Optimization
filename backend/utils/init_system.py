import os
import sys
from werkzeug.security import generate_password_hash
from backend.models.database import run_sql_file, execute_query, get_db_connection
from backend.etl.generate_mock_data import generate_data
from backend.etl.run_etl import run_etl_pipeline
from backend.ml.train import train_model

def init_system(skip_db_errors=True):
    print("======================================================================")
    print("            SUPPLY CHAIN SYSTEM INITIALIZATION & SEEDING              ")
    print("======================================================================")
    
    db_available = True
    
    # 1. Create Schema DDL
    current_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.abspath(os.path.join(current_dir, "..", "database_setup.sql"))
    print(f"\nStep 1: Setting up database schema from {schema_path}...")
    try:
        run_sql_file(schema_path)
        print("Database schema created successfully.")
    except Exception as e:
        print(f"Error during schema creation: {e}")
        if skip_db_errors:
            print("[WARNING] Database not accessible. Skipping database schema setup.")
            db_available = False
        else:
            print("Make sure your database server is running and configured correctly in config.py.")
            sys.exit(1)
        
    # 2. Seed Admin and User accounts
    if db_available:
        print("\nStep 2: Seeding admin and user accounts...")
        try:
            # Check if admin exists
            admin_check = execute_query("SELECT id FROM users WHERE username = 'admin'")
            if not admin_check:
                hashed_pwd = generate_password_hash("admin123")
                execute_query(
                    "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
                    ("admin", hashed_pwd, "admin@supplychain.com", "admin"),
                    fetch=False
                )
                print("Admin user created successfully (admin/admin123).")
            else:
                print("Admin user already exists.")

            # Check if user exists
            user_check = execute_query("SELECT id FROM users WHERE username = 'user'")
            if not user_check:
                hashed_pwd = generate_password_hash("user123")
                execute_query(
                    "INSERT INTO users (username, password_hash, email, role) VALUES (%s, %s, %s, %s)",
                    ("user", hashed_pwd, "user@supplychain.com", "user"),
                    fetch=False
                )
                print("Regular user created successfully (user/user123).")
            else:
                print("Regular user already exists.")
        except Exception as e:
            print(f"Error seeding user accounts: {e}")
            if not skip_db_errors:
                sys.exit(1)
    else:
        print("\nStep 2: Seeding user accounts skipped (database not available).")
        
    # 3. Generate Mock Data
    print("\nStep 3: Generating mock DataCo CSV dataset...")
    try:
        generate_data(18500)
    except Exception as e:
        print(f"Error generating mock dataset: {e}")
        sys.exit(1)
        
    # 4. Run ETL Pipeline
    if db_available:
        print("\nStep 4: Running ETL pipeline to clean and load data...")
        try:
            run_etl_pipeline()
            print("ETL pipeline executed successfully. Database populated.")
        except Exception as e:
            print(f"Error running ETL pipeline: {e}")
            if not skip_db_errors:
                sys.exit(1)
    else:
        print("\nStep 4: ETL pipeline skipped (database not available).")
        
    # 5. Train Machine Learning Model
    print("\nStep 5: Training Decision Tree risk classifier...")
    try:
        train_model()
        print("ML Model trained and assets exported successfully.")
    except Exception as e:
        print(f"Error training ML model: {e}")
        sys.exit(1)
        
    print("\n======================================================================")
    print("                    INITIALIZATION COMPLETE!                           ")
    print("======================================================================")
    print("Your backend is now ready. You can start the server with:")
    print("  python -m backend.app")
    print("======================================================================")

if __name__ == "__main__":
    init_system(skip_db_errors=True)
