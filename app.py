import streamlit as st
import os
import zipfile
from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader
from io import BytesIO
import shutil

# Function to save images sequentially
def save_images_sequentially(image_list, output_folder, start_index):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    ordered_images = []
    for idx, image in enumerate(image_list, start=start_index):
        image_filename = f"{idx:03d}.jpg"  # Naming images sequentially
        image_path = os.path.join(output_folder, image_filename)
        image.save(image_path, "JPEG")
        ordered_images.append(image_path)
    
    return ordered_images, start_index + len(image_list)

# Function to process selected pages from the special PDF
def process_selected_pages(special_pdf_bytes, selected_pages, output_folder, start_index):
    images = []
    for page in selected_pages:
        images.extend(convert_from_bytes(special_pdf_bytes, first_page=page, last_page=page, dpi=200))
    
    return save_images_sequentially(images, output_folder, start_index)

# Function to process PDFs
def process_pdfs(uploaded_files, output_folder, start_index):
    images = []
    for pdf_file in uploaded_files:
        pdf_bytes = pdf_file.read()
        images.extend(convert_from_bytes(pdf_bytes, dpi=200))
    
    return save_images_sequentially(images, output_folder, start_index)

# Function to save uploaded JPEGs
def process_jpegs(uploaded_files, output_folder, start_index):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    ordered_images = []
    for idx, jpeg_file in enumerate(uploaded_files, start=start_index):
        image_filename = f"{idx:03d}.jpg"  # Naming JPEGs sequentially
        image_path = os.path.join(output_folder, image_filename)
        with open(image_path, "wb") as f:
            f.write(jpeg_file.read())
        ordered_images.append(image_path)
    
    return ordered_images, start_index + len(uploaded_files)

# Function to create ZIP file
def create_zip(image_files):
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for image_path in image_files:
            zipf.write(image_path, os.path.basename(image_path))
    zip_buffer.seek(0)
    return zip_buffer

# Streamlit UI
st.title("PDF & JPEG to Zip Converter")

# Upload JPEGs first
uploaded_jpegs = st.file_uploader("Upload JPEGs", accept_multiple_files=True, type=["jpg", "jpeg"])

# Upload special PDF
special_pdf = st.file_uploader("Upload a large PDF (Choose specific pages)", type=["pdf"])

selected_pages = []
special_pdf_bytes = None

if special_pdf:
    special_pdf_bytes = special_pdf.read()
    special_pdf_io = BytesIO(special_pdf_bytes)
    reader = PdfReader(special_pdf_io)
    num_pages = len(reader.pages)
    selected_pages = st.multiselect(
        f"Select pages from '{special_pdf.name}' (Total: {num_pages})", list(range(1, num_pages + 1))
    )

# Upload PDFs
uploaded_pdfs = st.file_uploader("Upload PDFs", accept_multiple_files=True, type=["pdf"])

# Choose order of PDFs and images (excluding special PDF pages)
all_files = []

if uploaded_pdfs:
    all_files.extend([pdf.name for pdf in uploaded_pdfs])

# Default order is empty
reordered_files = st.multiselect("Choose final order of PDFs and images:", all_files, default=[])

if (selected_pages or reordered_files) and st.button("Convert and Download"):
    output_folder = "pdf_images"
    special_image_files = []
    normal_image_files = []
    
    # Start naming from 001
    image_index = 1

    # Process JPEGs first
    if uploaded_jpegs:
        jpeg_images, image_index = process_jpegs(uploaded_jpegs, output_folder, image_index)
        normal_image_files.extend(jpeg_images)

    # Process special PDF selected pages next
    if special_pdf and selected_pages:
        special_image_files, image_index = process_selected_pages(special_pdf_bytes, selected_pages, output_folder, image_index)

    # Process PDFs in the chosen order
    for item in reordered_files:
        for file in uploaded_pdfs:
            if file.name == item:
                images, image_index = process_pdfs([file], output_folder, image_index)
                normal_image_files.extend(images)

    # Create individual ZIP files
    special_zip = create_zip(special_image_files)
    normal_zip = create_zip(normal_image_files)

    # Combine both ZIPs into a final ZIP, ensuring special images come first
    final_zip_buffer = BytesIO()
    with zipfile.ZipFile(final_zip_buffer, "w", zipfile.ZIP_DEFLATED) as final_zip:
        # Add special PDF images first
        for image_path in special_image_files:
            final_zip.write(image_path, os.path.basename(image_path))
        # Then add normal images
        for image_path in normal_image_files:
            final_zip.write(image_path, os.path.basename(image_path))

    final_zip_buffer.seek(0)

    st.download_button("Download Final Merged ZIP", data=final_zip_buffer, file_name="final_combined_images.zip", mime="application/zip")

    shutil.rmtree("pdf_images")