######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_routes.py:TestProductRoutes
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Category, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    ######################################################################
    # T E S T   L I S T   P R O D U C T S   (all + filtering)
    ######################################################################
    def test_list_all_products(self):
        """It should List all Products"""
        # Create 5 products
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_list_products_filter_by_name(self):
        """It should List Products filtered by name (partial match)"""
        product1 = ProductFactory(name="Blue Widget")
        product2 = ProductFactory(name="Red Widget")
        product3 = ProductFactory(name="Green Gadget")
        resp1 = self.client.post(BASE_URL, json=product1.serialize())
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        resp2 = self.client.post(BASE_URL, json=product2.serialize())
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        resp3 = self.client.post(BASE_URL, json=product3.serialize())
        self.assertEqual(resp3.status_code, status.HTTP_201_CREATED)

        response = self.client.get(BASE_URL, query_string={"name": "widget"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        names = [p["name"] for p in data]
        self.assertIn("Blue Widget", names)
        self.assertIn("Red Widget", names)
        self.assertNotIn("Green Gadget", names)

    def test_list_products_filter_by_availability(self):
        """It should List Products filtered by availability"""
        product_avail = ProductFactory(available=True)
        product_not_avail = ProductFactory(available=False)
        resp1 = self.client.post(BASE_URL, json=product_avail.serialize())
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        resp2 = self.client.post(BASE_URL, json=product_not_avail.serialize())
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)

        response = self.client.get(BASE_URL, query_string={"available": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]["available"])

        response = self.client.get(BASE_URL, query_string={"available": "false"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["available"], False)

    def test_list_products_filter_by_multiple(self):
        """It should List Products filtered by name AND category"""
        product1 = ProductFactory(name="Apple Pie", category=Category.FOOD)
        product2 = ProductFactory(name="Banana", category=Category.FOOD)
        product3 = ProductFactory(name="Apple Cider", category=Category.HOUSEWARES)
        resp1 = self.client.post(BASE_URL, json=product1.serialize())
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        resp2 = self.client.post(BASE_URL, json=product2.serialize())
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        resp3 = self.client.post(BASE_URL, json=product3.serialize())
        self.assertEqual(resp3.status_code, status.HTTP_201_CREATED)

        response = self.client.get(BASE_URL, query_string={"name": "apple", "category": "FOOD"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Apple Pie")

    def test_list_products_invalid_category(self):
        """It should return 400 when filtering by invalid category"""
        response = self.client.get(BASE_URL, query_string={"category": "INVALID"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_products_invalid_availability(self):
        """It should return 400 when filtering by invalid availability value"""
        response = self.client.get(BASE_URL, query_string={"available": "maybe"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ######################################################################
    # # T E S T   R E A D   A   P R O D U C T
    # ######################################################################
    def test_get_product(self):
        """It should Retrieve a single Product by ID"""
        # Create a product
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)

    def test_get_product_not_found(self):
        """It should return 404 when Product not found"""
        response = self.client.get(f"{BASE_URL}/99999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ######################################################################
    # # T E S T   U P D A T E   A   P R O D U C T
    # ######################################################################
    def test_update_product(self):
        """It should Update an existing Product"""
        # Create a product
        product = self._create_products(1)[0]
        # Modify data
        update_data = product.serialize()
        update_data["name"] = "Updated Name"
        update_data["price"] = "99.99"
        response = self.client.put(f"{BASE_URL}/{product.id}", json=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], "Updated Name")
        self.assertEqual(Decimal(data["price"]), Decimal("99.99"))

    def test_update_product_wrong_id(self):
        """It should throw an error on updating with wrong ID"""
        # Create a product
        product = self._create_products(1)[0]
        # Modify data
        update_data = product.serialize()
        update_data["id"] = update_data["id"]+1
        update_data["name"] = "Updated Name"
        update_data["price"] = "99.99"
        response = self.client.put(f"{BASE_URL}/{product.id}", json=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # def test_update_product_missing_key(self):
    #     """It should throw an error on updating with missing Key"""
    #     # Create a product
    #     product = self._create_products(1)[0]
    #     # Modify data
    #     update_data = {}

    #     response = self.client.put(f"{BASE_URL}/{product.id}", json=update_data)
    #     self.assertRaise(KeyError, routes.update_product)


    def test_update_product_not_found(self):
        """It should return 404 when updating a non-existent Product"""
        update_data = {"name": "Ghost", "description": "None", "price": 0.0, "available": True, "category": "UNKNOWN"}
        response = self.client.put(f"{BASE_URL}/99999", json=update_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

#   # def test_update_product_missing_data(self):
        """It should return 400 when update data is incomplete"""
        product = self._create_products(1)[0]
        update_data = {"name": "Only Name"}  # missing required fields
        response = self.client.put(f"{BASE_URL}/{product.id}", json=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ######################################################################
    # # T E S T   D E L E T E   A   P R O D U C T
    # ######################################################################
    def test_delete_product(self):
        """It should Delete a Product"""
        product = self._create_products(1)[0]
        response = self.client.delete(f"{BASE_URL}/{product.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Verify it's gone
        response = self.client.get(f"{BASE_URL}/{product.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product_not_found(self):
        """It should return 204 even if product doesn't exist (idempotent)"""
        response = self.client.delete(f"{BASE_URL}/99999")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
