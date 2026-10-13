"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import {
  Heart,
  Trash2,
  X,
  AlertCircle,
  AlertTriangle,
  ShoppingBag,
  ArrowRight,
  Check,
  RefreshCw,
  Minus,
  Plus,
} from "lucide-react";
import { useCart } from "../../lib/CartContext";
import { money, getProductBySlug as getLocalProductBySlug, type Product } from "../../lib/catalog";
import { fetchProductBySlug, productCache } from "../../lib/catalogApi";
import { useDrawerA11y } from "../../lib/useDrawerA11y";
import CustomSelect from "./CustomSelect";

interface WishlistResolvedItem {
  id: string;
  status: "available" | "unavailable";
  product?: Product;
}

interface ItemVariantState {
  color: string;
  size: string;
  quantity: number;
  error?: string;
  addedSuccess?: boolean;
}

export default function WishlistDrawer() {
  const router = useRouter();
  const { wishlist, toggleWishlist, isWishlistOpen, setIsWishlistOpen, addToCart } = useCart();
  const panelRef = useRef<HTMLDivElement>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [resolvedItems, setResolvedItems] = useState<WishlistResolvedItem[]>([]);
  const [retryKey, setRetryKey] = useState(0);

  // Variant selection and errors per product ID
  const [variantSelections, setVariantSelections] = useState<Record<string, ItemVariantState>>({});
  // Checked items for batch add/checkout
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchSuccess, setBatchSuccess] = useState<string | null>(null);

  // Auto-dismiss batch success banner
  useEffect(() => {
    if (!batchSuccess) return;
    const timer = setTimeout(() => setBatchSuccess(null), 4000);
    return () => clearTimeout(timer);
  }, [batchSuccess]);

  // Resolve wishlist items details from API or local fallback
  const resolveWishlist = useCallback(async (ids: string[], isMounted: () => boolean) => {
    if (ids.length === 0) {
      setResolvedItems([]);
      setIsLoading(false);
      setFetchError(null);
      return;
    }

    setIsLoading(true);
    setFetchError(null);

    let hadNetworkError = false;
    const results: WishlistResolvedItem[] = [];

    await Promise.all(
      ids.map(async (id) => {
        // Check cache first
        const cached = productCache.get(id);
        if (cached) {
          results.push({ id, status: "available", product: cached });
          return;
        }

        try {
          const res = await fetch(`/api/products/${encodeURIComponent(id)}`, {
            headers: { Accept: "application/json" },
            cache: "no-store",
          });

          if (res.ok) {
            const data = (await res.json()) as Product;
            if (data && (data.id || data.slug)) {
              productCache.set(data.id, data);
              if (data.slug) productCache.set(data.slug, data);
              results.push({ id, status: "available", product: data });
              return;
            }
          }

          if (res.status === 404) {
            // Check local catalog fallback
            const local = getLocalProductBySlug(id);
            if (local) {
              productCache.set(local.id, local);
              if (local.slug) productCache.set(local.slug, local);
              results.push({ id, status: "available", product: local });
            } else {
              results.push({ id, status: "unavailable" });
            }
            return;
          }

          // Other HTTP status
          hadNetworkError = true;
          const fallback = await fetchProductBySlug(id);
          if (fallback) {
            results.push({ id, status: "available", product: fallback });
          } else {
            results.push({ id, status: "unavailable" });
          }
        } catch {
          // Network failure
          hadNetworkError = true;
          const local = getLocalProductBySlug(id);
          if (local) {
            results.push({ id, status: "available", product: local });
          }
        }
      })
    );

    if (!isMounted()) return;

    // If completely failed due to network error and no items could be resolved
    if (hadNetworkError && results.length === 0 && ids.length > 0) {
      setFetchError(
        "Không thể kết nối đến máy chủ để tải thông tin sản phẩm yêu thích. Vui lòng thử lại."
      );
      setIsLoading(false);
      return;
    }

    // Preserve the original wishlist order
    const orderedResults: WishlistResolvedItem[] = ids.map((id) => {
      const found = results.find((r) => r.id === id);
      if (found) return found;
      // If network failed for this specific item but not others
      return { id, status: "unavailable" };
    });

    setResolvedItems(orderedResults);
    setIsLoading(false);

    // Initialize selectedIds with all available item IDs
    setSelectedIds((prev) => {
      const next = new Set<string>();
      orderedResults.forEach((r) => {
        if (r.status === "available") {
          next.add(r.id);
          if (r.product) {
            next.add(r.product.id);
          }
        }
      });
      return next;
    });
  }, []);

  useEffect(() => {
    if (!isWishlistOpen) return;
    let mounted = true;
    resolveWishlist(wishlist, () => mounted);
    return () => {
      mounted = false;
    };
  }, [isWishlistOpen, wishlist, retryKey, resolveWishlist]);

  useDrawerA11y(isWishlistOpen, () => setIsWishlistOpen(false), panelRef);

  if (!isWishlistOpen) return null;

  // Helpers for variant selections
  const updateItemColor = (productId: string, color: string, product: Product) => {
    setBatchError(null);
    setVariantSelections((prev) => {
      const current = prev[productId] || { color: "", size: "", quantity: 1 };
      // Check if current size is valid for the new color
      let validSize = current.size;
      if (product.variants && product.variants.length > 0) {
        const matchingVariants = product.variants.filter(
          (v: any) =>
            (v.color_name === color || v.color === color) &&
            (v.stock === undefined || v.stock > 0) &&
            v.isActive !== false &&
            v.is_active !== 0
        );
        const sizesForColor = matchingVariants.map((v: any) => v.size as string);
        if (validSize && !sizesForColor.includes(validSize)) {
          validSize = sizesForColor[0] || "";
        }
      }
      return {
        ...prev,
        [productId]: {
          ...current,
          color,
          size: validSize,
          error: undefined,
        },
      };
    });
  };

  const updateItemSize = (productId: string, size: string) => {
    setBatchError(null);
    setVariantSelections((prev) => {
      const current = prev[productId] || { color: "", size: "", quantity: 1 };
      return {
        ...prev,
        [productId]: {
          ...current,
          size,
          error: undefined,
        },
      };
    });
  };

  const updateItemQuantity = (productId: string, delta: number) => {
    setVariantSelections((prev) => {
      const current = prev[productId] || { color: "", size: "", quantity: 1 };
      const nextQty = Math.max(1, Math.min(10, current.quantity + delta));
      return {
        ...prev,
        [productId]: {
          ...current,
          quantity: nextQty,
        },
      };
    });
  };

  const toggleSelectId = (id: string) => {
    setBatchError(null);
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    setBatchError(null);
    const availableIds = resolvedItems.filter((i) => i.status === "available").map((i) => i.id);
    if (selectedIds.size === availableIds.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(availableIds));
    }
  };

  // Add a single item to cart
  const handleAddSingleToCart = (item: WishlistResolvedItem) => {
    if (!item.product) return;
    const p = item.product;
    const selection = variantSelections[p.id] || { color: "", size: "", quantity: 1 };

    // Strict validation: user must explicitly choose color and size
    if (!selection.color && !selection.size) {
      setVariantSelections((prev) => ({
        ...prev,
        [p.id]: { ...selection, error: "Vui lòng chọn màu và size trước khi thêm vào giỏ." },
      }));
      return;
    }
    if (!selection.color) {
      setVariantSelections((prev) => ({
        ...prev,
        [p.id]: { ...selection, error: "Vui lòng chọn màu sắc." },
      }));
      return;
    }
    if (!selection.size) {
      setVariantSelections((prev) => ({
        ...prev,
        [p.id]: { ...selection, error: "Vui lòng chọn kích cỡ (size)." },
      }));
      return;
    }

    addToCart(
      {
        productId: p.id,
        productSlug: p.slug,
        name: p.name,
        price: p.price,
        color: selection.color,
        size: selection.size,
        image: p.image,
      },
      selection.quantity,
      false
    );

    // Show temporary feedback
    setVariantSelections((prev) => ({
      ...prev,
      [p.id]: { ...selection, error: undefined, addedSuccess: true },
    }));

    setTimeout(() => {
      setVariantSelections((prev) => {
        if (!prev[p.id]) return prev;
        return { ...prev, [p.id]: { ...prev[p.id], addedSuccess: false } };
      });
    }, 2500);
  };

  // Batch validate selected items
  const validateSelectedItems = (): boolean => {
    if (selectedIds.size === 0) {
      setBatchError("Vui lòng chọn ít nhất một sản phẩm.");
      return false;
    }

    let hasError = false;
    const nextSelections = { ...variantSelections };

    for (const item of resolvedItems) {
      if (item.status !== "available" || !item.product) continue;
      const isSelected = selectedIds.has(item.id) || (item.product && selectedIds.has(item.product.id));
      if (!isSelected) continue;
      const p = item.product;
      const selection = nextSelections[p.id] || { color: "", size: "", quantity: 1 };

      if (!selection.color && !selection.size) {
        nextSelections[p.id] = {
          ...selection,
          error: "Vui lòng chọn màu và size.",
        };
        hasError = true;
      } else if (!selection.color) {
        nextSelections[p.id] = {
          ...selection,
          error: "Vui lòng chọn màu sắc.",
        };
        hasError = true;
      } else if (!selection.size) {
        nextSelections[p.id] = {
          ...selection,
          error: "Vui lòng chọn kích cỡ (size).",
        };
        hasError = true;
      }
    }

    if (hasError) {
      setVariantSelections(nextSelections);
      setBatchError("Vui lòng chọn đầy đủ màu và size cho các sản phẩm đã chọn.");
      return false;
    }

    setBatchError(null);
    return true;
  };

  // Batch add selected items to cart (preserves existing cart items!)
  const handleBatchAddToCart = () => {
    if (!validateSelectedItems()) return;

    let addedCount = 0;
    for (const item of resolvedItems) {
      if (item.status !== "available" || !item.product) continue;
      const isSelected = selectedIds.has(item.id) || (item.product && selectedIds.has(item.product.id));
      if (!isSelected) continue;
      const p = item.product;
      const selection = variantSelections[p.id];
      if (!selection || !selection.color || !selection.size) continue;

      addToCart(
        {
          productId: p.id,
          productSlug: p.slug,
          name: p.name,
          price: p.price,
          color: selection.color,
          size: selection.size,
          image: p.image,
        },
        selection.quantity,
        false
      );
      addedCount++;
    }

    setBatchSuccess(`Đã thêm ${addedCount} sản phẩm vào giỏ hàng thành công!`);
  };

  // Batch add selected items and proceed to /checkout (preserves existing cart items!)
  const handleContinueToCheckout = () => {
    if (!validateSelectedItems()) return;

    for (const item of resolvedItems) {
      if (item.status !== "available" || !item.product) continue;
      const isSelected = selectedIds.has(item.id) || (item.product && selectedIds.has(item.product.id));
      if (!isSelected) continue;
      const p = item.product;
      const selection = variantSelections[p.id];
      if (!selection || !selection.color || !selection.size) continue;

      addToCart(
        {
          productId: p.id,
          productSlug: p.slug,
          name: p.name,
          price: p.price,
          color: selection.color,
          size: selection.size,
          image: p.image,
        },
        selection.quantity,
        false
      );
    }

    setIsWishlistOpen(false);
    router.push("/checkout");
  };

  const availableItems = resolvedItems.filter((i) => i.status === "available");
  const unavailableCount = resolvedItems.filter((i) => i.status === "unavailable").length;

  return (
    <div
      className="wishlist-modal-backdrop cart-drawer-backdrop"
      onClick={() => setIsWishlistOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Danh sách yêu thích"
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className="wishlist-modal-panel cart-drawer-panel"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: 620 }}
      >
        <div className="sheet-handle-bar" aria-hidden="true" />

        {/* Drawer Header */}
        <div className="cart-drawer-header">
          <div className="cart-title-row">
            <Heart size={20} fill="currentColor" color="var(--primary)" />
            <h2>Sản phẩm đã lưu</h2>
            <span className="cart-count-badge">({wishlist.length})</span>
          </div>
          <button
            type="button"
            className="shop-icon drawer-close-btn"
            onClick={() => setIsWishlistOpen(false)}
            aria-label="Đóng danh sách yêu thích"
          >
            <X size={20} />
          </button>
        </div>

        {/* Drawer Body */}
        <div className="cart-drawer-body">
          {/* Global error banner with Retry */}
          {fetchError && (
            <div
              className="error-message"
              role="alert"
              style={{
                marginBottom: 16,
                padding: "12px 14px",
                display: "flex",
                alignItems: "center",
                gap: 12,
                fontSize: 13,
              }}
            >
              <AlertCircle size={20} style={{ flexShrink: 0 }} />
              <div style={{ flex: 1 }}>{fetchError}</div>
              <button
                type="button"
                className="shop-secondary"
                style={{ padding: "6px 12px", fontSize: 12, flexShrink: 0 }}
                onClick={() => setRetryKey((k) => k + 1)}
              >
                <RefreshCw size={13} style={{ marginRight: 4 }} />
                Thử lại
              </button>
            </div>
          )}

          {/* Batch error message */}
          {batchError && (
            <div
              className="error-message"
              role="alert"
              style={{
                marginBottom: 16,
                padding: "10px 14px",
                fontSize: 12.5,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <AlertCircle size={16} />
              <span>{batchError}</span>
            </div>
          )}

          {/* Batch success message */}
          {batchSuccess && (
            <div
              role="status"
              style={{
                marginBottom: 16,
                padding: "10px 14px",
                background: "var(--surface-subtle)",
                border: "1px solid var(--border-gold)",
                borderRadius: "var(--radius-control)",
                color: "var(--accent-text)",
                fontSize: 13,
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Check size={16} />
              <span>{batchSuccess}</span>
            </div>
          )}

          {/* Loading Skeleton */}
          {isLoading && (
            <div
              className="cart-items-list"
              aria-busy="true"
              aria-label="Đang tải danh sách sản phẩm đã lưu"
            >
              {[1, 2].map((i) => (
                <div
                  className="cart-line-item"
                  key={`skeleton-${i}`}
                  style={{ opacity: 0.7, pointerEvents: "none" }}
                >
                  <div
                    className="cart-line-img"
                    style={{
                      background: "var(--surface-muted)",
                      animation: "pulse 1.5s infinite ease-in-out",
                    }}
                  />
                  <div className="cart-line-details" style={{ flex: 1 }}>
                    <div
                      style={{
                        height: 16,
                        width: "70%",
                        background: "var(--surface-muted)",
                        borderRadius: 4,
                        marginBottom: 8,
                        animation: "pulse 1.5s infinite ease-in-out",
                      }}
                    />
                    <div
                      style={{
                        height: 12,
                        width: "40%",
                        background: "var(--surface-muted)",
                        borderRadius: 4,
                        marginBottom: 10,
                        animation: "pulse 1.5s infinite ease-in-out",
                      }}
                    />
                    <div
                      style={{
                        height: 16,
                        width: "30%",
                        background: "var(--surface-muted)",
                        borderRadius: 4,
                        marginBottom: 12,
                        animation: "pulse 1.5s infinite ease-in-out",
                      }}
                    />
                    <div
                      style={{
                        height: 32,
                        width: "100%",
                        background: "var(--surface-muted)",
                        borderRadius: 6,
                        animation: "pulse 1.5s infinite ease-in-out",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Loaded Wishlist Items */}
          {!isLoading && resolvedItems.length > 0 && (
            <div className="cart-items-list">
              {/* Select All Checkbox bar if more than 1 available item */}
              {availableItems.length > 1 && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    paddingBottom: 12,
                    borderBottom: "1px dashed var(--line)",
                    fontSize: 13,
                    color: "var(--text-secondary)",
                  }}
                >
                  <label
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      cursor: "pointer",
                      userSelect: "none",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.size === availableItems.length}
                      onChange={toggleSelectAll}
                      style={{ accentColor: "var(--primary)", width: 16, height: 16 }}
                    />
                    <span>Chọn tất cả ({availableItems.length})</span>
                  </label>
                  <span>
                    Đã chọn <strong>{selectedIds.size}</strong> sản phẩm
                  </span>
                </div>
              )}

              {resolvedItems.map((item) => {
                // Unavailable state card
                if (item.status === "unavailable" || !item.product) {
                  return (
                    <div
                      className="cart-line-item"
                      key={item.id}
                      style={{
                        background: "var(--surface-subtle)",
                        borderRadius: "var(--radius-control)",
                        padding: 14,
                        border: "1px solid var(--line)",
                        opacity: 0.85,
                      }}
                    >
                      <div
                        className="cart-line-img"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          background: "var(--surface-muted)",
                        }}
                      >
                        <AlertTriangle size={24} color="var(--muted)" />
                      </div>
                      <div className="cart-line-details" style={{ flex: 1 }}>
                        <div
                          style={{
                            display: "inline-block",
                            padding: "2px 8px",
                            background: "#fff4e5",
                            color: "#b76e00",
                            fontSize: 11,
                            fontWeight: 600,
                            borderRadius: 4,
                            marginBottom: 6,
                          }}
                        >
                          Tạm hết hàng / Không khả dụng
                        </div>
                        <p
                          style={{
                            fontSize: 13,
                            color: "var(--text-secondary)",
                            margin: "0 0 8px",
                          }}
                        >
                          Sản phẩm mã <code>{item.id}</code> hiện không còn trong danh mục bán lẻ.
                        </p>
                        <button
                          type="button"
                          className="remove-line-btn"
                          onClick={() => toggleWishlist(item.id)}
                          aria-label={`Bỏ lưu mã ${item.id}`}
                        >
                          <Trash2 size={14} style={{ marginRight: 4 }} />
                          Bỏ lưu khỏi danh sách
                        </button>
                      </div>
                    </div>
                  );
                }

                // Available product card
                const p = item.product;
                const selection = variantSelections[p.id] || {
                  color: "",
                  size: "",
                  quantity: 1,
                };

                // Real available colors
                const colors =
                  p.colors && p.colors.length > 0
                    ? p.colors
                    : p.variants && p.variants.length > 0
                    ? Array.from(
                        new Set(p.variants.map((v: any) => v.color_name || v.color))
                      )
                        .filter(Boolean)
                        .map((name) => ({
                          name: name as string,
                          hex:
                            p.variants?.find((v: any) => (v.color_name || v.color) === name)
                              ?.color_hex || "#ccc",
                        }))
                    : [{ name: p.color || "Tiêu chuẩn", hex: "#ccc" }];

                // Real available sizes: if color is selected, filter sizes of that color
                let sizes: string[] = [];
                if (p.variants && p.variants.length > 0) {
                  if (selection.color) {
                    const matched = p.variants.filter(
                      (v: any) =>
                        (v.color_name === selection.color || v.color === selection.color) &&
                        (v.stock === undefined || v.stock > 0) &&
                        v.isActive !== false &&
                        v.is_active !== 0
                    );
                    sizes = Array.from(new Set(matched.map((v: any) => v.size as string)));
                  }
                  if (sizes.length === 0) {
                    // Fallback to all sizes present in variants
                    sizes = Array.from(new Set(p.variants.map((v: any) => v.size as string)));
                  }
                } else if (p.sizes && p.sizes.length > 0) {
                  sizes = p.sizes;
                } else {
                  sizes = ["F"];
                }

                const isChecked = selectedIds.has(item.id) || (p && selectedIds.has(p.id));

                return (
                  <div
                    className="cart-line-item"
                    key={p.id}
                    style={{
                      borderBottom: "1px solid var(--line)",
                      paddingBottom: 16,
                      position: "relative",
                    }}
                  >
                    {/* Item Checkbox */}
                    <div style={{ paddingTop: 4 }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {
                          toggleSelectId(item.id);
                          if (p && p.id !== item.id) toggleSelectId(p.id);
                        }}
                        aria-label={`Chọn ${p.name} để thao tác`}
                        style={{ accentColor: "var(--primary)", width: 17, height: 17, cursor: "pointer" }}
                      />
                    </div>

                    {/* Thumbnail */}
                    <Link
                      href={`/products/${p.slug}`}
                      onClick={() => setIsWishlistOpen(false)}
                      className="cart-line-img"
                    >
                      <img
                        src={p.image}
                        alt={p.name}
                        width="76"
                        height="96"
                        onError={(e) => {
                          e.currentTarget.src = "/products/v2/ao-thun-essential.jpg";
                        }}
                      />
                    </Link>

                    {/* Details & Variant pickers */}
                    <div className="cart-line-details" style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                          gap: 8,
                        }}
                      >
                        <Link
                          href={`/products/${p.slug}`}
                          onClick={() => setIsWishlistOpen(false)}
                          className="cart-line-name"
                          style={{ marginBottom: 2 }}
                        >
                          {p.name}
                        </Link>
                        <button
                          type="button"
                          className="remove-line-btn"
                          aria-label={`Bỏ lưu ${p.name}`}
                          onClick={() => toggleWishlist(p.id)}
                          style={{ flexShrink: 0, padding: 0 }}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>

                      <div className="cart-line-price" style={{ marginBottom: 8 }}>
                        {money(p.price)}
                      </div>

                      {/* Variant Selection Comboboxes */}
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr",
                          gap: 8,
                          marginBottom: 8,
                        }}
                      >
                        {/* Color Selector */}
                        <div>
                          <label
                            htmlFor={`wish-color-${p.id}`}
                            style={{
                              fontSize: 11,
                              fontWeight: 600,
                              color: "var(--text-secondary)",
                              display: "block",
                              marginBottom: 3,
                            }}
                          >
                            Màu sắc:
                          </label>
                          <CustomSelect
                            id={`wish-color-${p.id}`}
                            size="sm"
                            variant="compact"
                            value={selection.color}
                            placeholder="Chọn màu"
                            ariaLabel={`Chọn màu cho ${p.name}`}
                            onChange={(val) => updateItemColor(p.id, val, p)}
                            options={colors.map((c) => ({
                              value: c.name,
                              label: c.name,
                            }))}
                          />
                        </div>

                        {/* Size Selector */}
                        <div>
                          <label
                            htmlFor={`wish-size-${p.id}`}
                            style={{
                              fontSize: 11,
                              fontWeight: 600,
                              color: "var(--text-secondary)",
                              display: "block",
                              marginBottom: 3,
                            }}
                          >
                            Kích cỡ (Size):
                          </label>
                          <CustomSelect
                            id={`wish-size-${p.id}`}
                            size="sm"
                            variant="compact"
                            value={selection.size}
                            placeholder="Chọn size"
                            ariaLabel={`Chọn size cho ${p.name}`}
                            onChange={(val) => updateItemSize(p.id, val)}
                            options={sizes.map((s) => ({
                              value: s,
                              label: s,
                            }))}
                          />
                        </div>
                      </div>

                      {/* Quantity Stepper & Inline Actions */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 12,
                          marginTop: 8,
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ fontSize: 11.5, color: "var(--text-secondary)" }}>SL:</span>
                          <div className="cart-stepper" style={{ transform: "scale(0.9)", transformOrigin: "left center" }}>
                            <button
                              type="button"
                              aria-label={`Giảm số lượng ${p.name}`}
                              disabled={selection.quantity <= 1}
                              onClick={() => updateItemQuantity(p.id, -1)}
                            >
                              <Minus size={13} />
                            </button>
                            <span className="cart-stepper-val">{selection.quantity}</span>
                            <button
                              type="button"
                              aria-label={`Tăng số lượng ${p.name}`}
                              disabled={selection.quantity >= 10}
                              onClick={() => updateItemQuantity(p.id, 1)}
                            >
                              <Plus size={13} />
                            </button>
                          </div>
                        </div>

                        {/* Single Add-to-cart button */}
                        <button
                          type="button"
                          className="shop-primary"
                          onClick={() => handleAddSingleToCart(item)}
                          style={{
                            padding: "6px 12px",
                            fontSize: 12,
                            borderRadius: "var(--radius-control)",
                          }}
                        >
                          {selection.addedSuccess ? (
                            <>
                              <Check size={14} style={{ marginRight: 4 }} />
                              Đã thêm
                            </>
                          ) : (
                            <>
                              <ShoppingBag size={14} style={{ marginRight: 4 }} />
                              Thêm giỏ
                            </>
                          )}
                        </button>
                      </div>

                      {/* Inline Error Message on this item */}
                      {selection.error && (
                        <div
                          role="alert"
                          style={{
                            marginTop: 6,
                            color: "var(--danger)",
                            fontSize: 12,
                            fontWeight: 500,
                            display: "flex",
                            alignItems: "center",
                            gap: 4,
                          }}
                        >
                          <AlertCircle size={14} />
                          <span>{selection.error}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Genuine Empty State (wishlist array is truly empty) */}
          {!isLoading && !fetchError && wishlist.length === 0 && (
            <div className="cart-empty-state">
              <Heart size={48} strokeWidth={1.2} />
              <h3>Chưa có sản phẩm yêu thích</h3>
              <p>
                Nhấn vào biểu tượng trái tim ở bất kỳ sản phẩm nào để lưu lại danh sách riêng của bạn.
              </p>
              <button
                type="button"
                className="shop-primary"
                onClick={() => setIsWishlistOpen(false)}
              >
                Khám phá bộ sưu tập
              </button>
            </div>
          )}
        </div>

        {/* Drawer Footer with Batch Actions */}
        {!isLoading && availableItems.length > 0 && (
          <div className="cart-drawer-footer" style={{ padding: "16px 20px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
                fontSize: 13,
              }}
            >
              <span>
                Đã chọn <strong>{selectedIds.size}</strong>/{availableItems.length} sản phẩm
              </span>
              <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                Giữ nguyên các món đã có trong giỏ
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <button
                type="button"
                className="shop-secondary"
                onClick={handleBatchAddToCart}
                disabled={selectedIds.size === 0}
                style={{
                  padding: "10px 14px",
                  fontSize: 13,
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                }}
              >
                <ShoppingBag size={16} />
                <span>Thêm vào giỏ hàng</span>
              </button>

              <button
                type="button"
                className="shop-primary"
                onClick={handleContinueToCheckout}
                disabled={selectedIds.size === 0}
                style={{
                  padding: "10px 14px",
                  fontSize: 13,
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 6,
                }}
              >
                <span>Tiếp tục đặt hàng</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
