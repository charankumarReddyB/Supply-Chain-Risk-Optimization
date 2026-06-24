-- ============================================================================
-- Supply Chain Risk Optimization - Complete Database Setup
-- OLTP + OLAP (Star Schema) + Indexes + Analytics Views
-- ============================================================================

CREATE DATABASE IF NOT EXISTS supply_chain_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE supply_chain_db;

-- ============================================================================
-- 1. OLTP SCHEMA (Operational Tables)
-- ============================================================================

-- Users Table (JWT Auth)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_username (username),
    INDEX idx_users_email (email)
);

-- ETL Log Table
CREATE TABLE IF NOT EXISTS etl_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL,
    records_processed INT DEFAULT 0,
    records_loaded INT DEFAULT 0,
    duration_seconds DECIMAL(10,2),
    error_message TEXT,
    INDEX idx_etl_logs_status (status),
    INDEX idx_etl_logs_run_at (run_at)
);

-- Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id INT PRIMARY KEY,
    fname VARCHAR(50) NOT NULL,
    lname VARCHAR(50) NOT NULL,
    segment VARCHAR(50),
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    zipcode VARCHAR(20),
    INDEX idx_customers_segment (segment),
    INDEX idx_customers_country (country)
);

-- Products Table
CREATE TABLE IF NOT EXISTS products (
    product_id INT PRIMARY KEY,
    category_id INT,
    category_name VARCHAR(100),
    product_name VARCHAR(150) NOT NULL,
    product_price DECIMAL(10, 2) NOT NULL,
    product_status VARCHAR(50),
    description TEXT,
    INDEX idx_products_category (category_id),
    INDEX idx_products_name (product_name(50))
);

-- Suppliers Table
CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(50),
    rating DECIMAL(3, 2) DEFAULT 5.00,
    status VARCHAR(20) DEFAULT 'Active',
    INDEX idx_suppliers_status (status),
    INDEX idx_suppliers_rating (rating)
);

-- Warehouses Table
CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(50),
    state VARCHAR(50),
    country VARCHAR(50),
    capacity INT,
    manager VARCHAR(100),
    INDEX idx_warehouses_country (country)
);

-- Orders Table
CREATE TABLE IF NOT EXISTS orders (
    order_id INT PRIMARY KEY,
    customer_id INT,
    product_id INT,
    quantity INT DEFAULT 1,
    sales DECIMAL(10, 2) NOT NULL,
    profit DECIMAL(10, 2) NOT NULL,
    order_date DATETIME NOT NULL,
    order_status VARCHAR(50),
    payment_type VARCHAR(50),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE SET NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL,
    INDEX idx_orders_customer (customer_id),
    INDEX idx_orders_product (product_id),
    INDEX idx_orders_date (order_date),
    INDEX idx_orders_status (order_status)
);

-- Shipments Table
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT UNIQUE,
    shipping_date DATETIME NOT NULL,
    shipping_mode VARCHAR(50),
    days_shipping_real INT,
    days_shipment_scheduled INT,
    delivery_status VARCHAR(50),
    late_delivery_risk INT DEFAULT 0,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    INDEX idx_shipments_mode (shipping_mode),
    INDEX idx_shipments_delivery_status (delivery_status),
    INDEX idx_shipments_late_risk (late_delivery_risk)
);

-- Inventory Table
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    warehouse_id INT,
    stock_level INT DEFAULT 0,
    reorder_point INT DEFAULT 50,
    safety_stock INT DEFAULT 10,
    lead_time_days INT DEFAULT 5,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id) ON DELETE CASCADE,
    INDEX idx_inventory_product (product_id),
    INDEX idx_inventory_warehouse (warehouse_id),
    INDEX idx_inventory_stock (stock_level)
);


-- ============================================================================
-- 2. OLAP DATA WAREHOUSE SCHEMA (Star Schema)
-- ============================================================================

-- Dimension Customer
CREATE TABLE IF NOT EXISTS dim_customer (
    Customer_ID INT PRIMARY KEY,
    Customer_Fname VARCHAR(50) NOT NULL,
    Customer_Lname VARCHAR(50) NOT NULL,
    Customer_Segment VARCHAR(50),
    Customer_City VARCHAR(50),
    Customer_State VARCHAR(50),
    Customer_Country VARCHAR(50),
    Customer_Zipcode VARCHAR(20),
    INDEX idx_dim_customer_segment (Customer_Segment)
);

