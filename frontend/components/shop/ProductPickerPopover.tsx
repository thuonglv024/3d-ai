"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Search, X, Check } from "lucide-react";
import type { Product, CategoryKey } from "../../lib/catalog";
import { essential, getAllProducts, money } from "../../lib/catalog";
import { fetchAllProducts } from "../../lib/catalogApi";

interface CategoryTab {
  key: string;
  name: string;
}

const CATEGORY_TABS: CategoryTab[] = [
  { key: "all", name: "Tất cả" },
  { key: "ao-thun", name: "Áo thun" },
  { key: "so-mi", name: "Sơ mi" },
  { key: "ao-khoac", name: "Áo khoác" },
  { key: "quan", name: "Quần" },
  { key: "vay", name: "Váy" },
];

export default function ProductPickerPopover({
  selectedProduct,
  onSelectProduct,
}: {
  selectedProduct: Product;
  onSelectProduct: (p: Product) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [products, setProducts] = useState<Product[]>(() => getAllProducts());
  const [mounted, setMounted] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const prevOpenRef = useRef(false);

  useEffect(() => {
    setMounted(true);
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 640);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Restore focus to trigger when closing
  useEffect(() => {
    if (prevOpenRef.current && !isOpen) {
      triggerRef.current?.focus();
    }
    prevOpenRef.current = isOpen;
  }, [isOpen]);

  // Lock body scroll on mobile bottom sheet
  useEffect(() => {
    if (isOpen && isMobile) {
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = prevOverflow;
      };
    }
  }, [isOpen, isMobile]);

  // Load all products from API (paginated without exceeding limit=100)
  useEffect(() => {
    let active = true;
    fetchAllProducts()
      .then((items) => {
        if (active && items.length > 0) {
          setProducts(items);
        }
      })
      .catch(() => {
        // Fall back to local catalog
        if (active) setProducts(getAllProducts());
      });

    return () => {
      active = false;
    };
  }, []);

  // Close on outside click or Escape
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        popoverRef.current &&
        !popoverRef.current.contains(target) &&
        (!menuRef.current || !menuRef.current.contains(target))
      ) {
        setIsOpen(false);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const [dropdownPosition, setDropdownPosition] = useState({
    flipUp: false,
    alignRight: false,
    maxHeight: 520,
  });

  useEffect(() => {
    if (!isOpen || !popoverRef.current) return;

    const measure = () => {
      const trigger = popoverRef.current;
      const menu = menuRef.current;
      if (!trigger) return;

      const tRect = trigger.getBoundingClientRect();
      const vWidth = window.innerWidth;
      const vHeight = window.innerHeight;

      const menuHeight = menu ? menu.offsetHeight : 440;
      const menuWidth = menu ? menu.offsetWidth : 440;

      const spaceBelow = vHeight - tRect.bottom;
      const spaceAbove = tRect.top;

      const flipUp = spaceBelow < menuHeight && spaceAbove > spaceBelow;
      const alignRight = tRect.left + menuWidth > vWidth - 16;
      const availableHeight = flipUp ? spaceAbove - 20 : spaceBelow - 20;

      setDropdownPosition({
        flipUp,
        alignRight,
        maxHeight: Math.max(220, Math.min(540, availableHeight)),
      });
    };

    measure();
    const handleResize = () => measure();
    window.addEventListener("resize", handleResize);
    window.addEventListener("scroll", handleResize, true);
    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("scroll", handleResize, true);
    };
  }, [isOpen]);

  // Focus search input when popover opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    } else {
      setSearchQuery("");
      setActiveCategory("all");
    }
  }, [isOpen]);

  // Filter products by search and category
  const filteredProducts = useMemo(() => {
    return products.filter((p) => {
      if (activeCategory !== "all" && p.category !== activeCategory) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchName = p.name.toLowerCase().includes(q);
        const matchSub = p.subtitle?.toLowerCase().includes(q);
        const matchCat = p.categoryName?.toLowerCase().includes(q);
        const matchMat = p.material?.toLowerCase().includes(q);
        if (!matchName && !matchSub && !matchCat && !matchMat) {
          return false;
        }
      }
      return true;
    });
  }, [products, activeCategory, searchQuery]);

  // Count items per category tab
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: products.length };
    for (const p of products) {
      counts[p.category] = (counts[p.category] || 0) + 1;
    }
    return counts;
  }, [products]);

  const handleSelect = (prod: Product) => {
    onSelectProduct(prod);
    setIsOpen(false);
  };

  const currentProd = selectedProduct || essential;

  const renderPopoverContent = () => (
    <>
      {isMobile && (
        <div
          className="product-picker-backdrop"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}
      <div
        ref={menuRef}
        className={`product-picker-popover ${dropdownPosition.flipUp && !isMobile ? "is-flipped-up" : ""} ${dropdownPosition.alignRight && !isMobile ? "is-align-right" : ""} ${isMobile ? "is-mobile-sheet" : ""}`}
        style={isMobile ? undefined : { maxHeight: `${dropdownPosition.maxHeight}px` }}
        role="dialog"
        aria-modal={isMobile ? "true" : undefined}
        aria-label="Bộ chọn sản phẩm đối chiếu size"
      >
        <div className="sheet-handle-bar" aria-hidden="true" />

        {isMobile && (
          <div className="picker-sheet-header-top">
            <span className="picker-sheet-title">Chọn sản phẩm đối chiếu</span>
            <button
              type="button"
              className="picker-close-sheet-btn"
              onClick={() => setIsOpen(false)}
              aria-label="Đóng bảng chọn sản phẩm"
            >
              <X size={18} />
            </button>
          </div>
        )}

        {/* Header & Search */}
        <div className="picker-popover-header">
          <div className="picker-search-wrap">
            <Search size={16} className="picker-search-icon" />
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Tìm theo tên sản phẩm, chất liệu..."
              className="picker-search-input"
              aria-label="Tìm kiếm sản phẩm"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="picker-clear-search"
                aria-label="Xóa từ khóa tìm kiếm"
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Category Tabs */}
          <div className="picker-category-tabs" role="tablist">
            {CATEGORY_TABS.map((tab) => {
              const count = categoryCounts[tab.key] || 0;
              const isActive = activeCategory === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className={`picker-tab-btn ${isActive ? "active" : ""}`}
                  onClick={() => setActiveCategory(tab.key)}
                >
                  <span>{tab.name}</span>
                  <span className="picker-tab-count">({count})</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Product Items List */}
        <div className="picker-product-list" role="listbox" tabIndex={-1}>
          {filteredProducts.length > 0 ? (
            filteredProducts.map((p) => {
              const isSelected = p.id === currentProd.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  className={`picker-product-item ${isSelected ? "selected" : ""}`}
                  onClick={() => handleSelect(p)}
                >
                  <span className="picker-item-thumb">
                    <img
                      src={p.image}
                      alt={p.name}
                      width="44"
                      height="44"
                      loading="lazy"
                      onError={(e) => {
                        e.currentTarget.src = "/products/v2/ao-thun-essential.jpg";
                      }}
                    />
                  </span>
                  <span className="picker-item-info">
                    <span className="picker-item-header">
                      <span className="picker-item-cat">{p.categoryName}</span>
                      <span className="picker-item-price">{money(p.price)}</span>
                    </span>
                    <strong className="picker-item-name">{p.name}</strong>
                    <span className="picker-item-sub">{p.subtitle}</span>
                  </span>
                  {isSelected && (
                    <span className="picker-item-check" aria-hidden="true">
                      <Check size={16} />
                    </span>
                  )}
                </button>
              );
            })
          ) : (
            <div className="picker-empty-state">
              <p>Không tìm thấy sản phẩm phù hợp với từ khóa.</p>
              {searchQuery && (
                <button
                  type="button"
                  className="picker-reset-btn"
                  onClick={() => {
                    setSearchQuery("");
                    setActiveCategory("all");
                  }}
                >
                  Xem tất cả sản phẩm
                </button>
              )}
            </div>
          )}
        </div>

        <div className="picker-popover-footer">
          <span>Hiển thị {filteredProducts.length} / {products.length} sản phẩm</span>
        </div>
      </div>
    </>
  );

  return (
    <div className="product-picker-container" ref={popoverRef}>
      {/* Trigger Button */}
      <button
        ref={triggerRef}
        type="button"
        className={`product-picker-trigger ${isOpen ? "open" : ""}`}
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        aria-label="Chọn sản phẩm đối chiếu bảng size"
      >
        <span className="picker-trigger-thumb">
          <img
            src={currentProd.image}
            alt={currentProd.name}
            width="32"
            height="32"
            className="trigger-img"
            onError={(e) => {
              e.currentTarget.src = "/products/v2/ao-thun-essential.jpg";
            }}
          />
        </span>
        <span className="picker-trigger-text">
          <span className="picker-label-prefix">Đối chiếu size:</span>
          <span className="picker-label-category">{currentProd.categoryName}</span>
          <span className="picker-label-divider">·</span>
          <strong className="picker-label-name">{currentProd.name}</strong>
        </span>
        <ChevronDown size={16} className={`picker-chevron ${isOpen ? "rotated" : ""}`} />
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        isMobile && mounted
          ? createPortal(renderPopoverContent(), document.body)
          : renderPopoverContent()
      )}
    </div>
  );
}
