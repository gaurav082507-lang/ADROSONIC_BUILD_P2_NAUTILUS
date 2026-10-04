# Real Edits Evaluation Dataset (Test Only)

This folder is reserved for real-world, hand-tampered evaluation documents to validate Lucen AI's document forensics pipeline against genuine human manipulation.

### Instructions:
1. Add **20 hand-tampered documents** (PDFs or high-resolution document scans/photos) into this directory.
2. For each document, include realistic modifications such as:
   - Altered invoice line item amounts and totals
   - Retyped or spliced hospital bills with modified discharge dates/costs
   - Spliced policy numbers or altered Aadhaar/PAN identity numbers
   - Modified motor insurance repair estimate quotations
3. Accompany each file with an optional `{filename}.json` describing the ground truth:
   ```json
   {
     "filename": "sample_01.pdf",
     "tampered": true,
     "recipes": ["digit_replacement", "font_inconsistency"],
     "regions": [{"page": 1, "field": "total_amount", "bbox": [0.65, 0.72, 0.25, 0.05]}],
     "expected_rules": ["DOC-LOGIC-01", "DOC-FONT-01"]
   }
   ```
4. **Note**: This dataset is strictly for **test and benchmark evaluation only** — never include these samples in the training set.
