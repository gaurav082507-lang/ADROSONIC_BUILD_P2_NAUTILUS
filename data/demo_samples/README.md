# Lucen AI Demo Samples

This directory contains evaluation and test samples designed for verifying the Image Pipeline detectors and forensic analysis.

| Filename | Description | Characteristics & Expected Flags |
|---|---|---|
| `01_ai_generated_car_damage.jpg` | Synthetic vehicle damage rendering | Software tag names `Midjourney v6.0` (`IMG-EXIF-02a`), lack of sensor EXIF (`IMG-EXIF-01`), high AI likelihood (`IMG-AI-01`), band: **HIGH**. |
| `02_genuine_phone_photo.jpg` | Authentic smartphone capture | Clean camera EXIF (`Apple iPhone 14 Pro`, `DateTimeOriginal`), uniform noise distribution, low ELA delta, band: **LOW**. |
| `03_edited_spliced_photo.jpg` | Tampered composite image | Spliced foreign patch resulting in significant compression inconsistency (`IMG-ELA-01`), localized bounding box, `Adobe Photoshop 2024` in EXIF (`IMG-EXIF-02b`), band: **MEDIUM / HIGH**. |
| `04_low_res_compressed.jpg` | Heavily degraded input | Short side 240 px (< 512 px), low JPEG quality (q=30 < 50), high blur. Triggers `IMG-QUAL-01` warning and gates detector weights. |

All images are programmatically generated and free of third-party copyright restrictions.
