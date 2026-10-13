"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Heart } from "lucide-react";
import type { Product } from "../../lib/catalog";
import { money } from "../../lib/catalog";
import { useCart } from "../../lib/CartContext";

function getCategoryFallback(cat: string) {
  const c = (cat || "").toLowerCase();
  if (c.includes("so-mi") || c.includes("sơ mi")) return "/products/v2/so-mi-oxford-classic.jpg";
  if (c.includes("ao-khoac") || c.includes("áo khoác")) return "/products/v2/ao-khoac-blazer-linen.jpg";
  if (c.includes("quan") || c.includes("quần")) return "/products/v2/quan-tay-pleated-wide-leg.jpg";
  if (c.includes("vay") || c.includes("váy") || c.includes("đầm")) return "/products/v2/chan-vay-chu-a-linen.jpg";
  return "/products/v2/ao-thun-essential.jpg";
}

export default function ProductCard({
  product,
  index,
}: {
  product: Product;
  index?: number;
}) {
  const { isWishlisted, toggleWishlist } = useCart();
  const favorite = isWishlisted(product.id);
  const fallback = getCategoryFallback(product.category || product.categoryName);
  const [imgSrc, setImgSrc] = useState(product.image || fallback);

  useEffect(() => {
    setImgSrc(product.image || getCategoryFallback(product.category || product.categoryName));
  }, [product.image, product.category, product.categoryName]);

  const stagger = index !== undefined ? index % 12 : 0;

  return (
    <article
      className="product-card"
      aria-label={`Sản phẩm ${product.name}`}
      style={{ "--stagger-index": stagger } as React.CSSProperties}
    >
      <div className="product-card-media">
        <Link href={`/products/${product.slug}`} className="product-card-image-link">
          <img
            src={imgSrc}
            alt={`${product.name}, màu ${product.color}`}
            loading="lazy"
            width="600"
            height="800"
            className="product-card-img"
            onError={() => {
              if (imgSrc !== fallback) {
                setImgSrc(fallback);
              }
            }}
          />
        </Link>

        {product.isNew && <span className="product-tag new-tag">Mới</span>}
        {product.isFeatured && !product.isNew && (
          <span className="product-tag featured-tag">Nổi bật</span>
        )}

        <button
          className={`shop-icon favorite-btn ${favorite ? "selected" : ""}`}
          aria-label={favorite ? `Bỏ lưu ${product.name}` : `Lưu ${product.name} vào yêu thích`}
          aria-pressed={favorite}
          onClick={(e) => {
            e.preventDefault();
            toggleWishlist(product.id);
          }}
        >
          <Heart size={18} fill={favorite ? "currentColor" : "none"} />
        </button>
      </div>

      <div className="product-card-body">
        <div className="product-card-meta">
          <span className="product-card-category">{product.categoryName}</span>
          <div className="product-card-colors" aria-label="Màu sắc có sẵn">
            {product.colors.map((c) => (
              <span
                key={c.name}
                className="color-dot"
                style={{ backgroundColor: c.hex }}
                title={c.name}
              />
            ))}
          </div>
        </div>

        <h3 className="product-card-title">
          <Link href={`/products/${product.slug}`}>{product.name}</Link>
        </h3>

        <div className="product-card-price-row">
          <div className="product-card-price">
            <strong>{money(product.price)}</strong>
            {product.originalPrice && (
              <span className="original-price">{money(product.originalPrice)}</span>
            )}
          </div>
          <span className="demo-price-tag">Giá thử nghiệm</span>
        </div>

        <div className="product-card-sizes" aria-label="Kích thước">
          {product.sizes.map((s) => (
            <span key={s} className="size-badge">
              {s}
            </span>
          ))}
        </div>
      </div>
    </article>
  );
}
