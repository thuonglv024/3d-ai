/**
 * MORPH Studio — Catalog API Client
 * Provides paginated querying, search, categories, and single-product lookup
 * with robust offline/SSR fallback to local catalog data in catalog.ts.
 */

import {
  type Product,
  type CategoryInfo,
  type CategoryKey,
  CATEGORIES,
  PRODUCTS,
  getAllProducts,
  getProductBySlug as getLocalProductBySlug,
} from "./catalog";

export interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

export interface CatalogQueryOptions {
  category?: string;
  search?: string;
  sort?: "featured" | "price_asc" | "price_desc" | string;
  page?: number;
  limit?: number;
  minPrice?: number;
  maxPrice?: number;
  priceRange?: string; // "all" | "under-500" | "500-1000" | "over-1000"
  color?: string;
  size?: string;
}

function getBaseApiUrl(): string {
  if (typeof window !== "undefined") {
    // Client-side: use relative URL so Next.js rewrites proxy to backend
    return "";
  }
  // Server-side: use environment variable or default backend port
  return process.env.BACKEND_URL || "http://127.0.0.1:8000";
}

/**
 * Filter and paginate local products array as a fallback when API is unreachable.
 */
function filterAndPaginateLocalProducts(options?: CatalogQueryOptions): PaginatedProducts {
  const page = Math.max(1, options?.page || 1);
  const limit = Math.max(1, options?.limit || 24);
  const all = getAllProducts();

  let minPrice = options?.minPrice;
  let maxPrice = options?.maxPrice;

  if (options?.priceRange) {
    if (options.priceRange === "under-500") {
      maxPrice = 499999;
    } else if (options.priceRange === "500-1000") {
      minPrice = 500000;
      maxPrice = 1000000;
    } else if (options.priceRange === "over-1000") {
      minPrice = 1000001;
    }
  }

  const filtered = all.filter((p) => {
    // Search query
    if (options?.search) {
      const q = options.search.toLowerCase().trim();
      const matchName = p.name.toLowerCase().includes(q);
      const matchSub = p.subtitle?.toLowerCase().includes(q);
      const matchCat = p.categoryName?.toLowerCase().includes(q);
      const matchMat = p.material?.toLowerCase().includes(q);
      const matchDesc = p.description?.toLowerCase().includes(q);
      if (!matchName && !matchSub && !matchCat && !matchMat && !matchDesc) {
        return false;
      }
    }

    // Category
    if (options?.category && options.category !== "all" && p.category !== options.category) {
      return false;
    }

    // Price
    if (minPrice !== undefined && p.price < minPrice) {
      return false;
    }
    if (maxPrice !== undefined && p.price > maxPrice) {
      return false;
    }

    // Color group matching
    if (options?.color) {
      const cQuery = options.color.toLowerCase().trim();
      const hasColor = p.colors?.some((c) => {
        const cName = c.name.toLowerCase();
        if (cQuery === "white" || cQuery === "trắng") {
          return cName.includes("trắng") || cName.includes("kem");
        }
        if (cQuery === "black" || cQuery === "đen") {
          return cName.includes("đen") || cName.includes("than");
        }
        if (cQuery === "blue" || cQuery === "xanh") {
          return cName.includes("xanh") || cName.includes("navy") || cName.includes("rêu");
        }
        if (cQuery === "brown" || cQuery === "nâu") {
          return cName.includes("nâu") || cName.includes("đất") || cName.includes("camel") || cName.includes("cafe");
        }
        if (cQuery === "beige" || cQuery === "be") {
          return cName.includes("be") || cName.includes("cát");
        }
        return cName.includes(cQuery);
      });
      if (!hasColor) return false;
    }

    // Size
    if (options?.size && !p.sizes?.includes(options.size)) {
      return false;
    }

    return true;
  });

  // Sort
  const sort = options?.sort || "featured";
  const sorted = [...filtered].sort((a, b) => {
    if (sort === "price_asc") return a.price - b.price;
    if (sort === "price_desc") return b.price - a.price;
    // Featured / default: featured and new first
    if (a.isFeatured && !b.isFeatured) return -1;
    if (!a.isFeatured && b.isFeatured) return 1;
    if (a.isNew && !b.isNew) return -1;
    if (!a.isNew && b.isNew) return 1;
    return 0;
  });

  const total = sorted.length;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const start = (page - 1) * limit;
  const items = sorted.slice(start, start + limit);

  return {
    items,
    total,
    page,
    limit,
    totalPages,
  };
}

export const productCache = new Map<string, Product>();

/**
 * Fetch paginated products with filter and search options.
 * Falls back gracefully to local catalog data if the backend API is unavailable.
 */
