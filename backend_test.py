#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Chuflay Educational Platform
Testing Global Admin Functionalities and Image Upload System
"""

import requests
import json
import os
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

class ChuflayBackendTester:
    def __init__(self):
        # Get backend URL from frontend .env
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    self.base_url = line.split('=')[1].strip() + '/api'
                    break
        
        print(f"Testing backend at: {self.base_url}")
        
        self.session = requests.Session()
        self.global_admin_token = None
        self.admin_colegio_token = None
        self.padre_token = None
        self.test_colegio_id = None
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def test_api_health(self) -> bool:
        """Test if API is accessible"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                self.log_test("API Health Check", True, f"Response: {data.get('message', 'OK')}")
                return True
            else:
                self.log_test("API Health Check", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Health Check", False, f"Error: {str(e)}")
            return False
    
    def create_test_users(self) -> bool:
        """Create test users for different roles"""
        try:
            # Create Global Admin
            global_admin_data = {
                "email": "globaladmin@chuflay.edu",
                "password": "GlobalAdmin123!",
                "role": "admin_global",
                "full_name": "Global Administrator"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=global_admin_data)
            if response.status_code in [200, 400]:  # 400 if already exists
                self.log_test("Create Global Admin User", True, "User created or already exists")
            else:
                self.log_test("Create Global Admin User", False, f"Status: {response.status_code}")
                return False
            
            # Create Admin Colegio (will be assigned after creating college)
            admin_colegio_data = {
                "email": "admin@colegio-test.edu",
                "password": "AdminColegio123!",
                "role": "admin_colegio",
                "full_name": "Admin Colegio Test"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=admin_colegio_data)
            if response.status_code in [200, 400]:
                self.log_test("Create Admin Colegio User", True, "User created or already exists")
            else:
                self.log_test("Create Admin Colegio User", False, f"Status: {response.status_code}")
                return False
            
            # Create Padre
            padre_data = {
                "email": "padre@test.com",
                "password": "Padre123!",
                "role": "padre",
                "full_name": "Padre Test"
            }
            
            response = self.session.post(f"{self.base_url}/auth/register", json=padre_data)
            if response.status_code in [200, 400]:
                self.log_test("Create Padre User", True, "User created or already exists")
                return True
            else:
                self.log_test("Create Padre User", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Create Test Users", False, f"Error: {str(e)}")
            return False
    
    def login_users(self) -> bool:
        """Login test users and get tokens"""
        try:
            # Login Global Admin
            login_data = {
                "email": "globaladmin@chuflay.edu",
                "password": "GlobalAdmin123!"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.global_admin_token = data['access_token']
                self.log_test("Login Global Admin", True, "Token obtained")
            else:
                self.log_test("Login Global Admin", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
            
            # Login Admin Colegio
            login_data = {
                "email": "admin@colegio-test.edu",
                "password": "AdminColegio123!"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.admin_colegio_token = data['access_token']
                self.log_test("Login Admin Colegio", True, "Token obtained")
            else:
                self.log_test("Login Admin Colegio", False, f"Status: {response.status_code}")
                return False
            
            # Login Padre
            login_data = {
                "email": "padre@test.com",
                "password": "Padre123!"
            }
            
            response = self.session.post(f"{self.base_url}/auth/login", json=login_data)
            if response.status_code == 200:
                data = response.json()
                self.padre_token = data['access_token']
                self.log_test("Login Padre", True, "Token obtained")
                return True
            else:
                self.log_test("Login Padre", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Login Users", False, f"Error: {str(e)}")
            return False
    
    def test_global_admin_college_management(self) -> bool:
        """Test Global Admin college management endpoints"""
        if not self.global_admin_token:
            self.log_test("Global Admin College Management", False, "No global admin token")
            return False
        
        headers = {"Authorization": f"Bearer {self.global_admin_token}"}
        
        try:
            # Test: Create College
            college_data = {
                "nombre": "Colegio Test Automatizado",
                "rnc": "123456789",
                "direccion": "Calle Test 123",
                "ciudad": "Santo Domingo",
                "telefono": "809-123-4567",
                "email_oficial": "info@colegiotest.edu",
                "director": "Director Test",
                "plan_suscripcion": "basico"
            }
            
            response = self.session.post(f"{self.base_url}/global/colegios", json=college_data, headers=headers)
            if response.status_code == 200:
                college = response.json()
                self.test_colegio_id = college['id']
                self.log_test("Global Admin - Create College", True, f"College ID: {self.test_colegio_id}")
            else:
                self.log_test("Global Admin - Create College", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
            
            # Test: Get All Colleges
            response = self.session.get(f"{self.base_url}/global/colegios", headers=headers)
            if response.status_code == 200:
                colleges = response.json()
                self.log_test("Global Admin - Get All Colleges", True, f"Found {len(colleges)} colleges")
            else:
                self.log_test("Global Admin - Get All Colleges", False, f"Status: {response.status_code}")
                return False
            
            # Test: Update College
            update_data = {
                "direccion": "Nueva Direccion Test 456",
                "telefono": "809-987-6543"
            }
            
            response = self.session.put(f"{self.base_url}/global/colegios/{self.test_colegio_id}", json=update_data, headers=headers)
            if response.status_code == 200:
                self.log_test("Global Admin - Update College", True, "College updated successfully")
            else:
                self.log_test("Global Admin - Update College", False, f"Status: {response.status_code}")
                return False
            
            return True
            
        except Exception as e:
            self.log_test("Global Admin College Management", False, f"Error: {str(e)}")
            return False
    
    def test_global_admin_user_management(self) -> bool:
        """Test Global Admin user management endpoints"""
        if not self.global_admin_token:
            self.log_test("Global Admin User Management", False, "No global admin token")
            return False
        
        headers = {"Authorization": f"Bearer {self.global_admin_token}"}
        
        try:
            # Test: Get All Users
            response = self.session.get(f"{self.base_url}/global/usuarios", headers=headers)
            if response.status_code == 200:
                users = response.json()
                self.log_test("Global Admin - Get All Users", True, f"Found {len(users)} users")
                
                # Find a user to impersonate (not global admin)
                target_user = None
                for user in users:
                    if user['role'] != 'admin_global':
                        target_user = user
                        break
                
                if target_user:
                    # Test: Impersonate User
                    response = self.session.post(f"{self.base_url}/global/impersonate/{target_user['id']}", headers=headers)
                    if response.status_code == 200:
                        impersonate_data = response.json()
                        self.log_test("Global Admin - Impersonate User", True, f"Impersonated: {target_user['full_name']}")
                    else:
                        self.log_test("Global Admin - Impersonate User", False, f"Status: {response.status_code}")
                        return False
                else:
                    self.log_test("Global Admin - Impersonate User", False, "No suitable user found for impersonation")
                
                return True
            else:
                self.log_test("Global Admin - Get All Users", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Global Admin User Management", False, f"Error: {str(e)}")
            return False
    
    def test_global_admin_statistics(self) -> bool:
        """Test Global Admin statistics endpoint"""
        if not self.global_admin_token:
            self.log_test("Global Admin Statistics", False, "No global admin token")
            return False
        
        headers = {"Authorization": f"Bearer {self.global_admin_token}"}
        
        try:
            response = self.session.get(f"{self.base_url}/global/estadisticas", headers=headers)
            if response.status_code == 200:
                stats = response.json()
                expected_keys = ['total_colegios', 'colegios_activos', 'total_usuarios', 'total_estudiantes']
                
                missing_keys = [key for key in expected_keys if key not in stats]
                if not missing_keys:
                    self.log_test("Global Admin - Statistics", True, f"All expected statistics present: {list(stats.keys())}")
                    return True
                else:
                    self.log_test("Global Admin - Statistics", False, f"Missing keys: {missing_keys}")
                    return False
            else:
                self.log_test("Global Admin - Statistics", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Global Admin Statistics", False, f"Error: {str(e)}")
            return False
    
    def test_global_admin_subscriptions(self) -> bool:
        """Test Global Admin subscription management"""
        if not self.global_admin_token or not self.test_colegio_id:
            self.log_test("Global Admin Subscriptions", False, "Missing token or college ID")
            return False
        
        headers = {"Authorization": f"Bearer {self.global_admin_token}"}
        
        try:
            # Test: Create Subscription
            subscription_data = {
                "colegio_id": self.test_colegio_id,
                "plan": "premium",
                "meses": 12,
                "precio_mensual": 99.99
            }
            
            response = self.session.post(f"{self.base_url}/global/suscripciones", json=subscription_data, headers=headers)
            if response.status_code == 200:
                subscription = response.json()
                self.log_test("Global Admin - Create Subscription", True, f"Subscription created for plan: {subscription['plan']}")
            else:
                self.log_test("Global Admin - Create Subscription", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
            
            # Test: Get All Subscriptions
            response = self.session.get(f"{self.base_url}/global/suscripciones", headers=headers)
            if response.status_code == 200:
                subscriptions = response.json()
                self.log_test("Global Admin - Get All Subscriptions", True, f"Found {len(subscriptions)} subscriptions")
                return True
            else:
                self.log_test("Global Admin - Get All Subscriptions", False, f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Global Admin Subscriptions", False, f"Error: {str(e)}")
            return False
    
    def test_image_upload_system(self) -> bool:
        """Test image upload endpoint"""
        if not self.global_admin_token:
            self.log_test("Image Upload System", False, "No authentication token")
            return False
        
        headers = {"Authorization": f"Bearer {self.global_admin_token}"}
        
        try:
            # Create a test image file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                # Create a simple PNG file (1x1 pixel)
                png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
                temp_file.write(png_data)
                temp_file_path = temp_file.name
            
            # Test: Upload Image
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test_image.png', f, 'image/png')}
                response = self.session.post(f"{self.base_url}/upload/imagen", files=files, headers=headers)
            
            # Clean up temp file
            os.unlink(temp_file_path)
            
            if response.status_code == 200:
                upload_result = response.json()
                if 'url' in upload_result:
                    self.log_test("Image Upload - Valid Image", True, f"Image uploaded: {upload_result['url']}")
                else:
                    self.log_test("Image Upload - Valid Image", False, "No URL in response")
                    return False
            else:
                self.log_test("Image Upload - Valid Image", False, f"Status: {response.status_code}, Response: {response.text}")
                return False
            
            # Test: Upload Invalid File (should fail)
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                temp_file.write(b'This is not an image')
                temp_file_path = temp_file.name
            
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                response = self.session.post(f"{self.base_url}/upload/imagen", files=files, headers=headers)
            
            os.unlink(temp_file_path)
            
            if response.status_code == 400:
                self.log_test("Image Upload - Invalid File Type", True, "Correctly rejected non-image file")
                return True
            else:
                self.log_test("Image Upload - Invalid File Type", False, f"Should have rejected non-image, got status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Image Upload System", False, f"Error: {str(e)}")
            return False
    
    def test_role_based_access_control(self) -> bool:
        """Test role-based access control"""
        try:
            # Test: Non-Global Admin trying to access global endpoints
            if self.admin_colegio_token:
                headers = {"Authorization": f"Bearer {self.admin_colegio_token}"}
                response = self.session.get(f"{self.base_url}/global/colegios", headers=headers)
                
                if response.status_code == 403:
                    self.log_test("RBAC - Admin Colegio Access Denied", True, "Correctly denied access to global endpoints")
                else:
                    self.log_test("RBAC - Admin Colegio Access Denied", False, f"Should have been denied, got status: {response.status_code}")
                    return False
            
            # Test: Padre trying to access global endpoints
            if self.padre_token:
                headers = {"Authorization": f"Bearer {self.padre_token}"}
                response = self.session.get(f"{self.base_url}/global/usuarios", headers=headers)
                
                if response.status_code == 403:
                    self.log_test("RBAC - Padre Access Denied", True, "Correctly denied access to global endpoints")
                    return True
                else:
                    self.log_test("RBAC - Padre Access Denied", False, f"Should have been denied, got status: {response.status_code}")
                    return False
            
            return True
            
        except Exception as e:
            self.log_test("Role-Based Access Control", False, f"Error: {str(e)}")
            return False
    
    def test_authentication_validation(self) -> bool:
        """Test JWT token validation"""
        try:
            # Test: Invalid token
            headers = {"Authorization": "Bearer invalid_token_here"}
            response = self.session.get(f"{self.base_url}/global/colegios", headers=headers)
            
            if response.status_code == 401:
                self.log_test("Auth - Invalid Token", True, "Correctly rejected invalid token")
            else:
                self.log_test("Auth - Invalid Token", False, f"Should have rejected invalid token, got status: {response.status_code}")
                return False
            
            # Test: No token
            response = self.session.get(f"{self.base_url}/global/colegios")
            
            if response.status_code == 403:  # FastAPI HTTPBearer returns 403 for missing token
                self.log_test("Auth - Missing Token", True, "Correctly rejected missing token")
                return True
            else:
                self.log_test("Auth - Missing Token", False, f"Should have rejected missing token, got status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Authentication Validation", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("=" * 60)
        print("CHUFLAY BACKEND COMPREHENSIVE TESTING")
        print("=" * 60)
        
        # Basic connectivity
        if not self.test_api_health():
            print("❌ API not accessible, stopping tests")
            return
        
        # Setup test users
        self.create_test_users()
        if not self.login_users():
            print("❌ Failed to login test users, stopping tests")
            return
        
        # Test Global Admin Functionalities
        print("\n🔧 Testing Global Admin Functionalities...")
        self.test_global_admin_college_management()
        self.test_global_admin_user_management()
        self.test_global_admin_statistics()
        self.test_global_admin_subscriptions()
        
        # Test Image Upload System
        print("\n📸 Testing Image Upload System...")
        self.test_image_upload_system()
        
        # Test Security
        print("\n🔒 Testing Authentication & Authorization...")
        self.test_role_based_access_control()
        self.test_authentication_validation()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        failed = len(self.test_results) - passed
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        
        if failed > 0:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    tester = ChuflayBackendTester()
    tester.run_all_tests()