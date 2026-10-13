import { Suspense } from "react";
import { notFound } from "next/navigation";
import { getAllProducts } from "../../../lib/catalog";
import { fetchProductBySlug } from "../../../lib/catalogApi";
import ProductDetail from "../../../components/shop/ProductDetail";

export const dynamic = "force-dynamic";
export const revalidate = 0;
export const dynamicParams = true;

export async function generateStaticParams() {
  const products = getAllProducts();
  return products.map((p) => ({
    slug: p.slug,
  }));
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const product = await fetchProductBySlug(slug);

  if (!product) {
    notFound();
  }

  return (
    <Suspense fallback={<div className="fit-lazy">Đang tải sản phẩm MORPH Studio…</div>}>
      <ProductDetail product={product} />
    </Suspense>
  );
}
