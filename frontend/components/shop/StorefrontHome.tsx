"use client";

import { useEffect, useState, useTransition, Suspense, useRef } from "react";
import dynamic from "next/dynamic";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowDown,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  ScanLine,
  Sparkles,
} from "lucide-react";
import { type Product, essential } from "../../lib/catalog";
import { fetchProducts, type PaginatedProducts } from "../../lib/catalogApi";
import Header from "./Header";
import Footer from "./Footer";
import ProductCard from "./ProductCard";
import ProductFilter, { type FilterState } from "./ProductFilter";
import CartDrawer from "./CartDrawer";
import WishlistDrawer from "./WishlistDrawer";
import Modal from "./Modal";
import { useScan } from "../../lib/ScanContext";

const FitExperience = dynamic(() => import("./FitExperience"), {
  ssr: false,
  loading: () => <div className="fit-lazy">Đang mở phòng tìm size…</div>,
});

const PAGE_SIZE = 24;

function ProductGridSkeleton({ count = 8 }: { count?: number }) {
  return (
    <div className="product-grid" aria-busy="true" aria-label="Đang tải sản phẩm...">
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="product-card skeleton-card">
          <div className="product-card-media skeleton-media">
            <div className="skeleton-shimmer" />
          </div>
          <div className="product-card-body skeleton-body">
            <div className="skeleton-line skeleton-meta" />
            <div className="skeleton-line skeleton-title" />
            <div className="skeleton-line skeleton-price" />
            <div className="skeleton-line skeleton-sizes" />
          </div>
        </div>
      ))}
    </div>
  );
}

function PaginationControls({
  currentPage,
  totalPages,
  total,
  limit,
  onPageChange,
}: {
  currentPage: number;
  totalPages: number;
  total: number;
  limit: number;
  onPageChange: (page: number) => void;
}) {
  const start = total === 0 ? 0 : (currentPage - 1) * limit + 1;
  const end = Math.min(total, currentPage * limit);

  // Generate page numbers with ellipsis
  const pages: (number | "ellipsis")[] = [];
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (currentPage > 3) pages.push("ellipsis");
    const startPage = Math.max(2, currentPage - 1);
    const endPage = Math.min(totalPages - 1, currentPage + 1);
    for (let i = startPage; i <= endPage; i++) {
      if (!pages.includes(i)) pages.push(i);
    }
    if (currentPage < totalPages - 2) pages.push("ellipsis");
    if (!pages.includes(totalPages)) pages.push(totalPages);
  }

  return (
    <div className="catalog-pagination-wrap" aria-label="Điều hướng phân trang sản phẩm">
      <div className="pagination-status" role="status">
        Hiển thị <strong>{start}</strong> – <strong>{end}</strong> trong <strong>{total}</strong> sản phẩm
      </div>

      {totalPages > 1 && (
        <nav className="pagination-controls" aria-label="Danh sách trang">
          <button
            type="button"
            className="pagination-btn pagination-nav-btn prev-btn"
            disabled={currentPage <= 1}
            onClick={() => onPageChange(currentPage - 1)}
            aria-label="Về trang trước"
          >
            <ChevronLeft size={16} />
            <span>Trước</span>
          </button>

          <div className="pagination-pages">
            {pages.map((p, idx) =>
              p === "ellipsis" ? (
                <span key={`ellipsis-${idx}`} className="pagination-ellipsis" aria-hidden="true">
                  …
                </span>
              ) : (
                <button
                  key={p}
                  type="button"
                  className={`pagination-btn page-num-btn ${p === currentPage ? "active" : ""}`}
                  aria-current={p === currentPage ? "page" : undefined}
                  aria-label={`Trang ${p}`}
                  onClick={() => onPageChange(p)}
                >
                  {p}
                </button>
              )
            )}
          </div>

          <button
            type="button"
            className="pagination-btn pagination-nav-btn next-btn"
            disabled={currentPage >= totalPages}
            onClick={() => onPageChange(currentPage + 1)}
            aria-label="Sang trang sau"
          >
            <span>Sau</span>
            <ChevronRight size={16} />
          </button>
        </nav>
      )}
    </div>
  );
}

function StorefrontHomeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { job } = useScan();
  const [, startTransition] = useTransition();

  // Page state
  const [currentPage, setCurrentPage] = useState<number>(() => {
    const p = Number(searchParams?.get("page"));
    return Number.isFinite(p) && p > 0 ? p : 1;
  });

  // Filter state initialized from URL
  const [filters, setFilters] = useState<FilterState>(() => ({
    q: searchParams?.get("q") || "",
    category: searchParams?.get("category") || "",
    priceRange: searchParams?.get("priceRange") || "all",
    color: searchParams?.get("color") || "",
    size: searchParams?.get("size") || "",
    sort: searchParams?.get("sort") || "featured",
  }));

  // Catalog response state
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Sync state if URL searchParams changes externally
  useEffect(() => {
    const pageFromUrl = Number(searchParams?.get("page")) || 1;
    setCurrentPage(pageFromUrl);
    setFilters({
      q: searchParams?.get("q") || "",
      category: searchParams?.get("category") || "",
      priceRange: searchParams?.get("priceRange") || "all",
      color: searchParams?.get("color") || "",
      size: searchParams?.get("size") || "",
      sort: searchParams?.get("sort") || "featured",
    });
  }, [searchParams]);

  // Synchronize URL query parameters with active filters and page
  const updateUrl = (newFilters: FilterState, newPage: number) => {
    const params = new URLSearchParams();
    if (newPage > 1) params.set("page", String(newPage));
    if (newFilters.q) params.set("q", newFilters.q);
    if (newFilters.category) params.set("category", newFilters.category);
    if (newFilters.priceRange && newFilters.priceRange !== "all") {
      params.set("priceRange", newFilters.priceRange);
    }
    if (newFilters.color) params.set("color", newFilters.color);
    if (newFilters.size) params.set("size", newFilters.size);
    if (newFilters.sort && newFilters.sort !== "featured") {
      params.set("sort", newFilters.sort);
    }

    const qs = params.toString();
    const url = qs ? `/?${qs}#catalog` : "/#catalog";
    window.history.replaceState(null, "", url);
  };

  // Fetch products whenever filters or page change
  useEffect(() => {
    let isCancelled = false;
    setIsLoading(true);

    fetchProducts({
      page: currentPage,
      limit: PAGE_SIZE,
      category: filters.category,
      search: filters.q,
      sort: filters.sort,
      priceRange: filters.priceRange,
      color: filters.color,
      size: filters.size,
    })
      .then((data: PaginatedProducts) => {
        if (!isCancelled) {
          setProducts(data.items);
          setTotal(data.total);
          setTotalPages(data.totalPages);
        }
      })
      .catch(() => {
        if (!isCancelled) {
          setProducts([]);
          setTotal(0);
          setTotalPages(1);
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [currentPage, filters]);

  // Update filters and reset page to 1
  const handleFilterChange = (newFilters: FilterState) => {
    setFilters(newFilters);
    setCurrentPage(1);
    updateUrl(newFilters, 1);
  };

  // Reset all filters to default
  const handleResetFilters = () => {
    const emptyFilters: FilterState = {
      q: "",
      category: "",
      priceRange: "all",
      color: "",
      size: "",
      sort: "featured",
    };
    handleFilterChange(emptyFilters);
  };

  // Handle page navigation with smooth scroll back to catalog
  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > totalPages || newPage === currentPage) return;
    startTransition(() => {
      setCurrentPage(newPage);
      updateUrl(filters, newPage);
    });

    const catalogEl = document.getElementById("catalog");
    if (catalogEl) {
      catalogEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  // Modal for quick scan from home page
  const [scanOpen, setScanOpen] = useState(false);
  const [scanProduct, setScanProduct] = useState<Product>(essential);

  const openScanForProduct = (prod: Product) => {
    setScanProduct(prod);
    setScanOpen(true);
  };

  return (
    <div className="storefront">
      <Header />

      <main className="shop-main">
        {/* Compact & Refined Editorial Hero Banner */}
        <section className="shop-hero-editorial">
          <div className="hero-content">
            <span className="hero-season-tag">
              <Sparkles size={14} /> Bộ sưu tập Thu Đông 2026
            </span>
            <h1 className="hero-title">
              Vừa vặn từ phom dáng
              <br />
              đến hình thể của bạn.
            </h1>
            <p className="hero-desc">
              Thiết kế tối giản trên nền chất liệu tự nhiên cao cấp. Kết hợp công nghệ mô phỏng hình thể 3D để mỗi sản phẩm bạn chọn đều mang lại cảm giác thoải mái nhất.
            </p>

            <div className="hero-actions">
              <a href="#catalog" className="shop-primary hero-cta-btn">
                Khám phá bộ sưu tập <ArrowDown size={17} />
              </a>
              <button
                className="shop-secondary hero-scan-btn"
                onClick={() => openScanForProduct(essential)}
                aria-label="Bạn chưa chắc về size? Tìm size bằng 3D"
              >
                <ScanLine size={18} />
                {job?.status === "completed" ? "Xem lại hình thể 3D của bạn" : "Bạn chưa chắc về size? Tìm với 3D"}
              </button>
            </div>
          </div>

          <div className="hero-feature-card">
            <div className="feature-card-eyebrow">
              <span className="feature-atelier-badge">MORPH STUDIO · 3D FIT LAB</span>
              <span className="feature-status-dot" title="Sẵn sàng kết nối" />
            </div>
            <h3 className="feature-card-heading">
              Mô phỏng hình thể 3D & gợi ý size qua 2 góc chụp webcam
            </h3>
            <p className="feature-card-text">
              Ước lượng hình thể tham khảo qua 2 góc chụp trước và nghiêng từ webcam, tự động đối chiếu với bảng số đo của từng thiết kế mà không cần thước dây.
            </p>
            <div className="feature-card-highlights">
              <div className="highlight-item">
                <span className="highlight-bullet" />
                <span>Webcam thân trên · 2 góc chụp trước & nghiêng</span>
              </div>
              <div className="highlight-item">
                <span className="highlight-bullet" />
                <span>Ước lượng hình thể tham khảo qua 2 góc chụp webcam</span>
              </div>
              <div className="highlight-item">
                <span className="highlight-bullet" />
                <span>Không lưu hồ sơ ảnh cá nhân · Dữ liệu phiên tạm thời</span>
              </div>
            </div>
            <button
              className="hero-scan-cta-link"
              onClick={() => openScanForProduct(essential)}
              aria-label="Trải nghiệm phòng thử 3D ngay"
            >
              <span className="cta-icon-text">
                <ScanLine size={16} />
                <span>{job?.status === "completed" ? "Xem lại mô hình 3D của bạn" : "Trải nghiệm phòng thử 3D ngay"}</span>
              </span>
              <ArrowRight size={15} />
            </button>
          </div>
        </section>

        {/* Product Catalog Section */}
        <section className="shop-catalog-section" id="catalog">
          <div className="catalog-header-row">
            <div>
              <h2 className="catalog-title">Bộ sưu tập trang phục</h2>
              <p className="catalog-subtitle">
                Được tuyển chọn kỹ lưỡng với đầy đủ bảng size cơ thể cho từng thiết kế.
              </p>
            </div>
          </div>

          {/* Filtering Bar */}
          <ProductFilter
            filters={filters}
            onChange={handleFilterChange}
            onReset={handleResetFilters}
            totalResults={total}
          />

          {/* Product Grid / Skeleton / Empty State */}
          {isLoading ? (
            <ProductGridSkeleton count={8} />
          ) : products.length > 0 ? (
            <>
              <div className="product-grid">
                {products.map((product, idx) => (
                  <ProductCard key={product.id} product={product} index={idx} />
                ))}
              </div>

              {/* Pagination Controls */}
              <PaginationControls
                currentPage={currentPage}
                totalPages={totalPages}
                total={total}
                limit={PAGE_SIZE}
                onPageChange={handlePageChange}
              />
            </>
          ) : (
            <div className="catalog-empty-state">
              <div className="empty-icon-wrap">
                <ScanLine size={40} />
              </div>
              <h3>Không tìm thấy sản phẩm phù hợp</h3>
              <p>
                Không có món đồ nào khớp với bộ lọc bạn đã chọn. Hãy thử xóa bớt bộ lọc hoặc tìm kiếm với từ khóa khác.
              </p>
              <button className="shop-primary" onClick={handleResetFilters}>
                Xóa bộ lọc
              </button>
            </div>
          )}
        </section>

        {/* Tasteful & Compact 3-Step Fit Guide */}
        <section className="shop-fit-story">
          <div>
            <h2>Vừa vặn bắt đầu<br />từ bạn.</h2>
            <p>
              Mỗi cơ thể là một tỉ lệ duy nhất. Công nghệ 3D của MORPH hỗ trợ bạn đưa ra quyết định chọn size tự tin hơn mà không cần phỏng đoán.
            </p>
            <button className="shop-text" onClick={() => openScanForProduct(essential)}>
              Trải nghiệm scan 3D ngay <ArrowRight size={17} />
            </button>
          </div>
          <ol>
            <li>
              <span>01</span>
              <div>
                <h3>Chụp hai góc bằng webcam</h3>
                <p>Chính diện và nghiêng 90°, AI tự căn chỉnh và đếm ngược.</p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <h3>Mô phỏng hình thể 3D</h3>
                <p>Xem số đo ước lượng và tương tác trực quan xoay 360°.</p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <h3>Đối chiếu bảng size riêng biệt</h3>
                <p>Tự động tính toán độ vừa vặn cho từng mẫu áo, quần hay váy.</p>
              </div>
            </li>
          </ol>
          <p className="shop-story-note">
            * Tính năng đang trong giai đoạn thử nghiệm. Kết quả số đo mang tính chất tham khảo; chưa kiểm chứng thực nghiệm trên cơ thể người thật.
          </p>
        </section>
      </main>

      <Footer />

      {/* Cart & Wishlist Drawers */}
      <CartDrawer />
      <WishlistDrawer />

      {/* Scan Modal from Home */}
      <Modal
        open={scanOpen}
        onClose={() => setScanOpen(false)}
        title={`Tìm size của tôi · ${scanProduct.name}`}
        wide
      >
        {scanOpen && (
          <FitExperience
            product={scanProduct}
            active={scanOpen}
            onSelectSize={(chosenSize) => {
              setScanOpen(false);
              router.push(`/products/${scanProduct.slug}?size=${chosenSize}`);
            }}
          />
        )}
      </Modal>
    </div>
  );
}

export default function StorefrontHome() {
  return (
    <Suspense fallback={<div className="fit-lazy">Đang tải cửa hàng MORPH Studio…</div>}>
      <StorefrontHomeContent />
    </Suspense>
  );
}
