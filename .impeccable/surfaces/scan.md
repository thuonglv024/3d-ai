# Surface: Standalone `/scan` Studio

## Role
The standalone `/scan` route is the dedicated dark measurement studio (`#141312`) for capturing two-view webcam photos (`upper_body` by default, `full_body` optional), inspecting the reconstructed 3D MakeHuman mesh, reviewing measurement source badges (`photo_estimate`, `photo_with_prior`, `template_model`, `user_input`, `unavailable`), and saving scans to the user's account history.

## Design Rules
- Read [`DESIGN.md`](file:///d:/MORPH-AI/DESIGN.md), [`PRODUCT.md`](file:///d:/MORPH-AI/PRODUCT.md), and [`docs/SCAN_QUALITY.md`](file:///d:/MORPH-AI/docs/SCAN_QUALITY.md).
- Camera-only capture: never display file upload inputs or pre-scan sample mannequins.
- Keep the live webcam viewport unobstructed while capturing; display clear pose-framing overlays and countdown indicators.
- Maintain honest Vietnamese copy that distinguishes photo-derived upper-body measurements from template or manual lower-body measurements.
