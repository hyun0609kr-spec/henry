# PDF Form Filling Guide

You MUST complete these steps in order. Do not skip ahead to writing code.

## Step 1: Check for Fillable Form Fields

First, determine whether the PDF has native fillable form fields:

```bash
python scripts/check_fillable_fields.py <file.pdf>
```

Based on the result, follow Path 1 or Path 2 below.

---

## Path 1: Fillable Form Fields

Use this path if the PDF has native fillable form fields.

### Step 1a: Extract Field Information

```bash
python scripts/extract_form_field_info.py <input.pdf> <field_info.json>
```

This generates a JSON file containing field IDs, page numbers, bounding boxes, and field types (text, checkbox, radio_group, choice).

### Step 1b: Convert PDF to Images

```bash
python scripts/convert_pdf_to_images.py <file.pdf> <output_directory>
```

Use the images for visual analysis to understand the form layout.

### Step 1c: Create field_values.json

Create a JSON file mapping each `field_id` to its intended value. Include `description` and `page` for each field:

```json
[
  {
    "field_id": "FirstName",
    "description": "First name of applicant",
    "page": 1,
    "value": "John"
  },
  {
    "field_id": "Agreement",
    "description": "Agreement checkbox",
    "page": 2,
    "value": "/Yes"
  }
]
```

### Step 1d: Fill the Form

```bash
python scripts/fill_fillable_fields.py <input.pdf> <field_values.json> <output.pdf>
```

---

## Path 2: Non-Fillable Form Fields

Use this path if the PDF does not have native fillable form fields. Text will be added as annotations at specified coordinates.

### Approach A: Structure-Based Coordinates (Preferred)

Use this approach when the PDF has selectable text elements.

#### Step 2a: Extract Form Structure

```bash
python scripts/extract_form_structure.py <input.pdf> form_structure.json
```

This extracts text labels, horizontal lines, and checkboxes with precise PDF coordinates.

#### Step 2b: Analyze Structure

Review `form_structure.json` to identify field locations. Use the labels, lines, and row boundaries to determine where to place text entries.

If meaningful text elements are detected, proceed with structure-based coordinates. Otherwise, fall back to Approach B.

### Approach B: Visual Estimation (Fallback)

Use this approach for scanned PDFs where structure extraction does not detect meaningful text.

#### Step 2b-1: Convert PDF to Images

```bash
python scripts/convert_pdf_to_images.py <input.pdf> <output_directory>
```

#### Step 2b-2: Identify Coordinates Visually

Use zoom and cropping tools (e.g., ImageMagick) to precisely determine pixel coordinates of each form field:

```bash
# Crop a region to inspect coordinates
convert page_1.png -crop 200x50+100+300 cropped_region.png
```

Refine coordinates iteratively until they are accurate.

### Hybrid Approach

Combine structure extraction for detected fields with visual estimation for missed elements. Convert all coordinates to a single coordinate system before filling.

---

## Step 3: Create fields.json for Annotation-Based Filling

For non-fillable forms, create a `fields.json` file describing the annotations to add:

```json
{
  "pages": [
    {
      "page_number": 1,
      "pdf_width": 612,
      "pdf_height": 792
    }
  ],
  "form_fields": [
    {
      "description": "First name",
      "page_number": 1,
      "label_bounding_box": [50, 100, 150, 115],
      "entry_bounding_box": [160, 100, 350, 115],
      "entry_text": {
        "text": "John",
        "font": "Arial",
        "font_size": 11,
        "font_color": "000000"
      }
    }
  ]
}
```

**Coordinate system:**
- When using structure-based extraction, coordinates are in PDF units (origin at bottom-left). Include `pdf_width` and `pdf_height` in the page info.
- When using visual estimation from images, coordinates are in image pixels (origin at top-left). Include `image_width` and `image_height` in the page info instead.

---

## Step 4: Validate Bounding Boxes

Always validate bounding boxes before filling:

```bash
python scripts/check_bounding_boxes.py fields.json
```

Fix any reported intersections or sizing issues before proceeding.

---

## Step 5: Fill the Form

```bash
python scripts/fill_pdf_form_with_annotations.py <input.pdf> fields.json <output.pdf>
```

---

## Step 6: Verify Results

Convert the output PDF to images and visually verify that all fields are filled correctly:

```bash
python scripts/convert_pdf_to_images.py <output.pdf> <verification_directory>
```

To create a validation image with bounding boxes overlaid:

```bash
python scripts/create_validation_image.py <page_number> fields.json <page_image.png> <validation_output.png>
```

Red boxes show entry bounding boxes; blue boxes show label bounding boxes.
