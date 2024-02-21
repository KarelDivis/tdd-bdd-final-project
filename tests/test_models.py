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
from service.models import Product, Category, db
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
        """It should Read a product"""
        product = ProductFactory()
        app.logger.debug(f"Product for Reading test: Name = {product.name}, Description: {product.description}")
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)
        found_product = Product.find(product.id)
        self.assertEqual(found_product.name, product.name)
        self.assertEqual(found_product.description, product.description)
        self.assertEqual(Decimal(found_product.price), product.price)
        self.assertEqual(found_product.available, product.available)
        self.assertEqual(found_product.category, product.category)

    def test_update_a_product(self):
        """It should Update a Product"""
        product = ProductFactory()
        app.logger.debug(f"Product prepared for Update test: Name = {product.name}, Description: {product.description}")
        product.id = None
        product.create()
        self.assertIsNotNone(product.id)
        created_id = product.id
        app.logger.debug(f"Product created for Update test: Name = {product.name}, Description: {product.description}")
        product.description = "My changed product description"
        product.update()
        app.logger.debug(f"Product updated in Update test: Name = {product.name}, Description: {product.description}")
        self.assertEqual(product.id, created_id)
        self.assertEqual(product.description, "My changed product description")
        products = Product.all()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].id, created_id)
        self.assertEqual(products[0].description, "My changed product description")

    def test_delete_a_product(self):
        """It should Delete a Product"""
        product = ProductFactory()
        app.logger.debug(f"Product prepared for Delete test: Name = {product.name}, Description: {product.description}")
        product.create()
        self.assertIsNotNone(product.id)
        self.assertEqual(len(Product.all()), 1)
        product.delete()
        self.assertEqual(len(Product.all()), 0)

    def test_list_all_products(self):
        """It should List all Products in the database"""
        self.assertEqual(len(Product.all()), 0)
        for _ in range(5):
            product = ProductFactory()
            product.create()
        self.assertEqual(len(Product.all()), 5)

    def test_find_by_name(self):
        """It should Find Products by Name"""
        product_names = []
        products = ProductFactory.create_batch(5)
        for product in products:            
            product_names.append(product.name)
            product.create()
        product_unique_names = set(product_names)
        for a_name in product_unique_names:
            a_name_count = product_names.count(a_name)
            products = Product.find_by_name(a_name)
            self.assertEqual(products.count(), a_name_count)
            for item in products:
                self.assertEqual(item.name, a_name)

    def test_find_by_availability(self):
        """It should Find Products by Availability"""
        available_count = 0
        products = ProductFactory.create_batch(10)
        for product in products:            
            if product.available:
                available_count += 1
            product.create()
        non_available_count = 10 - available_count
        products = Product.find_by_availability(False)
        self.assertEqual(products.count(), non_available_count)
        for product in products:
            self.assertFalse(product.available)

    def test_find_by_category(self):
        """It should Find Products by Category"""
        category_list = [] 
        products = ProductFactory.create_batch(10)
        for product in products:            
            category_list.append(product.category)
            product.create()
        unique_categories = set(category_list)
        for a_category in unique_categories:
            prod_cat_count = category_list.count(a_category)
            products = Product.find_by_category(a_category)
            self.assertEqual(products.count(), prod_cat_count)
            for product in products:
                self.assertEqual(product.category, a_category)
