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

"""
Test cases for Product Model

Test cases can be run with:
    nosetests
    coverage report -m

While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_models.py:TestProductModel

"""
import os
import logging
import unittest
from decimal import Decimal
from service.models import Product, Category, db, DataValidationError
from service import app
from tests.factories import ProductFactory


DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)


######################################################################
#  P R O D U C T   M O D E L   T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductModel(unittest.TestCase):
    """Test Cases for Product Model"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        Product.init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    ######################################################################
    #  T E S T   C A S E S
    ######################################################################

    def test_create_a_product(self):
        """It should Create a product and assert that it exists"""
        product = Product(name="Fedora", description="A red hat", price=12.50, available=True, category=Category.CLOTHS)
        self.assertEqual(str(product), "<Product Fedora id=[None]>")
        self.assertTrue(product is not None)
        self.assertEqual(product.id, None)
        self.assertEqual(product.name, "Fedora")
        self.assertEqual(product.description, "A red hat")
        self.assertEqual(product.available, True)
        self.assertEqual(product.price, 12.50)
        self.assertEqual(product.category, Category.CLOTHS)

    def test_add_a_product(self):
        """It should Create a product and add it to the database"""
        products = Product.all()
        self.assertEqual(products, [])
        product = ProductFactory()
        product.id = None
        product.create()
        # Assert that it was assigned an id and shows up in the database
        self.assertIsNotNone(product.id)
        products = Product.all()
        self.assertEqual(len(products), 1)
        # Check that it matches the original product
        new_product = products[0]
        self.assertEqual(new_product.name, product.name)
        self.assertEqual(new_product.description, product.description)
        self.assertEqual(Decimal(new_product.price), product.price)
        self.assertEqual(new_product.available, product.available)
        self.assertEqual(new_product.category, product.category)

    #
    # ADD YOUR TEST CASES HERE
    #
    def test_read_a_product(self):
        """It should Read a Product"""
        product = ProductFactory()
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)
        # Fetch it back
        found_product = Product.find(product.id)
        self.assertEqual(found_product.id, product.id)
        self.assertEqual(found_product.name, product.name)
        self.assertEqual(found_product.description, product.description)
        self.assertEqual(found_product.price, product.price)

    def test_update_a_product(self):
        """It should Update a Product"""
        product = ProductFactory()
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)
        # Change it an save it
        product.description = "testing"
        original_id = product.id
        product.update()
        self.assertEqual(product.id, original_id)
        self.assertEqual(product.description, "testing")
        # Fetch it back and make sure the id hasn't changed
        # but the data did change
        products = Product.all()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].id, original_id)
        self.assertEqual(products[0].description, "testing")

    def test_delete_a_product(self):
        """It should Delete a Product"""
        product = ProductFactory()
        product.create()
        self.assertEqual(len(Product.all()), 1)
        # delete the product and make sure it isn't in the database
        product.delete()
        self.assertEqual(len(Product.all()), 0)

    def test_list_all_products(self):
        """It should List all Products in the database"""
        products = Product.all()
        self.assertEqual(products, [])
        # Create 5 Products
        for _ in range(5):
            product = ProductFactory()
            product.create()
        # See if we get back 5 products
        products = Product.all()
        self.assertEqual(len(products), 5)

    def test_find_by_name(self):
        """It should Find a Product by Name"""
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()
        name = products[0].name
        count = len([product for product in products if product.name == name])
        found = Product.find_by_name(name)
        self.assertEqual(found.count(), count)
        for product in found:
            self.assertEqual(product.name, name)

    def test_find_by_availability(self):
        """It should Find Products by Availability"""
        products = ProductFactory.create_batch(10)
        for product in products:
            product.create()
        available = products[0].available
        count = len([product for product in products if product.available == available])
        found = Product.find_by_availability(available)
        self.assertEqual(found.count(), count)
        for product in found:
            self.assertEqual(product.available, available)

    def test_find_by_category(self):
        """It should Find Products by Category"""
        products = ProductFactory.create_batch(10)
        for product in products:
            product.create()
        category = products[0].category
        count = len([product for product in products if product.category == category])
        found = Product.find_by_category(category)
        self.assertEqual(found.count(), count)
        for product in found:
            self.assertEqual(product.category, category)

    # ------------------------------------------------------------
    # ADDED TESTS BELOW
    # ------------------------------------------------------------

    def test_find_by_price(self):
        """It should Find Products by Price (Decimal and string)"""
        products = ProductFactory.create_batch(5)
        for product in products:
            product.create()
        price = products[0].price
        count = len([p for p in products if p.price == price])
        # Test with Decimal
        found = Product.find_by_price(price)
        self.assertEqual(found.count(), count)
        for product in found:
            self.assertEqual(product.price, price)
        # Test with string input (should be converted to Decimal)
        found_str = Product.find_by_price(str(price))
        self.assertEqual(found_str.count(), count)
        # Test with string containing quotes and spaces (as per method logic)
        found_str_quote = Product.find_by_price(f' "{price}" ')
        self.assertEqual(found_str_quote.count(), count)

    def test_find_by_price_not_found(self):
        """It should return empty list when price not found"""
        product = ProductFactory()
        product.create()
        found = Product.find_by_price(Decimal('99999.99'))
        self.assertEqual(found.count(), 0)

    def test_invalid_id_on_update(self):
        """It should raise DataValidationError when updating a product with no ID"""
        product = ProductFactory()
        product.id = None
        product.create()  # now it has an ID
        product.id = None  # simulate missing ID
        product.description = "testing"
        self.assertRaises(DataValidationError, product.update)

    def test_serialize_a_product(self):
        """It should serialize a Product into a dictionary"""
        product = ProductFactory()
        product.name = "Fedora"
        product.description = "A red hat"
        product.price = Decimal("12.50")
        product.available = True
        product.category = Category.CLOTHS
        product.create()
        # Fetch fresh from DB to ensure all fields are correct
        fresh = Product.find(product.id)
        data = fresh.serialize()
        self.assertEqual(data["id"], fresh.id)
        self.assertEqual(data["name"], "Fedora")
        self.assertEqual(data["description"], "A red hat")
        self.assertEqual(data["price"], "12.50")
        self.assertEqual(data["available"], True)
        self.assertEqual(data["category"], "CLOTHS")

    def test_deserialize_a_product(self):
        """It should deserialize a dictionary into a Product"""
        data = {
            "name": "Hammer",
            "description": "A sturdy tool",
            "price": "19.99",
            "available": False,
            "category": "TOOLS"
        }
        product = Product()
        product.deserialize(data)
        self.assertEqual(product.name, "Hammer")
        self.assertEqual(product.description, "A sturdy tool")
        self.assertEqual(product.price, Decimal("19.99"))
        self.assertEqual(product.available, False)
        self.assertEqual(product.category, Category.TOOLS)

    def test_deserialize_missing_key(self):
        """It should raise DataValidationError when a required key is missing"""
        data = {"name": "Hammer", "price": "19.99"}  # missing description
        product = Product()
        with self.assertRaises(DataValidationError) as context:
            product.deserialize(data)
        self.assertIn("missing description", str(context.exception))

    def test_deserialize_bad_available_type(self):
        """It should raise DataValidationError if 'available' is not a boolean"""
        data = {
            "name": "Hammer",
            "description": "Tool",
            "price": "19.99",
            "available": "yes",  # string instead of bool
            "category": "TOOLS"
        }
        product = Product()
        with self.assertRaises(DataValidationError) as context:
            product.deserialize(data)
        self.assertIn("Invalid type for boolean [available]", str(context.exception))

    def test_deserialize_bad_category(self):
        """It should raise DataValidationError if category string does not match any enum"""
        data = {
            "name": "Hammer",
            "description": "Tool",
            "price": "19.99",
            "available": True,
            "category": "INVALID_CATEGORY"
        }
        product = Product()
        with self.assertRaises(DataValidationError) as context:
            product.deserialize(data)
        self.assertIn("Invalid attribute", str(context.exception))

    def test_deserialize_bad_data_type(self):
        """It should raise DataValidationError when data is not a dict (TypeError)"""
        product = Product()
        with self.assertRaises(DataValidationError):
            product.deserialize("not a dict")

    def test_deserialize_with_none(self):
        """It should raise DataValidationError when data is None"""
        product = Product()
        with self.assertRaises(DataValidationError):
            product.deserialize(None)

    # def test_deserialize_invalid_price(self):
    #     """It should raise an exception when price cannot be converted to Decimal"""
    #     data = {
    #         "name": "Hammer",
    #         "description": "Tool",
    #         "price": "not a number",
    #         "available": True,
    #         "category": "TOOLS"
    #     }
    #     product = Product()
    #     # The current implementation does not explicitly catch decimal.InvalidOperation,
    #     # so it will raise that exception. This test ensures the behavior is documented.
    #     with self.assertRaises(InvalidOperation):
    #         product.deserialize(data)

    def test_repr_method(self):
        """It should return the correct string representation"""
        product = Product(name="Screwdriver", description="Tool", price=5.99)
        product.id = 42
        self.assertEqual(repr(product), "<Product Screwdriver id=[42]>")

    def test_category_enum_values(self):
        """It should have the correct Category enum members"""
        self.assertEqual(Category.UNKNOWN.value, 0)
        self.assertEqual(Category.CLOTHS.value, 1)
        self.assertEqual(Category.FOOD.value, 2)
        self.assertEqual(Category.HOUSEWARES.value, 3)
        self.assertEqual(Category.AUTOMOTIVE.value, 4)
        self.assertEqual(Category.TOOLS.value, 5)
        # Verify name access
        self.assertEqual(Category.UNKNOWN.name, "UNKNOWN")
        self.assertEqual(Category.CLOTHS.name, "CLOTHS")

    def test_product_category_default(self):
        """It should default to Category.UNKNOWN if not provided"""
        product = Product(name="Mystery", description="?", price=0)
        self.assertEqual(product.category, None)  # Column default is set on DB side
        # After adding to DB, the default should be applied
        product.create()
        self.assertEqual(product.category, Category.UNKNOWN)

    def test_find_by_category_with_enum_default(self):
        """It should find products using the default Category.UNKNOWN"""
        product = ProductFactory(category=Category.UNKNOWN)
        product.create()
        found = Product.find_by_category()
        self.assertEqual(found.count(), 1)
        self.assertEqual(found[0].category, Category.UNKNOWN)

    def test_find_nonexistent_product(self):
        """It should return None when finding a product by non-existent ID"""
        found = Product.find(99999)
        self.assertIsNone(found)
