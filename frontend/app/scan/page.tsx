"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Check } from "lucide-react";
import FitExperience from "../../components/shop/FitExperience";
import { essential, type Product } from "../../lib/catalog";
import ProductPickerPopover from "../../components/shop/ProductPickerPopover";

export default function Page() {
  const [selectedProduct, setSelectedProduct] = useState<Product>(essential);
  const [size, setSize] = useState("");

  const handleSelectProduct = (prod: Product) => {
    setSelectedProduct(prod);
    setSize("");
  };

  return (
    <main className="storefront scan-standalone">
      <header className="shop-header">
        <Link href="/" className="shop-logo" aria-label="MORPH Studio trang chủ">
          MORPH<span>STUDIO</span>
        </Link>

        <div className="scan-product-picker">
          <ProductPickerPopover
            selectedProduct={selectedProduct}
            onSelectProduct={handleSelectProduct}
          />
        </div>

        <Link href="/" className="scan-back-link">
          <ArrowLeft size={16} /> Về trang mua sắm
        </Link>
      </header>

      {size && (
        <div className="standalone-choice" role="status">
          <span>
            <Check size={16} /> Bạn đã chọn size <strong>{size}</strong> cho{" "}
            <strong>{selectedProduct.name}</strong>.
          </span>
          <Link href={`/products/${selectedProduct.slug}?size=${size}`}>
            Xem chi tiết sản phẩm này →
          </Link>
        </div>
      )}

      <FitExperience
        product={selectedProduct}
        active
        onSelectSize={setSize}
      />
    </main>
  );
}
