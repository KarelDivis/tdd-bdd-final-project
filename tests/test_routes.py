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
    nosetests --stop tests/test_service.py:TestProductService
    nosetests --stop tests/test_routes.py:TestProductRoutes
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models import db, init_db, Product
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

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
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

    #
    # ADD YOUR TEST CASES HERE
    #
    def test_get_product(self):
        """It should Get a single Product"""
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{str(test_product.id)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        read_data = response.get_json()
        self.assertEqual(read_data["id"], test_product.id)
        self.assertEqual(read_data["name"], test_product.name)
        self.assertEqual(read_data["description"], test_product.description)
        self.assertEqual(Decimal(read_data["price"]), test_product.price)
        self.assertEqual(read_data["available"], test_product.available)
        self.assertEqual(read_data["category"], test_product.category.name)

    def test_get_product_not_found(self):
        """Request for non-exiting product returns 404"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_a_product(self):
        """It should Update a single Product"""
        test_product = self._create_products(1)[0]
        test_product.name = "foo"
        test_product.description = "fighters"
        response = self.client.put(f"{BASE_URL}/{test_product.id}", json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_product = response.get_json()
        self.assertEqual(updated_product["id"], test_product.id)
        self.assertEqual(updated_product["name"], test_product.name)
        self.assertEqual(updated_product["description"], test_product.description)
        self.assertEqual(Decimal(updated_product["price"]), test_product.price)
        self.assertEqual(updated_product["available"], test_product.available)
        self.assertEqual(updated_product["category"], test_product.category.name)

    def test_update_non_existing_product(self):
        """Update non-existing Product should return 404"""
        test_product = self._create_products(1)[0]
        test_product.name = "foo"
        test_product.description = "fighters"
        response = self.client.put(f"{BASE_URL}/0", json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product_with_no_name(self):
        """It should not Update a Product without a name"""
        product = self._create_products()[0]
        update_product = product.serialize()
        del update_product["name"]
        logging.debug("Product no name: %s", update_product)
        response = self.client.put(f"{BASE_URL}/{product.id}", json=update_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_product_no_content_type(self):
        """It should not Update a Product with no Content-Type"""
        response = self.client.put(f"{BASE_URL}/1", data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_update_product_wrong_content_type(self):
        """It should not Update a Product with wrong Content-Type"""
        response = self.client.put(f"{BASE_URL}/1", data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_delete_product(self):
        """It should Delete a Product by ID"""
        products = self._create_products(2)
        product_count = self.get_product_count()
        product_delete = products[0]
        response = self.client.delete(f"{BASE_URL}/{product_delete.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.text, "")

        response = self.client.get(f"{BASE_URL}/{product_delete.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        new_count = self.get_product_count()
        self.assertEqual(new_count, product_count - 1)

    def test_delete_non_existing_product(self):
        """Delete non-existing Product should return 400"""
        response = self.client.delete(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_all_products(self):
        """It should List all Products"""
        expect_count = 10
        expect_products = self._create_products(expect_count)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_products = response.get_json()
        self.assertEqual(len(actual_products), expect_count)
        for actual in actual_products:
            expected = next(product for product in expect_products if product.id == actual["id"])
            self.assertEqual(actual["name"], expected.name)
            self.assertEqual(actual["description"], expected.description)
            self.assertEqual(Decimal(actual["price"]), expected.price)
            self.assertEqual(actual["available"], expected.available)
            self.assertEqual(actual["category"], expected.category.name)

    def test_list_by_name(self):
        """It should List Products by Name"""
        products = self._create_products(10)
        # change name of 3 products to same value
        for index in [2, 5, 7]:
            product = products[index]
            product.name = "foofoo"
            response = self.client.put(f"{BASE_URL}/{product.id}", json=product.serialize())
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.get_json()["name"], "foofoo")
        # lists product by name
        response = self.client.get(BASE_URL, query_string=f"name={quote_plus('foofoo')}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_products = response.get_json()
        self.assertEqual(len(actual_products), 3)
        for actual in actual_products:
            expected = next(product for product in products if product.id == actual["id"])
            self.assertEqual(actual["name"], expected.name)
            self.assertEqual(actual["description"], expected.description)
            self.assertEqual(Decimal(actual["price"]), expected.price)
            self.assertEqual(actual["available"], expected.available)
            self.assertEqual(actual["category"], expected.category.name)

    def test_list_by_category(self):
        """It should List Products by Category"""
        products = self._create_products(10)
        test_category = products[0].category
        category_found = [product for product in products if product.category == test_category]
        category_count = len(category_found)
        logging.debug("Found Products [%d] %s", category_count, category_found)

        response = self.client.get(BASE_URL, query_string=f"category={test_category.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_products = response.get_json()
        self.assertEqual(len(actual_products), category_count)
        for actual in actual_products:
            expected = next(product for product in products if product.id == actual["id"])
            self.assertEqual(actual["name"], expected.name)
            self.assertEqual(actual["description"], expected.description)
            self.assertEqual(Decimal(actual["price"]), expected.price)
            self.assertEqual(actual["available"], expected.available)
            self.assertEqual(actual["category"], expected.category.name)

    def test_list_by_availability(self):
        """It should List Products by Availability"""
        products = self._create_products(10)
        available_products = [product for product in products if product.available is True]
        available_count = len(available_products)
        logging.debug("Found [%d] available Products", available_count)

        response = self.client.get(BASE_URL, query_string="available=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        actual_products = response.get_json()
        self.assertEqual(len(actual_products), available_count)
        for actual in actual_products:
            expected = next(product for product in products if product.id == actual["id"])
            self.assertEqual(actual["name"], expected.name)
            self.assertEqual(actual["description"], expected.description)
            self.assertEqual(Decimal(actual["price"]), expected.price)
            self.assertEqual(actual["available"], expected.available)
            self.assertEqual(actual["category"], expected.category.name)

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
