"use client";

import type { Product } from "../../lib/catalog";

/**
 * The try-on "wardrobe" column: 1:1 thumbnails, product name, and the size
 * being tried. Selecting another item is only possible when the parent owns the
 * product state (standalone /scan); embedded in a product page the list is
 * read-only, because changing the garment there would desync the page.
 */
export default function TryOnWardrobe({
  products,
  selectedId,
  size,
  onSelect,
}: {
  products: Product[];
  selectedId: string;
  size: string;
  onSelect?: (product: Product) => void;
}) {
  return (
    <aside className="tryon-wardrobe" aria-label="Tủ đồ">
      <div className="tryon-panel-head">
        <strong>Tủ đồ</strong>
        <small>{products.length} món</small>
      </div>
      <div className="tryon-wardrobe-list">
        {products.map((product) => {
          const selected = product.id === selectedId || product.slug === selectedId;
          const sizeLabel = selected
            ? size || "Chưa chọn size"
            : `Size ${product.sizes[0]}–${product.sizes[product.sizes.length - 1]}`;
          return (
            <button
              key={product.id}
              type="button"
              className={selected ? "selected" : ""}
              onClick={() => onSelect?.(product)}
              disabled={!onSelect}
              title={onSelect ? `Thử ${product.name}` : "Mở phòng thử đồ độc lập để đổi sản phẩm"}
              aria-pressed={selected}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={product.image} alt="" width={44} height={44} loading="lazy" />
              <span>
                <b>{product.name}</b>
                <small>{sizeLabel}</small>
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
