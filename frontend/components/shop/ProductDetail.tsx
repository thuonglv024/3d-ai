"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Heart,
  Minus,
  Plus,
  ScanLine,
  ShieldCheck,
  ShoppingBag,
  Sparkles,
  X,
} from "lucide-react";
import type { Product } from "../../lib/catalog";
import { getRelatedProducts, money } from "../../lib/catalog";
import { fetchProducts } from "../../lib/catalogApi";
import { useCart } from "../../lib/CartContext";
import { useScan, type SizeAdviceResult } from "../../lib/ScanContext";
import Header from "./Header";
import Footer from "./Footer";
import ProductCard from "./ProductCard";
import WishlistDrawer from "./WishlistDrawer";
import Modal from "./Modal";
import SizeChartModal from "./SizeChartModal";

const FitExperience = dynamic(() => import("./FitExperience"), {
  ssr: false,
  loading: () => <div className="fit-lazy">Đang mở phòng tìm size…</div>,
});

function getCategoryFallback(cat: string) {
  const c = (cat || "").toLowerCase();
  if (c.includes("so-mi") || c.includes("sơ mi")) return "/products/v2/so-mi-oxford-classic.jpg";
  if (c.includes("ao-khoac") || c.includes("áo khoác")) return "/products/v2/ao-khoac-blazer-linen.jpg";
  if (c.includes("quan") || c.includes("quần")) return "/products/v2/quan-tay-pleated-wide-leg.jpg";
  if (c.includes("vay") || c.includes("váy") || c.includes("đầm")) return "/products/v2/chan-vay-chu-a-linen.jpg";
  return "/products/v2/ao-thun-essential.jpg";
}

