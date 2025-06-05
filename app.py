import logging
from flask import Flask, render_template, request, redirect, url_for
import requests
import csv
import json
import traceback

app = Flask(__name__)

# Set the base URL for Printify API requests
BASE_URL = 'https://api.printify.com/v1/'

def build_headers(token):
    """Return headers for Printify API requests."""
    return {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

logging.basicConfig(level=logging.DEBUG)

class ProductList:
    def __init__(self):
        self.products = []

    def add_product(self, product):
        self.products.append(product)

    def get_products(self):
        return self.products

product_list = ProductList()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        token = request.form['token']
        shops = get_printify_shops(token)
        return render_template('select_store.html', shops=shops, token=token)
    return render_template('index.html')

@app.route('/select_store', methods=['POST'])
def select_store():
    token = request.form['token']
    shop_id = request.form['shop_id']
    return render_template('upload_csv.html', token=token, shop_id=shop_id)

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    global product_list

    token = request.form['token']
    shop_id = request.form['shop_id']
    file = request.files['csv_file']
    blueprint_ids, products = process_csv_file(file)  # Get the blueprint_ids and products
    logging.debug("Blueprint IDs from CSV file: %s", blueprint_ids)

    for product in products:
        product_list.add_product(product)

    print_providers = []
    for blueprint_id in blueprint_ids:
        print("Blueprint ID before call to get_print_providers:", blueprint_id)
        providers = get_print_providers(blueprint_id, token)
        product_title = get_product_title(blueprint_id, token)  # fetch the product title
        print("Blueprint ID:", "ID Check")
        print("Print Providers:", "print_providers")
        print_providers.append({
            'blueprint_id': blueprint_id, 
            'title': product_title, 
            'providers': providers
        })

    logging.debug("Final Print Providers: %s", print_providers)

    return render_template('select_print_provider.html', print_providers=print_providers, token=token, shop_id=shop_id, blueprint_ids=blueprint_ids)

@app.route('/select_variants', methods=['POST'])
def select_variants():
    try:
        token = request.form['token']
        shop_id = request.form['shop_id']

        selected_print_providers = []
        variant_mappings = []  # This list stores variant mappings for each print provider
        for item in request.form:
            if item.startswith('print_provider_id_'):
                blueprint_id = request.form.get(f'blueprint_id_{item.replace("print_provider_id_", "")}')
                print_provider_id = request.form[item]
                product_title = get_product_title(blueprint_id, token)
                variants = get_variants(blueprint_id, print_provider_id, token)

                # Prepare data for the template
                sizes = set()
                colors = set()
                variant_mapping = {}  # Map of size and color to variant ID
                for variant in variants:
                    if 'options' in variant:
                        size = variant['options'].get('size')
                        color = variant['options'].get('color')
                        if size and color:
                            sizes.add(size)
                            colors.add(color)
                            if size not in variant_mapping:
                                variant_mapping[size] = {}
                            variant_mapping[size][color] = variant['id']

                print_provider_details = {
                    'blueprint_id': blueprint_id,
                    'print_provider_id': print_provider_id,
                    'title': product_title,
                    'sizes': list(sizes),
                    'colors': list(colors),
                    'variant_mapping': variant_mapping,
                    'variant_ids': list(variant_mapping.values())
                }
                selected_print_providers.append(print_provider_details)

                variant_mappings.append({blueprint_id: {print_provider_id: variant_mapping}})  # Store the variant mapping for this print provider

        # Pass variant_mappings to the template
        return render_template('select_variants.html', token=token, shop_id=shop_id, print_providers=selected_print_providers, variant_mappings=variant_mappings)
    except Exception as e:
        logging.error("Error occurred: %s", str(e))
        traceback.print_exc()
        raise e

@app.route('/create_product', methods=['POST'])
def create_product():
    global product_list
    token = request.form['token']
    shop_id = request.form['shop_id']
    products = product_list.get_products()

    # Extract print provider details
    blueprint_ids = request.form.getlist('blueprint_id[]')
    print_provider_ids = request.form.getlist('print_provider_id[]')
    variant_ids_groups = [request.form.getlist(f'variant_id_{blueprint_id}_{print_provider_id}') 
                        for blueprint_id, print_provider_id in zip(blueprint_ids, print_provider_ids)]
    try:
        for i, (blueprint_id, print_provider_id, variant_ids_group) in enumerate(zip(blueprint_ids, print_provider_ids, variant_ids_groups)):
            logging.debug("Processing product with Blueprint ID: %s", blueprint_id)
            logging.debug("Print Provider ID: %s", print_provider_id)

            print("Variant IDs: ", variant_ids_group)

            for product in products:
                # Only process products that match the current blueprint_id
                if product['blueprint_id'] != blueprint_id:
                    continue

                logging.debug("Product: %s", product)

                # Call the image upload function and get the image ID
                image_id = upload_image(product['file_name'], product['local_path'], token)

                logging.debug("Image ID: %s", image_id)

                variant_ids = [
                    {
                        "id": int(id), 
                        "price": 4500, 
                        "is_enabled": True
                    } 
                    for variant_id_group in variant_ids_group
                    for id in variant_id_group.split(',')  # Split the group into individual variant IDs
                    if id  # Ignore empty strings
                ]

                product_data = {
                    "title": product['title'],
                    "description": product['description'],
                    "blueprint_id": int(blueprint_id),  # Convert to int
                    "print_provider_id": int(print_provider_id),  # Convert to int
                    "tags": product['tags'].split(','),
                    "variants": variant_ids,
                    "print_areas": [
                        {
                            "variant_ids": [variant["id"] for variant in variant_ids],
                            "placeholders": [
                                {
                                    "position": "front",
                                    "images": [
                                        {
                                            "id": image_id,  # Use the image ID from the upload function
                                            "x": 0.5, 
                                            "y": 0.5, 
                                            "scale": 0.5,
                                            "angle": 0
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }

                logging.debug("Product Data: %s", product_data)

                create_product_api(shop_id, product_data, token)

        return "Products created successfully!"

    except Exception as e:
        logging.error("Error occurred: %s", str(e))
        traceback.print_exc()
        return "An error occurred while creating products."

def get_printify_shops(token):
    url = BASE_URL + 'shops.json'
    response = requests.get(url, headers=build_headers(token))
    shops = response.json()
    return shops

def get_product_title(blueprint_id, token):
    url = BASE_URL + f'catalog/blueprints/{blueprint_id}.json'
    response = requests.get(url, headers=build_headers(token))
    product_data = response.json()
    return product_data['title']  # replace 'title' with the correct key for the product title

def get_print_providers(blueprint_id, token):
    url = BASE_URL + f'catalog/blueprints/{blueprint_id}/print_providers.json'
    response = requests.get(url, headers=build_headers(token))
    print_providers = response.json()
    return print_providers

def get_variants(blueprint_id, print_provider_id, token):
    url = BASE_URL + f'catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json'
    response = requests.get(url, headers=build_headers(token))
    data = response.json()

    logging.debug("Response from Printify API: All variants received successfully")

    # Get the list of variants from the response data
    variants = data['variants']

    return variants


def upload_image(file_name, url, token):
    upload_url = BASE_URL + 'uploads/images.json'
    data = {
        'file_name': file_name,
        'url': url
    }
    response = requests.post(upload_url, headers=build_headers(token), json=data)
    if response.status_code != 200:
        raise Exception(f"Failed to upload image: {response.text}")
    print(f"Response from Printify API: {response.text} Image Uploaded Successfully")
    return response.json()['id']


def create_product_api(shop_id, product_data, token):
    url = BASE_URL + f'shops/{shop_id}/products.json'
    response = requests.post(url, headers=build_headers(token), json=product_data)
    print(product_data)
    #print(f"Response from Printify API: {response.text}")
    return response

def process_csv_file(file):
    csv_data = file.read().decode('utf-8')
    csv_reader = csv.DictReader(csv_data.splitlines(), delimiter=',')

    products = []  # Store the product data from the CSV file
    blueprint_ids = [] # Store the blueprint IDs from the CSV file
    for row in csv_reader:
        product = {
            'local_path': row['local_path'],
            'file_name': row['file_name'],
            'title': row['title'],
            'description': row['description'],
            'tags': row['tags'],
            'blueprint_id': row['blueprint_id']
        }

        products.append(product)
        blueprint_ids.append(int(row['blueprint_id'])) # Cast the blueprint_id to int

    return blueprint_ids, products

if __name__ == '__main__':
    app.run(debug=True)
