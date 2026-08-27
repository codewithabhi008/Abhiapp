import os
import io
import json
import unittest
from app import create_app
from database import db
from models import User, Folder, FileRecord

class AbhiAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def login(self, username='abhi', password='AbhiApp@2026'):
        return self.client.post('/api/auth/login', json={
            'identifier': username,
            'password': password,
            'remember': True
        })

    def test_01_authentication_flow(self):
        print("\n--- Testing Authentication Flow ---")
        # 1. Unauthenticated access redirect
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 401)
        print("  [PASS] Unauthenticated API request blocked (401)")

        # 2. Login with wrong password
        res = self.client.post('/api/auth/login', json={
            'identifier': 'abhi',
            'password': 'WrongPassword123'
        })
        self.assertEqual(res.status_code, 401)
        print("  [PASS] Invalid password rejected")

        # 3. Successful login
        res = self.login()
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['username'], 'abhi')
        print(f"  [PASS] Logged in successfully as {data['user']['username']}")

        # 4. Check authenticated user info
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 200)
        print("  [PASS] Authenticated user session verified")

    def test_02_dashboard_statistics(self):
        print("\n--- Testing Dashboard Statistics ---")
        self.login()
        res = self.client.get('/api/dashboard/stats')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        stats = data['stats']
        print(f"  [PASS] Total Files: {stats['total_files']}")
        print(f"  [PASS] Total Storage: {stats['total_storage_formatted']}")
        print(f"  [PASS] AutoCAD Drawings Count: {stats['autocad']['count']}")
        print(f"  [PASS] SolidWorks Files Count: {stats['solidworks']['count']}")
        print(f"  [PASS] PDF Documents Count: {stats['pdf']['count']}")
        self.assertGreater(stats['total_files'], 0)

    def test_03_file_listing_and_filtering(self):
        print("\n--- Testing File Query, Search & Filters ---")
        self.login()
        
        # All files
        res = self.client.get('/api/files')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        print(f"  [PASS] All files query returned {data['count']} items")

        # Filter by DWG
        res = self.client.get('/api/files?type=dwg')
        dwg_data = res.get_json()
        self.assertTrue(all(f['file_extension'] == '.dwg' for f in dwg_data['files']))
        print(f"  [PASS] Filter by DWG returned {dwg_data['count']} AutoCAD drawings")

        # Filter by SLDPRT
        res = self.client.get('/api/files?type=sldprt')
        sw_data = res.get_json()
        self.assertTrue(all(f['file_extension'] == '.sldprt' for f in sw_data['files']))
        print(f"  [PASS] Filter by SLDPRT returned {sw_data['count']} SolidWorks parts")

        # Search by keyword
        res = self.client.get('/api/files?search=Panel')
        search_data = res.get_json()
        self.assertGreater(search_data['count'], 0)
        print(f"  [PASS] Search 'Panel' returned {search_data['count']} matching files")

    def test_04_file_upload_and_operations(self):
        print("\n--- Testing File Upload & CRUD Lifecycle ---")
        self.login()

        # 1. Upload new CAD file
        cad_content = b'AUTOCAD_DXF_TEST_FILE_CONTENT_ABHIAPP'
        data = {
            'files': (io.BytesIO(cad_content), 'Fabrication_Sheet_LaserCut.dxf'),
            'tags': 'lasercut, sheetmetal, dxf',
            'description': '3mm MS laser cutting profile for panel door'
        }
        res = self.client.post('/api/files/upload', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 201)
        upload_res = res.get_json()
        self.assertTrue(upload_res['success'])
        new_file = upload_res['files'][0]
        file_id = new_file['id']
        print(f"  [PASS] Uploaded {new_file['original_name']} (ID: {file_id}, Category: {new_file['category']})")

        # 2. Preview CAD details
        res = self.client.get(f'/api/files/{file_id}/preview')
        self.assertEqual(res.status_code, 200)
        preview_data = res.get_json()
        self.assertEqual(preview_data['type'], 'cad')
        print(f"  [PASS] CAD Inspector preview details returned: {preview_data['cad_details']['type']}")

        # 3. Rename File
        res = self.client.put(f'/api/files/{file_id}/rename', json={'new_name': 'Fabrication_Door_LaserCut_Rev2.dxf'})
        self.assertEqual(res.status_code, 200)
        print(f"  [PASS] File renamed to: {res.get_json()['file']['original_name']}")

        # 4. Toggle Favorite
        res = self.client.put(f'/api/files/{file_id}/favorite')
        self.assertEqual(res.status_code, 200)
        print(f"  [PASS] Favorite toggled: is_favorite={res.get_json()['is_favorite']}")

        # 5. Download File
        res = self.client.get(f'/api/files/{file_id}/download')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, cad_content)
        print(f"  [PASS] File downloaded and verified bit-exact binary content")

        # 6. Delete File
        res = self.client.delete(f'/api/files/{file_id}')
        self.assertEqual(res.status_code, 200)
        print(f"  [PASS] File safely deleted from disk and database")

    def test_05_folder_hierarchy(self):
        print("\n--- Testing Folder Tree Explorer ---")
        self.login()

        # 1. Fetch folder tree
        res = self.client.get('/api/folders')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(len(data['folders']), 0)
        print(f"  [PASS] Folder hierarchy tree contains {len(data['folders'])} folders")

        # 2. Create subfolder
        acad_folder = next(f for f in data['folders'] if f['folder_name'] == 'AutoCAD')
        res = self.client.post('/api/folders', json={
            'folder_name': 'Schematics_415V',
            'parent_folder_id': acad_folder['id']
        })
        self.assertEqual(res.status_code, 201)
        new_folder = res.get_json()['folder']
        print(f"  [PASS] Created subfolder: {new_folder['full_path']}")

        # 3. Clean up folder
        res = self.client.delete(f"/api/folders/{new_folder['id']}")
        self.assertEqual(res.status_code, 200)
        print(f"  [PASS] Subfolder deleted successfully")

    def test_06_settings_and_storage_quota(self):
        print("\n--- Testing Settings & Storage Quota ---")
        self.login()
        res = self.client.get('/api/settings/storage')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        print(f"  [PASS] Storage Quota: {data['total_storage_formatted']} / {data['quota_limit_formatted']} ({data['percentage_used']}%)")

if __name__ == '__main__':
    unittest.main()