export default function ProductDetail({ product }: { product: Product }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addToCart, isWishlisted, toggleWishlist } = useCart();
  const { job, fetchAdviceForProduct, appliedSizes, applySizeToProduct } = useScan();

  const [selectedColor, setSelectedColor] = useState(product.color || product.colors[0]?.name || "");
  const [selectedSize, setSelectedSize] = useState(() => {
    const qSize = searchParams?.get("size");
    if (qSize && product.sizes.includes(qSize)) return qSize;
    const aSize = appliedSizes[product.id];
    if (aSize && product.sizes.includes(aSize)) return aSize;
    return "";
  });
  const [selectedImage, setSelectedImage] = useState(product.image);

  const galleryImages = useMemo(() => {
    if (Array.isArray(product.gallery) && product.gallery.length > 0) {
      return [...product.gallery];
    }
    return [product.image];
  }, [product.gallery, product.image]);
  const [quantity, setQuantity] = useState(1);
  const [message, setMessage] = useState("");
  const [addedFeedback, setAddedFeedback] = useState<{
    productName: string;
    size: string;
    color: string;
    quantity: number;
  } | null>(null);

  const [chartOpen, setChartOpen] = useState(false);
  const [fitOpen, setFitOpen] = useState(false);

  // Auto-dismiss add-to-cart toast after 6 seconds
  useEffect(() => {
    if (!addedFeedback) return;
    const timer = setTimeout(() => {
      setAddedFeedback(null);
    }, 6000);
    return () => clearTimeout(timer);
  }, [addedFeedback]);

  // Dynamic size advice from active scan session if available
  const [advice, setAdvice] = useState<SizeAdviceResult | null>(null);
  const [adviceLoading, setAdviceLoading] = useState(false);

  const favorite = isWishlisted(product.id);
  const [relatedProducts, setRelatedProducts] = useState<Product[]>([]);

  // Fetch actual related products from current catalog data
  useEffect(() => {
    let active = true;
    fetchProducts({ category: product.category, limit: 12 })
      .then((res) => {
        if (!active) return;
        const matches = res.items.filter((p) => p.id !== product.id && p.slug !== product.slug);
        if (matches.length < 4) {
          fetchProducts({ limit: 12 }).then((allRes) => {
            if (!active) return;
            const filler = allRes.items.filter(
              (p) => p.id !== product.id && p.slug !== product.slug && !matches.some((m) => m.id === p.id)
            );
            setRelatedProducts([...matches, ...filler].slice(0, 4));
          });
        } else {
          setRelatedProducts(matches.slice(0, 4));
        }
      })
      .catch(() => {
        if (active) {
          setRelatedProducts(getRelatedProducts(product.id, 4));
        }
      });

    return () => {
      active = false;
    };
  }, [product.id, product.category, product.slug]);

  // Reset selection state when product changes to avoid carrying over wrong attributes
  useEffect(() => {
    const qSize = searchParams?.get("size");
    const validQ = qSize && product.sizes.includes(qSize) ? qSize : "";
    const validA = appliedSizes[product.id] && product.sizes.includes(appliedSizes[product.id]) ? appliedSizes[product.id] : "";

    setSelectedColor(product.color || product.colors[0]?.name || "");
    setSelectedSize(validQ || validA || "");
    setSelectedImage(product.image);
    setQuantity(1);
    setMessage("");
    setAddedFeedback(null);
    setChartOpen(false);
    setFitOpen(false);
  }, [product.id]);

  // Validate URL size parameter: only accept sizes belonging to this product
  useEffect(() => {
    const querySize = searchParams?.get("size");
    if (querySize) {
      if (product.sizes.includes(querySize)) {
        setSelectedSize(querySize);
        applySizeToProduct(product.id, querySize);
      } else {
        // Query size is invalid for this product
        setSelectedSize((prev) => (product.sizes.includes(prev) ? prev : ""));
      }
    } else if (appliedSizes[product.id] && product.sizes.includes(appliedSizes[product.id])) {
      setSelectedSize(appliedSizes[product.id]);
    }
  }, [searchParams, appliedSizes, product.id, product.sizes, applySizeToProduct]);

  // Fetch advice if scan session is active (requires explicit user action to select/apply)
  useEffect(() => {
    if (!job || job.status !== "completed") {
      setAdvice(null);
      return;
    }
    let active = true;
    setAdviceLoading(true);

    fetchAdviceForProduct(product)
      .then((res) => {
        if (active) {
          setAdvice(res);
        }
      })
      .catch((err) => {
        if (active) {
          setAdvice(null);
        }
      })
      .finally(() => {
        if (active) setAdviceLoading(false);
      });

    return () => {
      active = false;
    };
  }, [job?.id, job?.status, product.id, fetchAdviceForProduct]);

  // Explicit user action to add to cart
  const handleAddToCart = () => {
    if (!selectedSize || !product.sizes.includes(selectedSize)) {
      setMessage("Vui lòng chọn một size hợp lệ trước khi thêm vào giỏ.");
      setAddedFeedback(null);
      return;
    }
    setMessage("");
    addToCart(
      {
        productId: product.id,
        productSlug: product.slug,
        name: product.name,
        price: product.price,
        color: selectedColor,
        size: selectedSize,
        image: selectedImage || product.image,
      },
      quantity,
      false
    );
    setAddedFeedback({
      productName: product.name,
      size: selectedSize,
      color: selectedColor,
      quantity,
    });
  };

  const handleApplySizeFromScan = (sizeToApply: string) => {
    if (product.sizes.includes(sizeToApply)) {
      setSelectedSize(sizeToApply);
      applySizeToProduct(product.id, sizeToApply);
      setMessage(`Đã áp dụng size ${sizeToApply} theo gợi ý hình thể của bạn.`);
    }
    setFitOpen(false);
  };

  const handleOpenSizeChartFromScan = () => {
    setFitOpen(false);
    setChartOpen(true);
  };

  const handleOpenScanFromChart = () => {
    setChartOpen(false);
    setFitOpen(true);
  };

  return (
    <div className="storefront">
      <Header />

      <main className="shop-main product-detail-main">
        {/* Breadcrumb Navigation */}
        <nav className="shop-breadcrumb" aria-label="Điều hướng phân cấp">
          <Link href="/">Trang chủ</Link>
          <span>/</span>
          <Link href={`/?category=${product.category}#catalog`}>{product.categoryName}</Link>
          <span>/</span>
          <span className="current-crumb">{product.name}</span>
        </nav>

        {/* Product Layout Grid */}
        <div className="product-layout">
          {/* Left: Gallery */}
          <div className="product-gallery">
            <div className="product-photo">
              <img
                key={selectedImage}
                src={selectedImage}
                alt={selectedColor === product.color ? `${product.name} - ${product.color}` : `${product.name} (Ảnh minh họa màu gốc: ${product.color})`}
                width="900"
                height="1200"
                fetchPriority="high"
                className="main-detail-img"
                onError={(e) => {
                  const fb = getCategoryFallback(product.category || product.categoryName);
                  if (!e.currentTarget.src.endsWith(fb)) {
                    e.currentTarget.src = fb;
                  }
                }}
              />
              <span className="product-photo-tag">{product.categoryName} · Thử nghiệm</span>
              <button
                className={`shop-icon favorite ${favorite ? "selected" : ""}`}
                aria-label={favorite ? "Bỏ lưu sản phẩm" : "Lưu sản phẩm yêu thích"}
                aria-pressed={favorite}
                onClick={() => toggleWishlist(product.id)}
              >
                <Heart size={20} fill={favorite ? "currentColor" : "none"} />
              </button>
            </div>

            {/* Gallery Thumbnails */}
            {galleryImages.length > 1 && (
              <div className="gallery-thumbnails" role="group" aria-label="Hình ảnh chi tiết">
                {galleryImages.map((img, idx) => {
                  const isDetail = img.includes("-detail");
                  const label = idx === 0 ? "Ảnh chính" : isDetail ? "Ảnh phóng to chi tiết" : "Ảnh phóng to chi tiết";
                  return (
                    <button
                      key={img}
                      type="button"
                      className={`thumb-btn ${selectedImage === img ? "active" : ""}`}
                      onClick={() => setSelectedImage(img)}
                      aria-label={label}
                      title={label}
                    >
                      <img
                        src={img}
                        alt={label}
                        width="72"
                        height="96"
                        onError={(e) => {
                          const fb = getCategoryFallback(product.category || product.categoryName);
                          if (!e.currentTarget.src.endsWith(fb)) {
                            e.currentTarget.src = fb;
                          }
                        }}
                      />
                    </button>
                  );
                })}
              </div>
            )}

            <p className="product-image-note">
              Ảnh sản phẩm thử nghiệm cho trải nghiệm số đo hình thể 3D.
            </p>
          </div>

          {/* Right: Product Info & Actions */}
          <section className="product-info" aria-label="Thông tin sản phẩm">
            <span className="detail-category-badge">{product.categoryName}</span>
            <h1>{product.name}</h1>
            <p className="product-subtitle">{product.subtitle}</p>

            <div className="product-price">
              {money(product.price)}
              {product.originalPrice && (
                <span className="original-price">{money(product.originalPrice)}</span>
              )}
              <span>Giá thử nghiệm</span>
            </div>

            <div className="product-stock-badge in-stock" role="status" aria-label="Tình trạng kho hàng">
              <span className="stock-indicator-dot" />
              <span>Còn hàng · Sẵn sàng đóng gói và giao hàng</span>
            </div>

            <div className="product-divider" />

            {/* Color Selector */}
            <div className="product-color-selector">
              <div className="color-label-row">
                <span>
                  Màu sắc: <strong>{selectedColor}</strong>
                  {selectedColor !== product.color && (
                    <small style={{ color: "var(--text-secondary)", marginLeft: 8, fontSize: "12px" }}>
                      (Ảnh hiển thị màu gốc: {product.color})
                    </small>
                  )}
                </span>
              </div>
              <div className="color-swatches-group" role="radiogroup" aria-label="Chọn màu sắc">
                {product.colors.map((c) => {
                  const isSelected = selectedColor === c.name;
                  return (
                    <button
                      key={c.name}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      aria-label={c.name}
                      className={`color-swatch-item ${isSelected ? "selected" : ""}`}
                      onClick={() => setSelectedColor(c.name)}
                      style={{ backgroundColor: c.hex }}
                    >
                      {isSelected && (
                        <Check
                          size={14}
                          color={["#ffffff", "#fcfbf7", "#f4f1ea", "#f0ece1", "#ded6c4"].includes(c.hex) ? "#194e3d" : "#ffffff"}
                        />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Size Selector */}
            <div className="size-selector-section">
              <div className="size-heading">
                <span>
                  Kích thước{selectedSize && <strong> · {selectedSize}</strong>}
                </span>
                <button
                  type="button"
                  className="shop-inline size-chart-btn"
                  onClick={() => setChartOpen(true)}
                >
                  Bảng size chi tiết
                </button>
              </div>

              {/* Recommended size highlight badge from scan advice */}
              {advice?.candidates && advice.candidates.length > 0 && (
                <div className="product-recommended-size-badge" role="status">
                  <Sparkles size={14} className="rec-sparkle-icon" />
                  <span>
                    Size gợi ý cho bạn: <strong>Size {advice.candidates.join(", ")}</strong>
                  </span>
                </div>
              )}

              <div className="product-sizes" role="group" aria-label="Chọn kích thước">
                {product.sizes.map((s) => {
                  const isSelected = selectedSize === s;
                  const isRecommended = advice?.candidates?.includes(s);
                  return (
                    <button
                      key={s}
                      type="button"
                      aria-label={`Size ${s}${isRecommended ? " (Gợi ý cho bạn)" : ""}`}
                      className={`${isSelected ? "selected" : ""} ${isRecommended ? "recommended" : ""}`}
                      aria-pressed={isSelected}
                      onClick={() => {
                        setSelectedSize(s);
                        applySizeToProduct(product.id, s);
                        if (isRecommended) {
                          setMessage(`Đã chọn size ${s} (gợi ý theo hình thể của bạn).`);
                        } else {
                          setMessage("");
                        }
                        setAddedFeedback(null);
                      }}
                    >
                      {s}
                      {isRecommended && (
                        <span className="recommended-dot" title="Kích thước phù hợp với hình thể của bạn" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Fit Studio Entry Card */}
            <div className="product-fit-banner">
              <button
                type="button"
                className="fit-entry"
                onClick={() => setFitOpen(true)}
              >
                <span className="fit-entry-icon">
                  <ScanLine size={24} />
                </span>
                <span className="fit-entry-text">
                  <strong>
                    {advice?.candidates?.length
                      ? `MORPH AI gợi ý: Size ${advice.candidates.join(", ")}`
                      : advice?.status === "insufficient_measurements"
                      ? "Chưa đủ dữ liệu để gợi ý (cần số đo vòng mông)"
                      : job?.status === "completed"
                      ? "Xem lại hình thể 3D & gợi ý size"
                      : "Bạn chưa chắc về size?"}
                  </strong>
                  <small>
                    {advice?.candidates?.length
                      ? "Bấm để xem tương tác mô hình 3D và số đo của bạn"
                      : advice?.status === "insufficient_measurements"
                      ? "Webcam thân trên chưa đo vòng mông cho sản phẩm này"
                      : job?.status === "completed"
                      ? "Đối chiếu hình thể của bạn với bảng size sản phẩm"
                      : "Tìm size của tôi với MORPH AI bằng webcam 2 góc"}
                  </small>
                </span>
                <ArrowRight size={20} />
              </button>
            </div>

            {/* Quantity and Add to Cart Row */}
            <div className="purchase-actions-row">
              <div className="qty-picker">
                <button
                  type="button"
                  aria-label="Giảm số lượng"
                  disabled={quantity <= 1}
                  onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                >
                  <Minus size={15} />
                </button>
                <span>{quantity}</span>
                <button
                  type="button"
                  aria-label="Tăng số lượng"
                  disabled={quantity >= 10}
                  onClick={() => setQuantity((q) => Math.min(10, q + 1))}
                >
                  <Plus size={15} />
                </button>
              </div>

              <button
                type="button"
                className="shop-primary add-to-cart-btn"
                onClick={handleAddToCart}
              >
                <ShoppingBag size={18} />
                Thêm vào giỏ
                <ArrowRight size={18} />
              </button>
            </div>

            {message && (
              <p className="product-message" role="alert">
                {message}
              </p>
            )}

            <p className="product-context">
              <ShieldCheck size={16} />
              Chọn size thủ công hoặc đối chiếu trực tiếp với avatar 3D của bạn.
            </p>

            {/* Collapsible Details */}
            <div className="product-collapsibles">
              <details className="product-detail" open>
                <summary>
                  Chất liệu & Cấu tạo
                  <Plus size={16} />
                </summary>
                <p>{product.material}</p>
                <ul className="detail-bullets">
                  {product.details.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </details>

              <details className="product-detail">
                <summary>
                  Phom dáng & Thiết kế
                  <Plus size={16} />
                </summary>
                <p>{product.fit}</p>
                <p>{product.description}</p>
              </details>

              <details className="product-detail">
                <summary>
                  Lưu ý thử nghiệm
                  <Plus size={16} />
                </summary>
                <p>
                  Sản phẩm, giá bán và bảng size là dữ liệu thử nghiệm trong MORPH Studio. Giỏ hàng chỉ lưu trữ trên trình duyệt của bạn. Chưa tích hợp hệ thống thanh toán hoặc đặt hàng thật.
                </p>
              </details>
            </div>
          </section>
        </div>

        {/* Related Products Section */}
        {relatedProducts.length > 0 && (
          <section className="related-products-section">
            <div className="section-title-row">
              <h2>Có thể bạn cũng thích</h2>
              <Link href={`/?category=${product.category}#catalog`} className="shop-inline">
                Xem thêm trong danh mục {product.categoryName} →
              </Link>
            </div>
            <div className="product-grid related-grid">
              {relatedProducts.map((p, idx) => (
                <ProductCard key={p.id} product={p} index={idx} />
              ))}
            </div>
          </section>
        )}
      </main>

      <Footer />

      {/* Floating Add to Cart Confirmation Toast */}
      {addedFeedback && (
        <aside className="commerce-toast commerce-toast-success" role="status" aria-live="polite">
          <div className="toast-icon-wrap">
            <Check size={18} />
          </div>
          <div className="toast-body">
            <p className="toast-title">Đã thêm vào giỏ hàng</p>
            <p className="toast-desc">
              Đã thêm <strong>{addedFeedback.productName}</strong> - Size <strong>{addedFeedback.size}</strong> vào giỏ hàng.
            </p>
          </div>
          <div className="toast-actions">
            <Link href="/cart" className="toast-view-cart-btn">
              Xem giỏ hàng →
            </Link>
            <button
              type="button"
              className="toast-close-btn"
              aria-label="Đóng thông báo"
              onClick={() => setAddedFeedback(null)}
            >
              <X size={16} />
            </button>
          </div>
        </aside>
      )}

      {/* Wishlist Drawer */}
      <WishlistDrawer />

      {/* Size Chart Modal */}
      <SizeChartModal
        product={product}
        open={chartOpen}
        onClose={() => setChartOpen(false)}
        onOpenScan={handleOpenScanFromChart}
      />

      {/* Fit Studio Modal */}
      <Modal
        open={fitOpen}
        onClose={() => setFitOpen(false)}
        title={`Tìm size của tôi · ${product.name}`}
        wide
      >
        {fitOpen && (
          <FitExperience
            product={product}
            active={fitOpen}
            onSelectSize={handleApplySizeFromScan}
            onOpenSizeChart={handleOpenSizeChartFromScan}
            onClose={() => setFitOpen(false)}
          />
        )}
      </Modal>
    </div>
  );
}