export async function fetchProducts(options?: CatalogQueryOptions): Promise<PaginatedProducts> {
  const page = Math.max(1, options?.page || 1);
  // Cap at 100 to avoid backend 422 validation error
  const limit = Math.min(100, Math.max(1, options?.limit || 24));

  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("limit", String(limit));

  if (options?.category && options.category !== "all") {
    params.set("category", options.category);
  }
  if (options?.search) {
    params.set("search", options.search);
  }
  if (options?.sort) {
    params.set("sort", options.sort);
  }

  // Map price parameters cleanly to backend contract (min_price & max_price)
  if (options?.priceRange && options.priceRange !== "all") {
    if (options.priceRange === "under-500") {
      params.set("max_price", "499999");
    } else if (options.priceRange === "500-1000") {
      params.set("min_price", "500000");
      params.set("max_price", "1000000");
    } else if (options.priceRange === "over-1000") {
      params.set("min_price", "1000001");
    }
  }
  if (options?.minPrice !== undefined) {
    params.set("min_price", String(options.minPrice));
  }
  if (options?.maxPrice !== undefined) {
    params.set("max_price", String(options.maxPrice));
  }

  if (options?.color) {
    params.set("color", options.color);
  }
  if (options?.size) {
    params.set("size", options.size);
  }

  const url = `${getBaseApiUrl()}/api/products?${params.toString()}`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const res = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      return filterAndPaginateLocalProducts(options);
    }

    const data = await res.json();

    // Case 1: Backend returns paginated object { items, total, ... }
    if (data && Array.isArray(data.items)) {
      const total = typeof data.total === "number" ? data.total : data.items.length;
      const apiLimit = typeof data.limit === "number" ? data.limit : (typeof data.page_size === "number" ? data.page_size : limit);
      const apiPage = typeof data.page === "number" ? data.page : page;
      const totalPages = typeof data.totalPages === "number" ? data.totalPages : (typeof data.total_pages === "number" ? data.total_pages : Math.max(1, Math.ceil(total / apiLimit)));

      data.items.forEach((p: Product) => {
        if (p.id) productCache.set(p.id, p);
        if (p.slug) productCache.set(p.slug, p);
      });

      return {
        items: data.items,
        total,
        page: apiPage,
        limit: apiLimit,
        totalPages,
      };
    }

    // Case 2: Backend returns plain array Product[]
    if (Array.isArray(data)) {
      const total = data.length;
      const totalPages = Math.max(1, Math.ceil(total / limit));
      const start = (page - 1) * limit;
      const items = data.slice(start, start + limit);

      items.forEach((p: Product) => {
        if (p.id) productCache.set(p.id, p);
        if (p.slug) productCache.set(p.slug, p);
      });

      return {
        items,
        total,
        page,
        limit,
        totalPages,
      };
    }

    return filterAndPaginateLocalProducts(options);
  } catch {
    return filterAndPaginateLocalProducts(options);
  }
}

/**
 * Fetch a single product by slug or id.
 * Falls back to local catalog if the backend API is unavailable.
 */
export async function fetchProductBySlug(slug: string): Promise<Product | null> {
  if (!slug) return null;

  const url = `${getBaseApiUrl()}/api/products/${encodeURIComponent(slug)}`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 4000);

    const res = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      if (data && (data.id || data.slug)) {
        return data as Product;
      }
    }
  } catch {
    // Fall back to local catalog
  }

  return getLocalProductBySlug(slug) || null;
}

/**
 * Fetch available categories list.
 * Falls back to CATEGORIES constant if offline.
 */
export async function fetchCategories(): Promise<CategoryInfo[]> {
  const url = `${getBaseApiUrl()}/api/products/categories`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const res = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        return data as CategoryInfo[];
      }
    }
  } catch {
    // Fall back to local categories
  }

  return CATEGORIES;
}

/**
 * Search products by query term with optional limit.
 */
export async function searchProducts(query: string, limit = 10): Promise<Product[]> {
  const trimmed = query.trim();
  if (!trimmed) return [];

  const url = `${getBaseApiUrl()}/api/products?search=${encodeURIComponent(trimmed)}&limit=${limit}`;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const res = await fetch(url, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) {
        return data.slice(0, limit) as Product[];
      }
      if (data && Array.isArray(data.items)) {
        return data.items.slice(0, limit) as Product[];
      }
    }
  } catch {
    // Fall back to local search
  }

  const q = trimmed.toLowerCase();
  return getAllProducts()
    .filter((p) => {
      return (
        p.name.toLowerCase().includes(q) ||
        p.subtitle?.toLowerCase().includes(q) ||
        p.categoryName?.toLowerCase().includes(q) ||
        p.material?.toLowerCase().includes(q) ||
        p.description?.toLowerCase().includes(q)
      );
    })
    .slice(0, limit);
}

/**
 * Fetch all available products across all pages from API without exceeding limit=100.
 * Populates productCache and returns full catalog.
 */
export async function fetchAllProducts(): Promise<Product[]> {
  try {
    const page1 = await fetchProducts({ page: 1, limit: 100 });
    let all = [...page1.items];
    if (page1.total > all.length) {
      const totalPages = Math.ceil(page1.total / 100);
      for (let p = 2; p <= totalPages; p++) {
        const next = await fetchProducts({ page: p, limit: 100 });
        all = all.concat(next.items);
      }
    }
    all.forEach((p) => {
      if (p.id) productCache.set(p.id, p);
      if (p.slug) productCache.set(p.slug, p);
    });
    return all.length > 0 ? all : getAllProducts();
  } catch {
    return getAllProducts();
  }
}

/**
 * Resolve products for an array of product IDs or slugs.
 * Checks in-memory cache, fetches missing ones concurrently, and returns found products.
 */
export async function resolveProductsByIds(ids: string[]): Promise<Product[]> {
  if (!ids || ids.length === 0) return [];
  const missing = ids.filter((id) => !productCache.has(id));

  if (missing.length > 0) {
    await Promise.all(
      missing.map(async (id) => {
        try {
          const p = await fetchProductBySlug(id);
          if (p) {
            productCache.set(p.id, p);
            productCache.set(p.slug, p);
          }
        } catch {
          // Ignore individual fetch errors
        }
      })
    );
  }

  const results: Product[] = [];
  for (const id of ids) {
    const cached = productCache.get(id);
    if (cached) {
      results.push(cached);
    } else {
      const local = getAllProducts().find((p) => p.id === id || p.slug === id);
      if (local) results.push(local);
    }
  }
  return results;
}

