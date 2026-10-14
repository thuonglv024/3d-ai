"use client";

import React, { createContext, useContext, useEffect, useState, useMemo } from "react";

export interface CartItem {
  id: string; // unique line id: `${productId}__${color}__${size}`
  productId: string;
  productSlug: string;
  name: string;
  price: number;
  color: string;
  size: string;
  image: string;
  quantity: number;
}

interface RemovedCartRecord {
  item: CartItem;
  index: number;
}

export interface CartContextValue {
  cart: CartItem[];
  addToCart: (item: Omit<CartItem, "id" | "quantity">, quantity?: number, openDrawer?: boolean) => void;
  updateQuantity: {
    (id: string, delta: number): void;
    (productId: string, color: string, size: string, deltaOrNewQty: number, isAbsolute?: boolean): void;
  };
  updateVariant: (
    oldItem: { productId: string; color: string; size: string } | CartItem,
    newColor: string,
    newSize: string
  ) => void;
  removeItem: (productId: string, color: string, size: string) => void;
  removeFromCart: (id: string) => void;
  undoRemove: () => void;
  lastRemovedItem: CartItem | null;
  clearCart: () => void;
  totalQuantity: number;
  subtotal: number;
  isCartOpen: boolean;
  setIsCartOpen: (open: boolean) => void;
  hydrated: boolean;

  // Wishlist
  wishlist: string[]; // array of product ids
  toggleWishlist: (productId: string) => void;
  isWishlisted: (productId: string) => boolean;
  isWishlistOpen: boolean;
  setIsWishlistOpen: (open: boolean) => void;
}

const CartContext = createContext<CartContextValue | null>(null);

