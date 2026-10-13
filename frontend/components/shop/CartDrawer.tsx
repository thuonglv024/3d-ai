"use client";

import Link from "next/link";
import { useRef } from "react";
import { ArrowLeft, ArrowRight, Minus, Plus, ShoppingBag, Trash2, X } from "lucide-react";
import { useCart } from "../../lib/CartContext";
import { money } from "../../lib/catalog";
import { useDrawerA11y } from "../../lib/useDrawerA11y";

export default function CartDrawer() {
  const { cart, updateQuantity, removeFromCart, totalQuantity, subtotal, isCartOpen, setIsCartOpen } =
    useCart();
  const panelRef = useRef<HTMLDivElement>(null);

  useDrawerA11y(isCartOpen, () => setIsCartOpen(false), panelRef);

  if (!isCartOpen) return null;

  return (
    <div
      className="cart-drawer-backdrop"
      onClick={() => setIsCartOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Giỏ hàng demo"
    >
      <div
        ref={panelRef}
        tabIndex={-1}
        className="cart-drawer-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="cart-drawer-header">
          <div className="cart-title-row">
            <ShoppingBag size={20} />
            <h2>Giỏ hàng của bạn</h2>
            <span className="cart-count-badge">({totalQuantity})</span>
          </div>
          <button
            type="button"
            className="shop-icon drawer-close-btn"
            onClick={() => setIsCartOpen(false)}
            aria-label="Đóng Giỏ hàng"
          >
            <X size={20} />
          </button>
        </div>

        <div className="cart-drawer-body">
          {cart.length > 0 ? (
            <div className="cart-items-list">
              {cart.map((line) => (
                <div className="cart-line-item" key={line.id}>
                  <Link
                    href={`/products/${line.productSlug}`}
                    onClick={() => setIsCartOpen(false)}
                    className="cart-line-img"
                  >
                    <img
                      src={line.image}
                      alt={line.name}
                      width="84"
                      height="105"
                      onError={(e) => {
                        e.currentTarget.src = "/products/v2/ao-thun-essential.jpg";
                      }}
                    />
                  </Link>

                  <div className="cart-line-details">
                    <Link
                      href={`/products/${line.productSlug}`}
                      onClick={() => setIsCartOpen(false)}
                      className="cart-line-name"
                    >
                      {line.name}
                    </Link>
                    <p className="cart-line-variant">
                      Màu: {line.color} · Size: <strong>{line.size}</strong>
                    </p>
                    <div className="cart-line-price">{money(line.price)}</div>

                    <div className="cart-quantity-row">
                      <div className="cart-quantity-control">
                        <button
                          className="qty-btn"
                          aria-label={`Giảm số lượng ${line.name}`}
                          disabled={line.quantity <= 1}
                          onClick={() => updateQuantity(line.id, -1)}
                        >
                          <Minus size={14} />
                        </button>
                        <span className="qty-value">{line.quantity}</span>
                        <button
                          className="qty-btn"
                          aria-label={`Tăng số lượng ${line.name}`}
                          disabled={line.quantity >= 10}
                          onClick={() => updateQuantity(line.id, 1)}
                        >
                          <Plus size={14} />
                        </button>
                      </div>

                      <button
                        className="remove-line-btn"
                        aria-label={`Xóa ${line.name} size ${line.size} khỏi giỏ`}
                        onClick={() => removeFromCart(line.id)}
                      >
                        <Trash2 size={16} />
                        <span>Xóa</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="cart-empty-state">
              <ShoppingBag size={48} strokeWidth={1.2} />
              <h3>Giỏ hàng đang trống</h3>
              <p>Khám phá bộ sưu tập và tìm món đồ vừa vặn với hình thể của bạn.</p>
              <button
                className="shop-primary"
                onClick={() => setIsCartOpen(false)}
              >
                Khám phá sản phẩm
              </button>
            </div>
          )}
        </div>

        {cart.length > 0 && (
          <div className="cart-drawer-footer">
            <div className="cart-summary-line">
              <span>Tạm tính ({totalQuantity} món)</span>
              <strong>{money(subtotal)}</strong>
            </div>

            <div className="cart-demo-notice">
              <p>
                <strong>Trải nghiệm mua sắm thử nghiệm</strong>
                <br />
                Giỏ hàng được lưu trữ cục bộ trên trình duyệt của bạn. Hệ thống chưa tích hợp thanh toán
                hoặc xử lý giao hàng thương mại thật.
              </p>
            </div>

            <div className="cart-drawer-actions">
              <Link
                href="/cart"
                className="shop-primary view-cart-page-btn"
                onClick={() => setIsCartOpen(false)}
              >
                Xem trang giỏ hàng
                <ArrowRight size={16} />
              </Link>

              <button
                type="button"
                className="shop-secondary continue-shopping-btn"
                onClick={() => setIsCartOpen(false)}
              >
                <ArrowLeft size={16} />
                Tiếp tục chọn đồ
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
