import io
import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import process_csv_file

class TestProcessCSVFile(unittest.TestCase):
    def test_process_csv_file(self):
        csv_content = (
            "local_path,file_name,title,description,tags,blueprint_id\n"
            "http://example.com/image1.png,image1.png,Product 1,Description 1,\"tag1,tag2\",123\n"
            "http://example.com/image2.png,image2.png,Product 2,Description 2,\"tag3,tag4\",456\n"
        )
        file_obj = io.BytesIO(csv_content.encode('utf-8'))

        blueprint_ids, products = process_csv_file(file_obj)

        expected_ids = [123, 456]
        self.assertEqual(blueprint_ids, expected_ids)

        expected_products = [
            {
                'local_path': 'http://example.com/image1.png',
                'file_name': 'image1.png',
                'title': 'Product 1',
                'description': 'Description 1',
                'tags': 'tag1,tag2',
                'blueprint_id': '123'
            },
            {
                'local_path': 'http://example.com/image2.png',
                'file_name': 'image2.png',
                'title': 'Product 2',
                'description': 'Description 2',
                'tags': 'tag3,tag4',
                'blueprint_id': '456'
            }
        ]

        self.assertEqual(products, expected_products)

if __name__ == '__main__':
    unittest.main()