-- Dimension Product
CREATE TABLE IF NOT EXISTS dim_product (
    Product_ID INT PRIMARY KEY,
    Product_Category_Id INT,
    Product_Category_Name VARCHAR(100),
    Product_Name VARCHAR(150) NOT NULL,
    Product_Price DECIMAL(10, 2) NOT NULL,
    Product_Status VARCHAR(50),
    INDEX idx_dim_product_category (Product_Category_Name(50))
);

-- Dimension Supplier
CREATE TABLE IF NOT EXISTS dim_supplier (
    Supplier_ID INT PRIMARY KEY,
    Supplier_Name VARCHAR(100) NOT NULL,
    Supplier_Rating DECIMAL(3, 2),
    Supplier_Status VARCHAR(20),
    INDEX idx_dim_supplier_rating (Supplier_Rating)
);

-- Dimension Warehouse
CREATE TABLE IF NOT EXISTS dim_warehouse (
    Warehouse_ID INT PRIMARY KEY,
    Warehouse_Name VARCHAR(100) NOT NULL,
    Warehouse_City VARCHAR(50),
    Warehouse_State VARCHAR(50),
    Warehouse_Capacity INT
);

-- Dimension Shipping
CREATE TABLE IF NOT EXISTS dim_shipping (
    Shipping_ID INT AUTO_INCREMENT PRIMARY KEY,
    Shipping_Mode VARCHAR(50) NOT NULL,
    Delivery_Status VARCHAR(50) NOT NULL,
    Shipping_Date_Real_Days INT,
    Shipping_Date_Scheduled_Days INT,
    INDEX idx_dim_shipping_mode (Shipping_Mode),
    INDEX idx_dim_shipping_status (Delivery_Status)
);

-- Dimension Date
CREATE TABLE IF NOT EXISTS dim_date (
    Date_ID INT PRIMARY KEY,        -- Formatted as YYYYMMDD
    Full_Date DATE NOT NULL,
    Day INT NOT NULL,
    Month INT NOT NULL,
    Year INT NOT NULL,
    Quarter INT NOT NULL,
    Month_Name VARCHAR(20) NOT NULL,
    Day_Of_Week VARCHAR(20) NOT NULL,
    INDEX idx_dim_date_year_month (Year, Month),
    INDEX idx_dim_date_quarter (Year, Quarter)
);

-- Fact Table: FactOrders (Central OLAP Table)
CREATE TABLE IF NOT EXISTS fact_order (
    Fact_ID INT AUTO_INCREMENT PRIMARY KEY,
    Order_ID INT NOT NULL,
    Customer_ID INT NOT NULL,
    Product_ID INT NOT NULL,
    Supplier_ID INT NOT NULL,
    Warehouse_ID INT NOT NULL,
    Date_ID INT NOT NULL,
    Shipping_ID INT NOT NULL,
    Quantity INT NOT NULL,
    Sales DECIMAL(10, 2) NOT NULL,
    Profit DECIMAL(10, 2) NOT NULL,
    Delivery_Delay INT NOT NULL,
    Risk_Level VARCHAR(10) NOT NULL,
    FOREIGN KEY (Customer_ID) REFERENCES dim_customer(Customer_ID),
    FOREIGN KEY (Product_ID) REFERENCES dim_product(Product_ID),
    FOREIGN KEY (Supplier_ID) REFERENCES dim_supplier(Supplier_ID),
    FOREIGN KEY (Warehouse_ID) REFERENCES dim_warehouse(Warehouse_ID),
    FOREIGN KEY (Date_ID) REFERENCES dim_date(Date_ID),
    FOREIGN KEY (Shipping_ID) REFERENCES dim_shipping(Shipping_ID),
    INDEX idx_fact_order_risk (Risk_Level),
    INDEX idx_fact_order_supplier (Supplier_ID),
    INDEX idx_fact_order_warehouse (Warehouse_ID),
    INDEX idx_fact_order_date (Date_ID),
    INDEX idx_fact_order_customer (Customer_ID),
    INDEX idx_fact_order_product (Product_ID)
);
