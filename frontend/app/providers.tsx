"use client";

import React from "react";
import { AuthProvider } from "../lib/AuthContext";
import { CartProvider } from "../lib/CartContext";
import { ScanProvider } from "../lib/ScanContext";
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <CartProvider>
        <ScanProvider>
          {children}
        </ScanProvider>
      </CartProvider>
    </AuthProvider>
  );
}
