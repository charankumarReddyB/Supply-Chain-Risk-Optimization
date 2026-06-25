import os
import random
import pandas as pd
import numpy as np
from datetime import datetime
from backend.config import Config
from backend.models.database import get_db_connection, run_sql_file

def run_etl_pipeline():
    print("Starting ETL pipeline...")
    
    # 1. Setup Database Tables if they don't exist
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sql_setup_path = os.path.abspath(os.path.join(current_dir, "..", "database_setup.sql"))
    print(f"Running database setup from {sql_setup_path}...")
    run_sql_file(sql_setup_path)
    
    # 2. Read Dataset CSV
    csv_path = Config.DATASET_PATH
    if not os.path.exists(csv_path):
        print(f"Dataset not found at {csv_path}. Running generator first...")
        from backend.etl.generate_mock_data import generate_data
        generate_data(18500)
        
    print(f"Reading dataset from {csv_path}...")
    df = pd.read_csv(csv_path, encoding='utf-8')
    
    print(f"Loaded {len(df)} records. Starting data cleaning...")
    
    # 3. Clean Missing Values & Remove Duplicates
    # Drop rows without critical keys
    df = df.dropna(subset=["Order Id", "Customer Id", "Product Card Id"])
    
    # Fill remaining missing text values
    df["Customer Zipcode"] = df["Customer Zipcode"].fillna("00000").astype(str)
    df["Customer Lname"] = df["Customer Lname"].fillna("")
    df["Product Description"] = df["Product Description"].fillna("No description available")
    
    # Remove duplicates
    initial_len = len(df)
    df = df.drop_duplicates(subset=["Order Item Id"])
    print(f"Removed {initial_len - len(df)} duplicate items.")
    
    # 4. Data Type Conversion & Parsing
    # Dates
    df["order_date_parsed"] = pd.to_datetime(df["order date (DateOrders)"], format="%m/%d/%Y %H:%M")
    df["shipping_date_parsed"] = pd.to_datetime(df["shipping date (DateOrders)"], format="%m/%d/%Y %H:%M")
    
    # Integers and Floats
    df["Order Id"] = df["Order Id"].astype(int)
    df["Customer Id"] = df["Customer Id"].astype(int)
    df["Product Card Id"] = df["Product Card Id"].astype(int)
    df["Days for shipping (real)"] = df["Days for shipping (real)"].astype(int)
    df["Days for shipment (scheduled)"] = df["Days for shipment (scheduled)"].astype(int)
    df["Order Item Quantity"] = df["Order Item Quantity"].astype(int)
    df["Sales"] = df["Sales"].astype(float)
    df["Benefit per order"] = df["Benefit per order"].astype(float)
    
    # 5. Create Derived Columns
    # Delivery_Delay = Days shipping real - Days shipping scheduled
    df["Delivery_Delay"] = df["Days for shipping (real)"] - df["Days for shipment (scheduled)"]
    
    # Risk Level classification
    def calculate_risk(row):
        delay = row["Delivery_Delay"]
        profit = row["Benefit per order"]
        if delay > 0 and profit < 0:
            return "High"
        elif delay > 0 or profit < 0:
            return "Medium"
        else:
            return "Low"
            
    df["Risk_Level"] = df.apply(calculate_risk, axis=1)
    
    # Assign deterministic Supplier and Warehouse based on Product Id to ensure integrity
    df["Supplier_ID"] = (df["Product Card Id"] % 5) + 1
    df["Warehouse_ID"] = (df["Product Card Id"] % 3) + 1
    
    print("ETL Transformation complete. Loading data into MySQL...")
    
    # Connect to MySQL
    conn = get_db_connection()
    try:
        # Clear existing data recursively to prevent primary key duplicates when re-running
        with conn.cursor() as cursor:
            tables = ["fact_order", "dim_customer", "dim_product", "dim_supplier", "dim_warehouse", 
                      "dim_shipping", "dim_date", "inventory", "shipments", "orders", "warehouses", 
                      "suppliers", "products", "customers"]
            tables_str = ", ".join(tables)
            cursor.execute(f"TRUNCATE TABLE {tables_str} CASCADE;")
            conn.commit()
            
        print("Truncated operational and warehouse tables. Loading dimensions and reference data...")
        
        # Load Reference Data
        # Suppliers
        suppliers_data = [
            (1, "Bharat Metals & Logistics", "info@bharatmetals.in", "+91-98765-43210", 4.8, "Active"),
            (2, "Krishna Industrial Manufacturing", "sales@krishnamfg.in", "+91-98765-43211", 3.2, "Active"),
            (3, "Vanguard Synergy Freight Corp", "support@vanguardsynergy.in", "+91-98765-43212", 4.5, "Active"),
            (4, "Apex Industrial Alloys & Materials", "orders@apexalloys.in", "+91-98765-43213", 2.9, "Active"),
            (5, "Aetherius Distribution Networks", "logistics@aetheriusdist.in", "+91-98765-43214", 4.1, "Active")
        ]
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO suppliers (supplier_id, name, email, phone, rating, status) VALUES (%s, %s, %s, %s, %s, %s)",
                suppliers_data
            )
            cursor.executemany(
                "INSERT INTO dim_supplier (Supplier_ID, Supplier_Name, Supplier_Rating, Supplier_Status) VALUES (%s, %s, %s, %s)",
                [(s[0], s[1], s[4], s[5]) for s in suppliers_data]
            )
            
        # Warehouses
        warehouses_data = [
            (1, "West India Fulfillment Hub", "Mumbai", "MH", "India", 50000, "Rajesh Sharma"),
            (2, "North India Logistics Hub", "Delhi", "DL", "India", 75000, "Amit Patel"),
            (3, "South India Logistics Hub", "Chennai", "TN", "India", 60000, "Karthik Srinivasan")
        ]
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO warehouses (warehouse_id, name, city, state, country, capacity, manager) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                warehouses_data
            )
            cursor.executemany(
                "INSERT INTO dim_warehouse (Warehouse_ID, Warehouse_Name, Warehouse_City, Warehouse_State, Warehouse_Capacity) VALUES (%s, %s, %s, %s, %s)",
                [(w[0], w[1], w[2], w[3], w[5]) for w in warehouses_data]
            )
        conn.commit()

        # Load Customers
        print("Loading Customers...")
        cust_df = df[[
            "Customer Id", "Customer Fname", "Customer Lname", "Customer Segment", 
            "Customer City", "Customer State", "Customer Country", "Customer Zipcode"
        ]].drop_duplicates(subset=["Customer Id"])
        
        with conn.cursor() as cursor:
            # OLTP
            cursor.executemany(
                """INSERT INTO customers (customer_id, fname, lname, segment, city, state, country, zipcode) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                cust_df.values.tolist()
            )
            # OLAP Dim
            cursor.executemany(
                """INSERT INTO dim_customer (Customer_ID, Customer_Fname, Customer_Lname, Customer_Segment, Customer_City, Customer_State, Customer_Country, Customer_Zipcode) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                cust_df.values.tolist()
            )
        conn.commit()
        
        # Load Products
        print("Loading Products...")
        prod_df = df[[
            "Product Card Id", "Category Id", "Category Name", "Product Name", 
            "Product Price", "Product Status", "Product Description"
        ]].drop_duplicates(subset=["Product Card Id"])
        
        with conn.cursor() as cursor:
            # OLTP
            cursor.executemany(
                """INSERT INTO products (product_id, category_id, category_name, product_name, product_price, product_status, description) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                prod_df.values.tolist()
            )
            # OLAP Dim
            cursor.executemany(
                """INSERT INTO dim_product (Product_ID, Product_Category_Id, Product_Category_Name, Product_Name, Product_Price, Product_Status) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                prod_df[[
                    "Product Card Id", "Category Id", "Category Name", "Product Name", 
                    "Product Price", "Product Status"
                ]].values.tolist()
            )
        conn.commit()

        # Load Orders and Shipments (OLTP)
        print("Loading Orders & Shipments...")
        orders_df = df[[
            "Order Id", "Customer Id", "Product Card Id", "Order Item Quantity", 
            "Sales", "Benefit per order", "order_date_parsed", "Order Status", "Type"
        ]].copy()
        orders_df["order_date_parsed"] = orders_df["order_date_parsed"].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        shipments_df = df[[
            "Order Id", "shipping_date_parsed", "Shipping Mode", 
            "Days for shipping (real)", "Days for shipment (scheduled)", 
            "Delivery Status", "Late_delivery_risk"
        ]].copy()
        shipments_df = shipments_df.drop_duplicates(subset=["Order Id"])
        shipments_df["shipping_date_parsed"] = shipments_df["shipping_date_parsed"].dt.strftime("%Y-%m-%d %H:%M:%S")
        
        with conn.cursor() as cursor:
            # Load Orders in OLTP
            cursor.executemany(
                """INSERT INTO orders (order_id, customer_id, product_id, quantity, sales, profit, order_date, order_status, payment_type) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) 
                   ON CONFLICT (order_id) DO UPDATE SET sales=orders.sales+EXCLUDED.sales, profit=orders.profit+EXCLUDED.profit, quantity=orders.quantity+EXCLUDED.quantity""",
                orders_df.values.tolist()
            )
            # Load Shipments in OLTP
            cursor.executemany(
                """INSERT INTO shipments (order_id, shipping_date, shipping_mode, days_shipping_real, days_shipment_scheduled, delivery_status, late_delivery_risk) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                shipments_df.values.tolist()
            )
        conn.commit()

        # Load Inventory (OLTP)
        print("Loading Inventory...")
        inventory_records = []
        for index, row in prod_df.iterrows():
            prod_id = int(row["Product Card Id"])
            # Map product to its designated warehouse
            wh_id = (prod_id % 3) + 1
            # Random starting inventory levels
            stock = random.randint(100, 1000)
            reorder = random.choice([50, 100, 150, 200])
            safety = random.choice([10, 20, 30, 40])
            lead_time = random.choice([3, 5, 7, 10])
            inventory_records.append((prod_id, wh_id, stock, reorder, safety, lead_time))
            
        with conn.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO inventory (product_id, warehouse_id, stock_level, reorder_point, safety_stock, lead_time_days) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                inventory_records
            )
        conn.commit()

        # Load Dim Shipping (OLAP)
        print("Loading Dim Shipping...")
        shipping_combos = df[[
            "Shipping Mode", "Delivery Status", "Days for shipping (real)", "Days for shipment (scheduled)"
        ]].drop_duplicates()
        
        with conn.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO dim_shipping (Shipping_Mode, Delivery_Status, Shipping_Date_Real_Days, Shipping_Date_Scheduled_Days) 
                   VALUES (%s, %s, %s, %s)""",
                shipping_combos.values.tolist()
            )
        conn.commit()

        # Fetch dim_shipping keys to map them in fact_order
        with conn.cursor() as cursor:
            cursor.execute("SELECT Shipping_ID, Shipping_Mode, Delivery_Status, Shipping_Date_Real_Days, Shipping_Date_Scheduled_Days FROM dim_shipping")
            shipping_mapping = cursor.fetchall()
            
        shipping_dict = {
            (r["Shipping_Mode"], r["Delivery_Status"], r["Shipping_Date_Real_Days"], r["Shipping_Date_Scheduled_Days"]): r["Shipping_ID"]
            for r in shipping_mapping
        }

        # Load Dim Date (OLAP)
        print("Loading Dim Date...")
        dates_series = df["order_date_parsed"].drop_duplicates()
        date_records = []
        for dt in dates_series:
            date_id = int(dt.strftime("%Y%m%d"))
            full_date = dt.date().strftime("%Y-%m-%d")
            day = dt.day
            month = dt.month
            year = dt.year
            quarter = (month - 1) // 3 + 1
            month_name = dt.strftime("%B")
            day_of_week = dt.strftime("%A")
            date_records.append((date_id, full_date, day, month, year, quarter, month_name, day_of_week))
            
        # Deduplicate date_records by date_id
        date_records_df = pd.DataFrame(date_records, columns=["Date_ID", "Full_Date", "Day", "Month", "Year", "Quarter", "Month_Name", "Day_Of_Week"])
        date_records_df = date_records_df.drop_duplicates(subset=["Date_ID"])
        
        with conn.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO dim_date (Date_ID, Full_Date, Day, Month, Year, Quarter, Month_Name, Day_Of_Week) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                date_records_df.values.tolist()
            )
        conn.commit()

        # Load Fact Order (OLAP)
        print("Loading Fact Order Table...")
        fact_records = []
        for index, row in df.iterrows():
            order_id = int(row["Order Id"])
            customer_id = int(row["Customer Id"])
            product_id = int(row["Product Card Id"])
            supplier_id = int(row["Supplier_ID"])
            warehouse_id = int(row["Warehouse_ID"])
            date_id = int(row["order_date_parsed"].strftime("%Y%m%d"))
            
            # Retrieve shipping id from dictionary
            ship_key = (
                row["Shipping Mode"], 
                row["Delivery Status"], 
                int(row["Days for shipping (real)"]), 
                int(row["Days for shipment (scheduled)"])
            )
            shipping_id = shipping_dict.get(ship_key)
            
            qty = int(row["Order Item Quantity"])
            sales = float(row["Sales"])
            profit = float(row["Benefit per order"])
            delivery_delay = int(row["Delivery_Delay"])
            risk_level = row["Risk_Level"]
            
            fact_records.append((
                order_id, customer_id, product_id, supplier_id, warehouse_id, 
                date_id, shipping_id, qty, sales, profit, delivery_delay, risk_level
            ))
            
        with conn.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO fact_order (Order_ID, Customer_ID, Product_ID, Supplier_ID, Warehouse_ID, Date_ID, Shipping_ID, Quantity, Sales, Profit, Delivery_Delay, Risk_Level) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                fact_records
            )
            
        conn.commit()
        
        print("ETL load finished successfully!")
        
    except Exception as e:
        print(f"Error during ETL loading: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    run_etl_pipeline()
