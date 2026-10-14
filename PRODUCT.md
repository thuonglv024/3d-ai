# MORPH AI Product Context

## Product Summary

MORPH AI is a local Vietnamese fashion storefront and 3D size-recommendation demo. The product combines a curated 160-product storefront (`/`), product detail pages (`/products/[id]`) with an embedded webcam size finder, a standalone 3D fitting studio (`/scan`), a local cart and wishlist drawer, atomic order placement (`/checkout`, `/orders/[id]`), and user accounts with saved scan history and manual body profiles (`/account`, `/account/body-profile`).

## Primary Audience

Vietnamese online clothing shoppers who want a calmer, clearer answer to "Will this size fit me?" before adding an item to their cart, as well as developers/evaluators testing two-photo webcam body reconstruction and size recommendation.

## Core User Jobs

1. Browse a 160-item men's and women's fashion catalog (`/`), filter by gender/category/price/search, manage a wishlist, and open a product detail page (`/products/[id]`).
2. Launch **"Tìm Cỡ Vừa Vặn & Quét 3D"** from the product page (or open `/scan` directly), enter height, weight, and gender, and capture front + 90° side poses via live webcam (`upper_body` default or `full_body` optional) to receive a recommended size, fit confidence, 3D mannequin preview, and measurement table with explicit source badges.
3. Supplement lower-body measurements (`hip_cm`, `inseam_cm`) via the manual body profile when using `upper_body` capture so trousers, skirts, and one-piece dresses can still be sized accurately.
4. Select the recommended size, add items to the cart, complete local checkout (`/checkout`) with atomic stock deduction, and view order details (`/orders/[id]`) or track measurement history on `/account`.

## Current Technical Reality

- The 3D engine uses **MediaPipe Pose & Selfie Segmentation**, a **3-tier mathematical calibration pipeline** (`estimate_upper_body_height`, `camera_fusion`, `ANATOMICAL_SECTION_FACTORS`), and **MakeHuman base mesh deformation** (PCHIP slice scaling).
- It is **not** SAM 3D Body or MHR, does not reconstruct personal face/hair identity, and has not yet been clinically validated against a real-human tape-measurement cohort.
- Every measurement carries an explicit `source` (`photo_estimate`, `photo_with_prior`, `template_model`, `user_input`, `unavailable`), `confidence`, and `valid_for_tracking` flag.
- Authentication uses an `HttpOnly` session cookie (`morph_session`) stored as a `SHA-256` hash in local SQLite (`backend/runtime/catalog.db`). No external e-commerce SaaS platform or live third-party payment gateway is connected.

## Tone And Brand

Calm luxury editorial storefront paired with an honest, non-clinical fitting studio. Warm Ivory (`#FAF7F2`), Alabaster (`#F3EFE6`), Espresso Ink (`#181512`), and Champagne Gold (`#C5A059` / `#8A6621`) lead the storefront experience, transitioning into a focused Dark Studio (`#141312`) for the camera and 3D measurement workspace. Copy must be natural Vietnamese with full diacritics, specific about what is estimated from photos vs. template priors vs. user input, and free of exaggerated AI accuracy claims.
