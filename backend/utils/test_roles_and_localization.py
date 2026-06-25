import requests
import sys

def test_roles_and_localization():
    # Allow target URL configuration via command line or default to localhost
    target_host = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:5000"
    base_url = f"{target_host}/api"
    
    print("======================================================================")
    print("        STARTING SECURITY AND CONTEXT LOCALIZATION TESTS              ")
    print(f"Target Server: {target_host}")
    print("======================================================================")

    # 1. Login as Admin
    print("\n1. Testing Login as Admin (admin/admin123)...")
    res_login_admin = requests.post(f"{base_url}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    print(f"Status: {res_login_admin.status_code}")
    if res_login_admin.status_code != 200:
        print("FAIL: Admin login failed. Make sure DB is seeded and backend is running.")
        sys.exit(1)
        
    admin_data = res_login_admin.json()
    admin_token = admin_data["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Login as User
    print("\n2. Testing Login as User (user/user123)...")
    res_login_user = requests.post(f"{base_url}/auth/login", json={
        "username": "user",
        "password": "user123"
    })
    print(f"Status: {res_login_user.status_code}")
    if res_login_user.status_code != 200:
        print("FAIL: User login failed.")
        sys.exit(1)
        
    user_data = res_login_user.json()
    user_token = user_data["token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 3. Verify unauthenticated request to monte-carlo graph is rejected
    print("\n3. Testing unauthenticated request to /api/monte-carlo/graph/delivery_delay.png...")
    res_graph_no_auth = requests.get(f"{base_url}/monte-carlo/graph/delivery_delay.png")
    print(f"Status: {res_graph_no_auth.status_code}")
    if res_graph_no_auth.status_code not in [401, 403]:
        print(f"FAIL: Unauthenticated access was allowed to graph. Status: {res_graph_no_auth.status_code}")
        sys.exit(1)
    else:
        print("SUCCESS: Unauthenticated access rejected.")

    # 4. Verify user-role access restrictions (403 and error message detail check)
    print("\n4. Testing access restrictions for the standard 'user' role...")
    restricted_endpoints = [
        ("GET", "suppliers/performance"),
        ("GET", "products/high-risk"),
        ("GET", "warehouses/olap/summary"),
        ("GET", "etl/status"),
        ("GET", "etl/logs"),
        ("GET", "risk/summary"),
        ("GET", "risk/suppliers"),
        ("GET", "risk/delivery-delays"),
        ("GET", "risk/shipping-performance"),
        ("GET", "risk/warehouse-performance"),
        ("POST", "risk/predict"),
        ("GET", "risk/model-info"),
        ("GET", "monte-carlo/results"),
        ("GET", "monte-carlo/graph/delivery_delay.png"),
        ("GET", "cost/by-category"),
        ("GET", "cost/by-region"),
        ("GET", "optimization/suppliers"),
        ("GET", "reports/pdf"),
    ]

    for method, path in restricted_endpoints:
        url = f"{base_url}/{path}"
        if method == "GET":
            res = requests.get(url, headers=user_headers)
        elif method == "POST":
            res = requests.post(url, json={}, headers=user_headers)
            
        print(f"  - {method} /api/{path}: Status={res.status_code}")
        if res.status_code != 403:
            print(f"FAIL: {method} /api/{path} did not return 403. Status: {res.status_code}")
            sys.exit(1)
        
        detail = res.json().get("detail")
        if detail != "This data is restricted to admin accounts.":
            print(f"FAIL: Expected restricted detail message. Got: {detail}")
            sys.exit(1)

    print("SUCCESS: User access restrictions verified.")

    # 5. Verify field-level trimming for suppliers
    print("\n5. Testing field-level trimming on GET /api/suppliers...")
    
    # User Request
    res_supp_user = requests.get(f"{base_url}/suppliers", headers=user_headers)
    if res_supp_user.status_code != 200:
        print(f"FAIL: User cannot read suppliers: {res_supp_user.status_code}")
        sys.exit(1)
    supp_user_list = res_supp_user.json()
    if len(supp_user_list) > 0:
        sample = supp_user_list[0]
        print(f"  - User Supplier Sample keys: {list(sample.keys())}")
        restricted_supplier_fields = ["reliability_score", "avg_delay_days", "on_time_rate", "total_sales", "total_revenue", "total_profit", "composite_score"]
        for f in restricted_supplier_fields:
            if f in sample:
                print(f"FAIL: Restricted field '{f}' is present in user's supplier listing.")
                sys.exit(1)
        print("  - SUCCESS: Restricted supplier fields are absent for User role.")

    # Admin Request
    res_supp_admin = requests.get(f"{base_url}/suppliers", headers=admin_headers)
    if res_supp_admin.status_code != 200:
        print(f"FAIL: Admin cannot read suppliers: {res_supp_admin.status_code}")
        sys.exit(1)
    supp_admin_list = res_supp_admin.json()
    
    # 6. Verify field-level trimming for orders
    print("\n6. Testing field-level trimming on GET /api/orders...")
    res_orders_user = requests.get(f"{base_url}/orders", headers=user_headers)
    if res_orders_user.status_code != 200:
        print(f"FAIL: User cannot read orders: {res_orders_user.status_code}")
        sys.exit(1)
    orders_user_list = res_orders_user.json()
    if len(orders_user_list) > 0:
        sample = orders_user_list[0]
        print(f"  - User Order Sample keys: {list(sample.keys())}")
        restricted_order_fields = ["unit_price", "total_cost", "transportation_cost"]
        for f in restricted_order_fields:
            if f in sample:
                print(f"FAIL: Restricted field '{f}' is present in user's order listing.")
                sys.exit(1)
        print("  - SUCCESS: Restricted order fields are absent for User role.")

    # Admin Request
    res_orders_admin = requests.get(f"{base_url}/orders", headers=admin_headers)
    if res_orders_admin.status_code != 200:
        print(f"FAIL: Admin cannot read orders: {res_orders_admin.status_code}")
        sys.exit(1)
    orders_admin_list = res_orders_admin.json()
    if len(orders_admin_list) > 0:
        sample_admin = orders_admin_list[0]
        print(f"  - Admin Order Sample keys: {list(sample_admin.keys())}")
        # sales or profit should be present
        if "sales" not in sample_admin:
            print("FAIL: 'sales' missing from admin's order response.")
            sys.exit(1)
        print("  - SUCCESS: Admin retains full fields.")

    # 7. Testing Cost endpoints for Admin
    print("\n7. Testing new cost endpoints for Admin...")
    res_cost_cat = requests.get(f"{base_url}/cost/by-category", headers=admin_headers)
    print(f"  - GET /api/cost/by-category: Status={res_cost_cat.status_code}")
    if res_cost_cat.status_code != 200:
        print(f"FAIL: Admin cannot fetch cost-by-category: {res_cost_cat.status_code}")
        sys.exit(1)
    print(f"    Sample Category Cost: {res_cost_cat.json()[0] if len(res_cost_cat.json()) > 0 else 'None'}")

    res_cost_reg = requests.get(f"{base_url}/cost/by-region", headers=admin_headers)
    print(f"  - GET /api/cost/by-region: Status={res_cost_reg.status_code}")
    if res_cost_reg.status_code != 200:
        print(f"FAIL: Admin cannot fetch cost-by-region: {res_cost_reg.status_code}")
        sys.exit(1)
    print(f"    Sample Region Cost: {res_cost_reg.json()[0] if len(res_cost_reg.json()) > 0 else 'None'}")

    # 8. Testing profile updating endpoints
    print("\n8. Testing user profile updates...")
    res_update_profile = requests.put(f"{base_url}/auth/profile", headers=admin_headers, json={
        "email": "admin_new@supplychain.com",
        "full_name": "Administrator Charan",
        "phone": "+91 99999 88888",
        "location": "Mumbai, India",
        "department": "IT Operations",
        "employee_id": "EMP-ADMIN-001"
    })
    print(f"  - PUT /api/auth/profile: Status={res_update_profile.status_code}")
    if res_update_profile.status_code != 200:
        print(f"FAIL: Admin profile update failed: {res_update_profile.status_code}")
        sys.exit(1)

    profile_data = res_update_profile.json()["user"]
    if profile_data.get("full_name") != "Administrator Charan" or profile_data.get("phone") != "+91 99999 88888":
        print("FAIL: Profile updates did not return expected values.")
        sys.exit(1)

    res_me = requests.get(f"{base_url}/auth/me", headers=admin_headers)
    print(f"  - GET /api/auth/me: Status={res_me.status_code}")
    if res_me.status_code != 200:
        print(f"FAIL: GET /api/auth/me failed: {res_me.status_code}")
        sys.exit(1)

    me_data = res_me.json()["user"]
    if me_data.get("full_name") != "Administrator Charan":
        print("FAIL: GET /api/auth/me did not contain updated profile fields.")
        sys.exit(1)
    print("  - SUCCESS: User profile update and persistence verified.")

    print("\n======================================================================")
    print("             ALL SECURITY, RBAC & TRIMMING TESTS PASSED!              ")
    print("======================================================================")

if __name__ == "__main__":
    test_roles_and_localization()
