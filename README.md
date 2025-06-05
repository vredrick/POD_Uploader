# POD Uploader

This repository contains a small Flask web application used to upload Print On Demand (POD) products to Printify. The app guides you through selecting a shop, uploading a CSV file that defines product data, choosing a print provider and variants, and finally creating the products through Printify's API.

## Setup

1. Install the Python dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
python app.py
```

3. Visit `http://localhost:5000` in your browser and follow the prompts. You will need a Printify API token to authenticate your requests.

## CSV Format

The uploaded CSV should include the following columns:

- `local_path` – URL for the product image to upload
- `file_name` – The name to use when uploading the image
- `title` – Product title
- `description` – Product description
- `tags` – Comma separated tags
- `blueprint_id` – Blueprint ID of the product in Printify

Each row represents one product to create. The app will parse the file and allow you to select print providers and variants before creating the items in your shop.