const CART_STORAGE_KEY = "morph-demo-cart-v2";
const WISHLIST_STORAGE_KEY = "morph-demo-wishlist-v1";

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCart] = useState<CartItem[]>([]);
  const [wishlist, setWishlist] = useState<string[]>([]);
  const [lastRemoved, setLastRemoved] = useState<RemovedCartRecord | null>(null);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isWishlistOpen, setIsWishlistOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage on client mount
  useEffect(() => {
    try {
      const savedCart = localStorage.getItem(CART_STORAGE_KEY);
      if (savedCart) {
        const parsed = JSON.parse(savedCart);
        if (Array.isArray(parsed)) {
          setCart(
            parsed.filter(
              (item: any) =>
                item &&
                typeof item.id === "string" &&
                typeof item.productId === "string" &&
                typeof item.name === "string" &&
                typeof item.price === "number" &&
                typeof item.color === "string" &&
                typeof item.size === "string" &&
                Number.isInteger(item.quantity) &&
                item.quantity > 0 &&
                item.quantity <= 10
            )
          );
        }
      }

      const savedWishlist = localStorage.getItem(WISHLIST_STORAGE_KEY);
      if (savedWishlist) {
        const parsedW = JSON.parse(savedWishlist);
        if (Array.isArray(parsedW)) {
          setWishlist(parsedW.filter((id) => typeof id === "string"));
        }
      }
    } catch {
      // Ignore storage parse errors
    } finally {
      setHydrated(true);
    }
  }, []);

  // Save cart changes to localStorage
  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
    } catch {}
  }, [cart, hydrated]);

  // Save wishlist changes to localStorage
  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(WISHLIST_STORAGE_KEY, JSON.stringify(wishlist));
    } catch {}
  }, [wishlist, hydrated]);

  const addToCart = (item: Omit<CartItem, "id" | "quantity">, quantity = 1, openDrawer = false) => {
    const lineId = `${item.productId}__${item.color}__${item.size}`;
    const qtyToAdd = Math.max(1, Math.min(10, quantity));

    setCart((prev) => {
      const existingIndex = prev.findIndex((l) => l.id === lineId);
      if (existingIndex > -1) {
        const updated = [...prev];
        const currentQty = updated[existingIndex].quantity;
        const newQty = Math.min(10, currentQty + qtyToAdd);
        updated[existingIndex] = { ...updated[existingIndex], quantity: newQty };
        return updated;
      }
      return [...prev, { ...item, id: lineId, quantity: qtyToAdd }];
    });

    if (openDrawer) {
      setIsCartOpen(true);
    }
  };

  function updateQuantity(id: string, delta: number): void;
  function updateQuantity(
    productId: string,
    color: string,
    size: string,
    deltaOrNewQty: number,
    isAbsolute?: boolean
  ): void;
  function updateQuantity(
    productIdOrLineId: string,
    colorOrDelta: string | number,
    size?: string,
    deltaOrNewQty?: number,
    isAbsolute = false
  ): void {
    setCart((prev) => {
      // Polymorphic overload: updateQuantity(lineId, delta)
      if (typeof colorOrDelta === "number") {
        const lineId = productIdOrLineId;
        const delta = colorOrDelta;
        return prev
          .map((line) => {
            if (line.id !== lineId) return line;
            const newQty = line.quantity + delta;
            if (newQty <= 0) return null;
            return { ...line, quantity: Math.min(10, Math.max(1, newQty)) };
          })
          .filter((l): l is CartItem => l !== null);
      }

      // Overload: updateQuantity(productId, color, size, deltaOrNewQty, isAbsolute)
      const productId = productIdOrLineId;
      const color = colorOrDelta;
      const itemSize = size;
      const targetVal = deltaOrNewQty ?? 0;
      const targetLineId = `${productId}__${color}__${itemSize}`;

      return prev
        .map((line) => {
          const matches =
            line.id === targetLineId ||
            (line.productId === productId && line.color === color && line.size === itemSize);
          if (!matches) return line;
          if (isAbsolute) {
            return { ...line, quantity: Math.max(1, Math.min(10, targetVal)) };
          }
          const newQty = line.quantity + targetVal;
          if (newQty <= 0) return null;
          return { ...line, quantity: Math.min(10, Math.max(1, newQty)) };
        })
        .filter((l): l is CartItem => l !== null);
    });
  }

  const updateVariant = (
    oldItem: { productId: string; color: string; size: string } | CartItem,
    newColor: string,
    newSize: string
  ) => {
    if (oldItem.color === newColor && oldItem.size === newSize) return;

    const oldLineId = `${oldItem.productId}__${oldItem.color}__${oldItem.size}`;
    const newLineId = `${oldItem.productId}__${newColor}__${newSize}`;

    setCart((prev) => {
      const oldIndex = prev.findIndex(
        (l) =>
          l.id === oldLineId ||
          (l.productId === oldItem.productId && l.color === oldItem.color && l.size === oldItem.size)
      );
      if (oldIndex === -1) return prev;

      const existingItem = prev[oldIndex];
      const targetIndex = prev.findIndex((l) => l.id === newLineId);

      if (targetIndex !== -1 && targetIndex !== oldIndex) {
        // If new variant already in cart, merge quantities!
        const mergedQty = Math.min(10, prev[targetIndex].quantity + existingItem.quantity);
        return prev
          .map((item, idx) => {
            if (idx === targetIndex) {
              return { ...item, quantity: mergedQty };
            }
            return item;
          })
          .filter((_, idx) => idx !== oldIndex);
      }

      // New variant does not exist yet: update line in place
      return prev.map((item, idx) => {
        if (idx !== oldIndex) return item;
        return {
          ...item,
          id: newLineId,
          color: newColor,
          size: newSize,
        };
      });
    });
  };

  const removeItem = (productId: string, color: string, size: string) => {
    const lineId = `${productId}__${color}__${size}`;
    setCart((prev) => {
      const targetIndex = prev.findIndex(
        (l) =>
          l.id === lineId ||
          (l.productId === productId && l.color === color && l.size === size)
      );
      if (targetIndex === -1) return prev;
      setLastRemoved({ item: prev[targetIndex], index: targetIndex });
      return prev.filter((_, idx) => idx !== targetIndex);
    });
  };

  const removeFromCart = (id: string) => {
    setCart((prev) => {
      const targetIndex = prev.findIndex((l) => l.id === id);
      if (targetIndex === -1) return prev;
      setLastRemoved({ item: prev[targetIndex], index: targetIndex });
      return prev.filter((_, idx) => idx !== targetIndex);
    });
  };

  const undoRemove = () => {
    if (!lastRemoved) return;
    const { item, index } = lastRemoved;
    setCart((prev) => {
      const existingIdx = prev.findIndex((l) => l.id === item.id);
      if (existingIdx !== -1) {
        // Item was re-added while undone, merge quantity
        const updated = [...prev];
        updated[existingIdx] = {
          ...updated[existingIdx],
          quantity: Math.min(10, updated[existingIdx].quantity + item.quantity),
        };
        return updated;
      }
      const updated = [...prev];
      const insertIdx = Math.min(Math.max(0, index), updated.length);
      updated.splice(insertIdx, 0, item);
      return updated;
    });
    setLastRemoved(null);
  };

  const clearCart = () => {
    setCart([]);
  };

  const toggleWishlist = (productId: string) => {
    setWishlist((prev) =>
      prev.includes(productId) ? prev.filter((id) => id !== productId) : [...prev, productId]
    );
  };

  const isWishlisted = (productId: string) => wishlist.includes(productId);

  const totalQuantity = useMemo(() => cart.reduce((sum, item) => sum + item.quantity, 0), [cart]);

  const subtotal = useMemo(
    () => cart.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [cart]
  );

  return (
    <CartContext.Provider
      value={{
        cart,
        addToCart,
        updateQuantity,
        updateVariant,
        removeItem,
        removeFromCart,
        undoRemove,
        lastRemovedItem: lastRemoved ? lastRemoved.item : null,
        clearCart,
        totalQuantity,
        subtotal,
        isCartOpen,
        setIsCartOpen,
        hydrated,
        wishlist,
        toggleWishlist,
        isWishlisted,
        isWishlistOpen,
        setIsWishlistOpen,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used within a CartProvider");
  return ctx;
}
