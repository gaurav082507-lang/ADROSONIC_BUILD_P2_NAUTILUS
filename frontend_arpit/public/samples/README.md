# Lucen sample inputs

These are **provisional placeholder binaries** so the UI can exercise the real upload path before the backend's demo samples are copied here.

Replace them with the backend's actual `data/demo_samples` files, preserving the exact filenames and MIME types:

- `ai_car.jpg`
- `genuine_car.jpg`
- `tampered_invoice.pdf`
- `clean_invoice.pdf`
- `id_card.png`
- `selfie.jpg`

The sample buttons fetch these files as `File` objects and submit them through the same API endpoints as user uploads. No filename-based outcome logic exists in the frontend.
