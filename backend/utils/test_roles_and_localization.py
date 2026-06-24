import requests
import sys

def test_roles_and_localization():
    base_url = "http://localhost:5000/api"
    print("======================================================================")
    print("        STARTING SECURITY AND CONTEXT LOCALIZATION TESTS              ")
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
    admin_user = admin_data["user"]
    print(f"Admin User Info: {admin_user}")
    if admin_user.get("role") != "admin":
        print("FAIL: Admin user role is not 'admin' in login response.")
        sys.exit(1)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Test GET /api/auth/me for Admin
    print("\n2. Testing /api/auth/me for Admin...")
    res_me_admin = requests.get(f"{base_url}/auth/me", headers=admin_headers)
    print(f"Status: {res_me_admin.status_code}")
    if res_me_admin.status_code != 200:
        print("FAIL: /api/auth/me failed for admin.")
        sys.exit(1)
    me_admin_data = res_me_admin.json()
    print(f"Me Admin Response: {me_admin_data}")
    if me_admin_data.get("role") != "admin" or me_admin_data.get("username") != "admin":
        print("FAIL: role or username not present at the root of /me response.")
        sys.exit(1)

    # 3. Login as User
    print("\n3. Testing Login as User (user/user123)...")
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
    user_user = user_data["user"]
    print(f"User Info: {user_user}")
    if user_user.get("role") != "user":
        print("FAIL: User role is not 'user' in login response.")
        sys.exit(1)

    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 4. Test GET /api/auth/me for User
    print("\n4. Testing /api/auth/me for User...")
    res_me_user = requests.get(f"{base_url}/auth/me", headers=user_headers)
    print(f"Status: {res_me_user.status_code}")
    if res_me_user.status_code != 200:
        print("FAIL: /api/auth/me failed for user.")
        sys.exit(1)
    me_user_data = res_me_user.json()
    print(f"Me User Response: {me_user_data}")
    if me_user_data.get("role") != "user" or me_user_data.get("username") != "user":
        print("FAIL: role or username not present at root of /me response for user.")
        sys.exit(1)

    # 5. Test read endpoints for both roles and check for currency: INR
    print("\n5. Testing Read Endpoints & Currency Verification...")
    endpoints = ["products", "suppliers", "orders"]
    for ep in endpoints:
        print(f"  - Testing GET /api/{ep} with user token...")
        res_read_user = requests.get(f"{base_url}/{ep}", headers=user_headers)
        print(f"    User GET Status: {res_read_user.status_code}")
        if res_read_user.status_code != 200:
            print(f"FAIL: user role cannot read /api/{ep}")
            sys.exit(1)
            
        data = res_read_user.json()
        if len(data) > 0:
            sample = data[0]
            print(f"    Sample Item keys: {list(sample.keys())}")
            if sample.get("currency") != "INR":
                print(f"FAIL: currency key not found or not 'INR' in sample item for /api/{ep}")
                sys.exit(1)
            else:
                print(f"    SUCCESS: currency key is 'INR'")
        else:
            print(f"    Warning: No records found for /api/{ep} to check currency")

        # Verify admin can read too
        res_read_admin = requests.get(f"{base_url}/{ep}", headers=admin_headers)
        if res_read_admin.status_code != 200:
            print(f"FAIL: admin role cannot read /api/{ep}")
            sys.exit(1)

    # 6. Test Dashboard endpoints and check for currency: INR
    print("\n6. Testing Dashboard Stats and KPIs Currency Verification...")
    res_dash = requests.get(f"{base_url}/dashboard/stats", headers=user_headers)
    if res_dash.status_code != 200:
        print("FAIL: Cannot get /api/dashboard/stats")
        sys.exit(1)
    dash_data = res_dash.json()
    if dash_data.get("currency") != "INR":
        print("FAIL: /api/dashboard/stats does not contain currency: INR")
        sys.exit(1)
    print("  - Stats currency check: SUCCESS")

    res_kpi = requests.get(f"{base_url}/dashboard/kpis", headers=user_headers)
    if res_kpi.status_code != 200:
        print("FAIL: Cannot get /api/dashboard/kpis")
        sys.exit(1)
    kpi_data = res_kpi.json()
    if kpi_data.get("currency") != "INR":
        print("FAIL: /api/dashboard/kpis does not contain currency: INR")
        sys.exit(1)
    print("  - KPIs currency check: SUCCESS")

    # 7. Verify role restriction (403 Forbidden) for User on write endpoints
    print("\n7. Testing Write Operations Restrict on User Role...")
    
    # Try adding a product
    prod_payload = {
        "product_id": 99999,
        "product_name": "Test Security Product",
        "product_price": 5000.0,
        "category_name": "Testing"
    }
    res_add_prod_user = requests.post(f"{base_url}/products", json=prod_payload, headers=user_headers)
    print(f"  - POST /api/products with User JWT: Status={res_add_prod_user.status_code}, Payload={res_add_prod_user.json()}")
    if res_add_prod_user.status_code != 403:
        print(f"FAIL: User role was allowed to write /api/products or did not return 403. Status: {res_add_prod_user.status_code}")
        sys.exit(1)

    # Try modifying an inventory item
    res_put_inv_user = requests.put(f"{base_url}/inventory/1", json={"stock_level": 500}, headers=user_headers)
    print(f"  - PUT /api/inventory/1 with User JWT: Status={res_put_inv_user.status_code}, Payload={res_put_inv_user.json()}")
    if res_put_inv_user.status_code != 403:
        print(f"FAIL: User role was allowed to write /api/inventory/1 or did not return 403. Status: {res_put_inv_user.status_code}")
        sys.exit(1)

    # Try running ETL
    res_run_etl_user = requests.post(f"{base_url}/etl/run", headers=user_headers)
    print(f"  - POST /api/etl/run with User JWT: Status={res_run_etl_user.status_code}, Payload={res_run_etl_user.json()}")
    if res_run_etl_user.status_code != 403:
        print(f"FAIL: User role was allowed to POST /api/etl/run or did not return 403. Status: {res_run_etl_user.status_code}")
        sys.exit(1)

    # 8. Verify admin can write successfully
    print("\n8. Testing Write Operations Allow on Admin Role...")
    # Add product as Admin
    res_add_prod_admin = requests.post(f"{base_url}/products", json=prod_payload, headers=admin_headers)
    print(f"  - POST /api/products with Admin JWT: Status={res_add_prod_admin.status_code}")
    if res_add_prod_admin.status_code not in [201, 409]:  # 201 Created, or 409 Conflict if already exists
        print(f"FAIL: Admin cannot write products. Status: {res_add_prod_admin.status_code}, Payload: {res_add_prod_admin.json()}")
        sys.exit(1)

    # Delete product as Admin
    res_del_prod_admin = requests.delete(f"{base_url}/products/99999", headers=admin_headers)
    print(f"  - DELETE /api/products/99999 with Admin JWT: Status={res_del_prod_admin.status_code}")
    if res_del_prod_admin.status_code not in [200, 404]:  # 200 OK, or 404 if deleted
        print(f"FAIL: Admin cannot delete products. Status: {res_del_prod_admin.status_code}")
        sys.exit(1)

    print("\n======================================================================")
    print("                ALL SECURITY AND RBAC TESTS PASSED!                   ")
    print("======================================================================")

if __name__ == "__main__":
    test_roles_and_localization()
