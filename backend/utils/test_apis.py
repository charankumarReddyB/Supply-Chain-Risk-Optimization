import sys
import requests
import json
import time

def test_backend_apis():
    # Allow target URL configuration via command line or default to localhost
    target_host = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:5000"
    base_url = f"{target_host}/api"
    
    print("======================================================================")
    print("                     STARTING BACKEND API TESTING                     ")
    print(f"Target Server: {target_host}")
    print("======================================================================")
    
    # 1. Test server online
    print("1. Testing main status endpoint...")
    try:
        res = requests.get(f"{target_host}/")
        print(f"Status: {res.status_code}, Payload: {res.json()}")
    except Exception as e:
        print(f"Failed to connect to backend server: {e}")
        print(f"Please make sure the backend server is running on {target_host}.")
        return

    # 2. Test User Registration
    print("\n2. Testing user registration...")
    reg_payload = {
        "username": f"test_user_{int(time.time())}",
        "email": f"test_{int(time.time())}@example.com",
        "password": "testpassword123",
        "role": "user"
    }
    res_reg = requests.post(f"{base_url}/auth/register", json=reg_payload)
    print(f"Status: {res_reg.status_code}, Payload: {res_reg.json()}")
    
    # 3. Test User Login
    print("\n3. Testing login...")
    login_payload = {
        "username": reg_payload["username"],
        "password": reg_payload["password"]
    }
    res_login = requests.post(f"{base_url}/auth/login", json=login_payload)
    print(f"Status: {res_login.status_code}")
    
    if res_login.status_code != 200:
        print("Login failed, skipping authenticated tests.")
        return
        
    login_data = res_login.json()
    token = login_data["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in successfully. JWT Token acquired.")
    
    # 4. Test Dashboard Stats
    print("\n4. Testing Dashboard Statistics API...")
    res_dash = requests.get(f"{base_url}/dashboard/stats", headers=headers)
    print(f"Status: {res_dash.status_code}")
    if res_dash.status_code == 200:
        dash_data = res_dash.json()
        print(f"KPIs: {dash_data.get('kpis')}")
        print(f"Risk Distribution Size: {len(dash_data.get('risk_distribution', []))}")
        print(f"Revenue Trend Size: {len(dash_data.get('revenue_trend', []))}")
        
    # 5. Test Supplier Performance
    print("\n5. Testing Supplier Performance API...")
    res_supp = requests.get(f"{base_url}/suppliers/performance", headers=headers)
    print(f"Status: {res_supp.status_code}")
    if res_supp.status_code == 200:
        supp_data = res_supp.json()
        print(f"Suppliers returned: {len(supp_data)}")
        if len(supp_data) > 0:
            print(f"Sample Supplier: {supp_data[0]}")
            
    # 6. Test Inventory Replenishment Suggestions
    print("\n6. Testing Inventory Replenishment API...")
    res_inv = requests.get(f"{base_url}/inventory/replenish", headers=headers)
    print(f"Status: {res_inv.status_code}")
    if res_inv.status_code == 200:
        inv_data = res_inv.json()
        print(f"Replenishment Alerts: {len(inv_data)}")
        
    # 7. Test ML Risk Prediction
    print("\n7. Testing ML Risk Prediction API...")
    predict_payload = {
        "days_shipment_scheduled": 3,
        "shipping_mode": "Second Class",
        "customer_segment": "Consumer",
        "category_name": "Men's Footwear",
        "product_price": 120.00,
        "sales": 120.00,
        "discount_rate": 0.05
    }
    res_pred = requests.post(f"{base_url}/risk/predict", json=predict_payload, headers=headers)
    print(f"Status: {res_pred.status_code}, Payload: {res_pred.json()}")
    
    # 8. Test ML Model Info
    print("\n8. Testing ML Model Info API...")
    res_ml = requests.get(f"{base_url}/risk/model-info", headers=headers)
    print(f"Status: {res_ml.status_code}")
    if res_ml.status_code == 200:
        ml_data = res_ml.json()
        print(f"Accuracy: {ml_data.get('accuracy'):.4f}")
        print("Feature Importance:")
        for feat, imp in list(ml_data.get("feature_importance", {}).items())[:3]:
            print(f"  - {feat}: {imp:.4f}")
            
    # 9. Test Optimization Reports
    print("\n9. Testing Optimization APIs...")
    res_opt = requests.get(f"{base_url}/optimization/suppliers", headers=headers)
    print(f"Supplier Recommendations Status: {res_opt.status_code}, Count: {len(res_opt.json()) if res_opt.status_code == 200 else 0}")
    
    # 10. Test Report Generation Download
    print("\n10. Testing PDF and Excel Export APIs...")
    res_pdf = requests.get(f"{base_url}/reports/pdf", headers=headers)
    print(f"PDF download: Status: {res_pdf.status_code}, Content-Type: {res_pdf.headers.get('Content-Type')}")
    
    res_excel = requests.get(f"{base_url}/reports/excel", headers=headers)
    print(f"Excel download: Status: {res_excel.status_code}, Content-Type: {res_excel.headers.get('Content-Type')}")
    
    print("\n======================================================================")
    print("                    API TESTING COMPLETE!                             ")
    print("======================================================================")

if __name__ == "__main__":
    test_backend_apis()
