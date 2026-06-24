import os
import csv
import random
from datetime import datetime, timedelta

def generate_data(num_records=18500):
    print(f"Generating {num_records} mock records for DataCo Smart Supply Chain Dataset...")
    
    # Ensure dataset directory exists
    os.makedirs(os.path.join("backend", "dataset"), exist_ok=True)
    csv_file_path = os.path.join("backend", "dataset", "DataCoSupplyChainDataset.csv")
    
    # Fields matching the original dataset
    headers = [
        "Type", "Days for shipping (real)", "Days for shipment (scheduled)", 
        "Benefit per order", "Sales per customer", "Delivery Status", 
        "Late_delivery_risk", "Category Id", "Category Name", "Customer City", 
        "Customer Country", "Customer Email", "Customer Fname", "Customer Id", 
        "Customer Lname", "Customer Password", "Customer Segment", "Customer State", 
        "Customer Street", "Customer Zipcode", "Department Id", "Department Name", 
        "Latitude", "Longitude", "Market", "Order City", "Order Country", 
        "Order Customer Id", "order date (DateOrders)", "Order Id", 
        "Order Item Cardprod Id", "Order Item Discount", "Order Item Discount Rate", 
        "Order Item Id", "Order Item Product Price", "Order Item Profit Ratio", 
        "Order Item Quantity", "Sales", "Order Item Total", "Order Profit Per Order", 
        "Order Region", "Order State", "Order Status", "Order Zipcode", 
        "Product Card Id", "Product Category Id", "Product Description", 
        "Product Image", "Product Name", "Product Price", "Product Status", 
        "shipping date (DateOrders)", "Shipping Mode"
    ]
    
    # Sample pools for realistic data
    payment_types = ["DEBIT", "TRANSFER", "CASH", "PAYMENT"]
    customer_segments = ["Consumer", "Corporate", "Home Office"]
    shipping_modes = ["Standard Class", "Second Class", "First Class", "Same Day"]
    markets = ["Pacific Asia", "USCA", "Latin America", "Europe", "Africa"]
    
    categories = [
        (1, "Industrial Steel", "Metals"),
        (2, "Electrical Equipment", "Power"),
        (3, "Cement & Construction", "Materials"),
        (4, "Automotive Parts", "Machinery"),
        (5, "Pipes & Fittings", "Hardware"),
        (6, "Industrial Polymers", "Chemicals"),
        (7, "Packaging & Storage", "Logistics"),
        (8, "Textiles & Safety Wear", "Apparel"),
        (9, "Paints & Coatings", "Chemicals"),
        (10, "Control & Automation", "Electronics")
    ]
    
    product_names = {
        1: ["Tata Steel HR Sheets", "JSW NeoSteel Rebars", "Sail Structural Beams"],
        2: ["Havells Switchgear 63A", "Bajaj Distribution Transformer", "Polycab Copper Cables 100m"],
        3: ["UltraTech Premium Cement Bag", "Ambuja Kavach Waterproof Cement", "ACC Gold Cement Bag"],
        4: ["Exide Heavy Duty Battery 12V", "Bosch India Disc Brake Pads", "Mahindra Tractor Alternators"],
        5: ["Supreme PVC Pressure Pipes", "Astral CPVC Pipe Fittings", "Prince SWR Pipes 3m"],
        6: ["Reliance PVC Resin Granules", "Haldia Polyethylene Pellets", "Pidilite Fevicol SH 5kg"],
        7: ["Wimplast Heavy Storage Crates", "Nilkamal Plastic Pallets", "Hindustan Tin Containers"],
        8: ["Raymond Safety Jackets", "Arvind Protective Hand Gloves", "Siyarams Industrial Overalls"],
        9: ["Asian Paints Apcolite Primer", "Berger Industrial Epoxy Paint", "Nerolac Rust Protector 20L"],
        10: ["L&T Control Panel Board", "Schneider India Digital Meters", "Siemens AC Drive 5HP"]
    }
    
    cities = [
        ("Mumbai", "MH", "India"), ("Delhi", "DL", "India"), ("Bengaluru", "KA", "India"),
        ("Kolkata", "WB", "India"), ("Chennai", "TN", "India"), ("Hyderabad", "TG", "India"),
        ("Pune", "MH", "India"), ("Ahmedabad", "GJ", "India"), ("Jaipur", "RJ", "India"),
        ("Lucknow", "UP", "India")
    ]
    
    order_cities = [
        ("Mumbai", "India", "West"), ("Delhi", "India", "North"),
        ("Bengaluru", "India", "South"), ("Kolkata", "India", "East"),
        ("Chennai", "India", "South"), ("Hyderabad", "India", "South"),
        ("Pune", "India", "West"), ("Ahmedabad", "India", "West"),
        ("Jaipur", "India", "North"), ("Lucknow", "India", "North")
    ]
    
    order_statuses = ["COMPLETE", "PROCESSING", "PENDING", "PENDING_PAYMENT", "CLOSED", "CANCELED", "ON_HOLD"]
    
    # Pre-generate lists to map consistently
    first_names = ["Rajesh", "Amit", "Sanjay", "Anil", "Sunil", "Dinesh", "Suresh", "Vijay", "Ramesh", "Deepak",
                   "Priya", "Sunita", "Anita", "Ritu", "Neha", "Pooja", "Asha", "Kiran", "Meena", "Jyoti"]
    last_names = ["Kumar", "Sharma", "Singh", "Patel", "Gupta", "Rao", "Reddy", "Joshi", "Das", "Mehta",
                  "Gupta", "Sen", "Nair", "Verma", "Prasad", "Mishra", "Pandey", "Choudhury", "Bose", "Menon"]

    customers = []
    for c_id in range(1, 1001):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        email = f"{fname.lower()}.{lname.lower()}_{c_id}@example.com"
        segment = random.choice(customer_segments)
        city, state, country = random.choice(cities)
        zipcode = f"{random.randint(110001, 850000)}"
        customers.append({
            "id": c_id, "fname": fname, "lname": lname, "email": email,
            "segment": segment, "city": city, "state": state, "country": country, "zipcode": zipcode
        })
        
    start_date = datetime(2015, 1, 1)
    
    # Write to CSV
    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        order_counter = 100000
        order_item_counter = 500000
        
        for i in range(num_records):
            customer = random.choice(customers)
            cat_id, cat_name, dept_name = random.choice(categories)
            prod_name = random.choice(product_names[cat_id])
            prod_price = round(random.uniform(3000.0, 150000.0), 2)
            
            qty = random.randint(1, 5)
            sales = round(prod_price * qty, 2)
            discount_rate = random.choice([0.0, 0.05, 0.1, 0.15, 0.2])
            discount = round(sales * discount_rate, 2)
            item_total = round(sales - discount, 2)
            
            # Profit can be positive or negative
            profit_ratio = random.uniform(-0.3, 0.4)
            profit = round(item_total * profit_ratio, 2)
            
            # Dates
            days_offset = random.randint(0, 1000)
            ord_date = start_date + timedelta(days=days_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
            # Shipping Modes and Days
            ship_mode = random.choice(shipping_modes)
            if ship_mode == "Same Day":
                sched_days = 0
                real_days = random.choice([0, 0, 0, 1])
            elif ship_mode == "First Class":
                sched_days = 1
                real_days = random.choice([1, 1, 2, 3])
            elif ship_mode == "Second Class":
                sched_days = 3
                real_days = random.choice([2, 3, 3, 4, 5])
            else: # Standard Class
                sched_days = 4
                real_days = random.choice([3, 4, 4, 5, 6, 7])
                
            shipping_date = ord_date + timedelta(days=real_days)
            
            # Status and Risk
            late = real_days > sched_days
            risk = 1 if late else 0
            
            if risk == 1:
                delivery_status = "Late delivery"
                status = random.choice(["PROCESSING", "PENDING", "ON_HOLD", "COMPLETE"])
            else:
                delivery_status = random.choice(["Shipping on time", "Advance shipping"])
                status = random.choice(["COMPLETE", "CLOSED"])
                
            # Random override for canceled orders
            if random.random() < 0.03:
                delivery_status = "Shipping canceled"
                status = "CANCELED"
                risk = 0
            
            order_city, order_country, market = random.choice(order_cities)
            
            row = [
                random.choice(payment_types),       # Type
                real_days,                          # Days for shipping (real)
                sched_days,                         # Days for shipment (scheduled)
                profit,                             # Benefit per order (Profit)
                item_total,                         # Sales per customer (Item Total after discount)
                delivery_status,                    # Delivery Status
                risk,                               # Late_delivery_risk
                cat_id,                             # Category Id
                cat_name,                           # Category Name
                customer["city"],                   # Customer City
                customer["country"],                # Customer Country
                customer["email"],                  # Customer Email
                customer["fname"],                  # Customer Fname
                customer["id"],                     # Customer Id
                customer["lname"],                  # Customer Lname
                "password123",                      # Customer Password
                customer["segment"],                # Customer Segment
                customer["state"],                  # Customer State
                "123 Main St",                      # Customer Street
                customer["zipcode"],                # Customer Zipcode
                cat_id + 10,                        # Department Id
                dept_name,                          # Department Name
                round(random.uniform(18.0, 45.0), 4), # Latitude
                round(random.uniform(-120.0, -65.0), 4), # Longitude
                market,                             # Market
                order_city,                         # Order City
                order_country,                      # Order Country
                customer["id"],                     # Order Customer Id
                ord_date.strftime("%m/%d/%Y %H:%M"), # order date (DateOrders)
                order_counter,                      # Order Id
                cat_id * 100 + 1,                   # Order Item Cardprod Id
                discount,                           # Order Item Discount
                discount_rate,                      # Order Item Discount Rate
                order_item_counter,                 # Order Item Id
                prod_price,                         # Order Item Product Price
                round(profit_ratio, 2),             # Order Item Profit Ratio
                qty,                                # Order Item Quantity
                sales,                              # Sales (Gross Sales)
                item_total,                         # Order Item Total (Net Sales)
                profit,                             # Order Profit Per Order
                market,                             # Order Region
                customer["state"],                  # Order State
                status,                             # Order Status
                "12345",                            # Order Zipcode
                cat_id * 100 + 1,                   # Product Card Id
                cat_id,                             # Product Category Id
                "Product Description Text",         # Product Description
                "http://images.example.com/p.jpg",  # Product Image
                prod_name,                          # Product Name
                prod_price,                         # Product Price
                0,                                  # Product Status
                shipping_date.strftime("%m/%d/%Y %H:%M"), # shipping date (DateOrders)
                ship_mode                           # Shipping Mode
            ]
            
            writer.writerow(row)
            
            # Increment order counter occasionally to group multiple items in same order
            if random.random() > 0.3:
                order_counter += 1
            order_item_counter += 1
            
    print(f"Dataset generated successfully at: {csv_file_path}")

if __name__ == "__main__":
    generate_data()
