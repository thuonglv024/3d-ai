/**
 * MORPH Studio — Product Catalog Data Contract & Sample Inventory
 * Centralized multi-product catalog with accurate sizing charts (cm body ranges).
 * Explicitly identified as illustrative test data.
 */

export type CategoryKey = "ao-thun" | "so-mi" | "ao-khoac" | "quan" | "vay";

export interface CategoryInfo {
  key: CategoryKey;
  name: string;
  description: string;
}

export const CATEGORIES: CategoryInfo[] = [
  { key: "ao-thun", name: "Áo thun", description: "Áo thun phom suông, chất liệu cotton chải kỹ cao cấp" },
  { key: "so-mi", name: "Sơ mi", description: "Sơ mi dáng suông hiện đại từ linen và oxford thoáng khí" },
  { key: "ao-khoac", name: "Áo khoác", description: "Áo blazer, bomber và cardigan tinh tế cho mọi thời tiết" },
  { key: "quan", name: "Quần", description: "Quần tây xếp ly, chino và linen cạp chun tối giản" },
  { key: "vay", name: "Váy", description: "Chân váy xếp ly, váy chữ A và đầm suông thanh lịch" },
];

export interface ColorOption {
  name: string;
  hex: string;
}

export interface SizeRange {
  min: number;
  max: number;
}

export interface SizeRow {
  size: string;
  chest_cm?: SizeRange;
  waist_cm?: SizeRange;
  hip_cm?: SizeRange;
}

export interface SizeChart {
  name: string;
  garment: "top" | "bottom";
  /**
   * illustrative: số minh hoạ của studio.
   * user_provided: hãng công bố.
   * derived_from_flat_spec: suy ra từ số đo áo trải phẳng (không phải bảng cơ thể của hãng).
   */
  source: "illustrative" | "user_provided" | "derived_from_flat_spec";
  measurement_basis: "body_cm";
  rows: SizeRow[];
}

export interface ProductVariant {
  id?: string;
  productId?: string;
  product_id?: string;
  sku?: string;
  color?: string;
  color_name?: string;
  colorName?: string;
  color_hex?: string;
  colorHex?: string;
  size: string;
  stock?: number;
  isActive?: boolean;
  is_active?: number;
}

export interface GarmentSpec {
  size: string;
  /** Chiều rộng ngực trải phẳng (½ ngực). Vòng ngực áo = 2 × giá trị này. */
  chest_flat_cm?: number;
  chest_cm?: number;
  waist_cm?: number;
  hip_cm?: number;
  length_cm?: number;
  shoulder_cm?: number;
  sleeve_cm?: number;
}

export interface Product {
  id: string;
  slug: string;
  name: string;
  subtitle: string;
  category: CategoryKey;
  categoryName: string;
  price: number;
  originalPrice?: number;
  color: string;
  colors: ColorOption[];
  sizes: string[];
  image: string;
  gallery: string[];
  description: string;
  material: string;
  fit: string;
  details: string[];
  isNew?: boolean;
  isFeatured?: boolean;
  chart: SizeChart;
  garment_specs?: GarmentSpec[];
  garment_source?: string | null;
  variants?: ProductVariant[];
}

export const PRODUCTS: Product[] = [
  // ==========================================
  // ÁO THUN (5 sản phẩm)
  // ==========================================
  {
    id: "ao-thun-essential",
    slug: "ao-thun-essential",
    name: "Áo thun Essential Cotton",
    subtitle: "Thiết kế kinh điển với phom suông nhẹ và bề mặt chải kỹ mịn màng.",
    category: "ao-thun",
    categoryName: "Áo thun",
    price: 390000,
    originalPrice: 450000,
    color: "Trắng ngà",
    colors: [
      { name: "Trắng ngà", hex: "#f4f1ea" },
      { name: "Đen tuyền", hex: "#1f2220" },
      { name: "Xanh forest", hex: "#194e3d" },
    ],
    sizes: ["XS", "S", "M", "L", "XL"],
    image: "/products/ao-thun-essential.jpg",
    gallery: [
      "/products/ao-thun-essential.jpg",
      "/products/ao-thun-essential-detail.jpg",
    ],
    description: "Áo thun cổ tròn tối giản dệt từ sợi cotton 100% chải kỹ 240gsm. Thiết kế vừa vặn tự nhiên, vai hơi hạ, mang lại cảm giác thoải mái khi mặc cả ngày.",
    material: "100% Cotton chải kỹ 240gsm, xử lý wash sinh học chống co rút và xù lông.",
    fit: "Regular fit vừa vặn, suông nhẹ từ ngực xuống gấu áo.",
    details: [
      "Bo cổ dày 2.5cm chống giãn sau nhiều lần giặt",
      "Đường may móc xích đôi gia cố vai và sườn áo",
      "Thoáng khí và thấm hút mồ hôi tối ưu",
      "Sản phẩm mẫu thử nghiệm trong MORPH Studio",
    ],
    isFeatured: true,
    chart: {
      name: "Bảng size Áo thun Essential",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "XS", chest_cm: { min: 72, max: 82 }, waist_cm: { min: 60, max: 74 } },
        { size: "S", chest_cm: { min: 82, max: 90 }, waist_cm: { min: 66, max: 80 } },
        { size: "M", chest_cm: { min: 90, max: 98 }, waist_cm: { min: 74, max: 88 } },
        { size: "L", chest_cm: { min: 98, max: 106 }, waist_cm: { min: 82, max: 96 } },
        { size: "XL", chest_cm: { min: 106, max: 115 }, waist_cm: { min: 90, max: 106 } },
      ],
    },
  },
  {
    id: "ao-thun-oversized-heavyweight",
    slug: "ao-thun-oversized-heavyweight",
    name: "Áo thun Heavyweight Oversized",
    subtitle: "Chất vải 280gsm đầm tay, phom hộp đứng cá tính và phóng khoáng.",
    category: "ao-thun",
    categoryName: "Áo thun",
    price: 450000,
    color: "Nâu đất",
    colors: [
      { name: "Nâu đất", hex: "#634735" },
      { name: "Xám tiêu", hex: "#7a7e80" },
      { name: "Đen tuyền", hex: "#222423" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/ao-thun-oversized-heavyweight.jpg",
    gallery: [
      "/products/ao-thun-oversized-heavyweight.jpg",
      "/products/ao-thun-oversized-heavyweight-detail.jpg",
    ],
    description: "Định lượng vải 280gsm tạo phom dáng hộp cứng cáp, vai rơi phóng khoáng. Một lựa chọn hiện đại cho phong cách tối giản streetwear.",
    material: "100% Cotton chải kỹ 280gsm dệt sợi đôi.",
    fit: "Oversized fit rộng rãi, vai hạ sâu, ống tay lửng.",
    details: [
      "Định lượng dày dặn giữ phom hoàn hảo",
      "Đường may trần đè 3 kim tỉ mỉ",
      "Gấu áo xẻ tà nhẹ tăng độ linh hoạt",
    ],
    isNew: true,
    chart: {
      name: "Bảng size Áo thun Heavyweight",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 84, max: 92 }, waist_cm: { min: 68, max: 82 } },
        { size: "M", chest_cm: { min: 92, max: 102 }, waist_cm: { min: 76, max: 90 } },
        { size: "L", chest_cm: { min: 102, max: 110 }, waist_cm: { min: 84, max: 98 } },
        { size: "XL", chest_cm: { min: 110, max: 120 }, waist_cm: { min: 92, max: 108 } },
      ],
    },
  },
  {
    id: "ao-thun-supima-crewneck",
    slug: "ao-thun-supima-crewneck",
    name: "Áo thun Supima Cổ tròn",
    subtitle: "Sợi bông sợi dài Supima thượng hạng, mềm mượt và bóng nhẹ tự nhiên.",
    category: "ao-thun",
    categoryName: "Áo thun",
    price: 490000,
    color: "Kem vani",
    colors: [
      { name: "Kem vani", hex: "#f0ece1" },
      { name: "Xanh navy", hex: "#233342" },
      { name: "Đen nhám", hex: "#1c1e1d" },
    ],
    sizes: ["XS", "S", "M", "L", "XL"],
    image: "/products/ao-thun-supima-crewneck.jpg",
    gallery: [
      "/products/ao-thun-supima-crewneck.jpg",
      "/products/ao-thun-supima-crewneck-detail.jpg",
    ],
    description: "Được dệt từ bông Supima cao cấp có sợi dài hơn 35% so với cotton thông thường, đem lại cảm giác êm ái, bền màu và giữ phom qua hàng trăm lần giặt.",
    material: "100% Supima Cotton sợi dài cao cấp.",
    fit: "Tailored fit ôm nhẹ gọn gàng.",
    details: [
      "Chất liệu mềm mại, không gây kích ứng da nhạy cảm",
      "Bề mặt bóng mờ tinh tế của sợi bông tuyển chọn",
      "Kháng khuẩn tự nhiên và hút ẩm vượt trội",
    ],
    chart: {
      name: "Bảng size Supima Crewneck",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "XS", chest_cm: { min: 72, max: 80 }, waist_cm: { min: 60, max: 72 } },
        { size: "S", chest_cm: { min: 80, max: 88 }, waist_cm: { min: 66, max: 78 } },
        { size: "M", chest_cm: { min: 88, max: 96 }, waist_cm: { min: 74, max: 86 } },
        { size: "L", chest_cm: { min: 96, max: 104 }, waist_cm: { min: 82, max: 94 } },
        { size: "XL", chest_cm: { min: 104, max: 112 }, waist_cm: { min: 90, max: 102 } },
      ],
    },
  },
  {
    id: "ao-thun-oricano-nam",
    slug: "ao-thun-oricano-nam",
    name: "Áo thun nam Oricano Basic",
    subtitle:
      "Cotton co giãn 4 chiều, khử mùi, phom gọn vừa người — số đo áo lấy từ bảng size của hãng.",
    category: "ao-thun",
    categoryName: "Áo thun",
    // Giá minh hoạ cho môi trường thử nghiệm, không phải giá bán thật.
    price: 390000,
    originalPrice: 450000,
    color: "Đen",
    colors: [
      { name: "Đen", hex: "#1c1d1c" },
      { name: "Trắng", hex: "#efece5" },
    ],
    sizes: ["S", "M", "L", "XL", "XXL"],
    image: "/products/v2/ao-thun-oricano-nam.jpg",
    gallery: [
      "/products/v2/ao-thun-oricano-nam.jpg",
      "/products/v2/ao-thun-oricano-nam-detail.jpg",
    ],
    description:
      "Áo thun nam cổ tròn phom gọn, vải cotton co giãn 4 chiều, xử lý khử mùi và không xù. Số đo may (dài áo, ½ ngực, dài tay, rộng vai) lấy từ bảng size của hãng; ảnh sản phẩm trong studio là ảnh minh hoạ do MORPH tạo, không phải ảnh của hãng.",
    material: "Cotton co giãn 4 chiều, xử lý khử mùi, bề mặt mịn không xù.",
    fit: "Regular fit gọn: ôm vừa vai và ngực, không buông rộng.",
    details: [
      "Dài áo 61–69 cm, ½ ngực 41–49 cm theo size S–XXL (số đo hãng công bố)",
      "Vải co giãn 4 chiều, không xù không nhăn",
      "Xử lý khử mùi trên bề mặt vải",
      "Đường may gấu áo và tay áo may đôi",
    ],
    isNew: true,
    chart: {
      // Hãng chỉ công bố bảng cao × cân; khoảng vòng cơ thể dưới đây SUY RA từ
      // chu vi áo phẳng trừ ease 2–10 cm, không phải bảng cơ thể của hãng.
      name: "Bảng size Oricano (suy ra từ số đo áo phẳng)",
      garment: "top",
      source: "derived_from_flat_spec",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 72, max: 80 }, waist_cm: { min: 62, max: 74 } },
        { size: "M", chest_cm: { min: 76, max: 84 }, waist_cm: { min: 66, max: 78 } },
        { size: "L", chest_cm: { min: 80, max: 88 }, waist_cm: { min: 70, max: 82 } },
        { size: "XL", chest_cm: { min: 84, max: 92 }, waist_cm: { min: 74, max: 86 } },
        { size: "XXL", chest_cm: { min: 88, max: 96 }, waist_cm: { min: 78, max: 90 } },
      ],
    },
    garment_specs: [
      { size: "S", chest_flat_cm: 41, chest_cm: 82, length_cm: 61, sleeve_cm: 17, shoulder_cm: 38 },
      { size: "M", chest_flat_cm: 43, chest_cm: 86, length_cm: 63, sleeve_cm: 18, shoulder_cm: 39 },
      { size: "L", chest_flat_cm: 45, chest_cm: 90, length_cm: 65, sleeve_cm: 19, shoulder_cm: 40 },
      { size: "XL", chest_flat_cm: 47, chest_cm: 94, length_cm: 67, sleeve_cm: 20, shoulder_cm: 41 },
      { size: "XXL", chest_flat_cm: 49, chest_cm: 98, length_cm: 69, sleeve_cm: 21, shoulder_cm: 42 },
    ],
    garment_source:
      "Bảng size Oricano (ảnh hãng): dài áo / ½ ngực / dài tay / rộng vai cho S–2XL; hãng gợi ý size theo cao × cân",
  },
  {
    id: "ao-thun-waffle-long-sleeve",
    slug: "ao-thun-waffle-long-sleeve",
    name: "Áo thun Waffle Dệt tổ ong",
    subtitle: "Tay dài kết cấu dệt tổ ong giữ ấm nhẹ, lý tưởng cho thời tiết giao mùa.",
    category: "ao-thun",
    categoryName: "Áo thun",
    price: 520000,
    color: "Xanh rêu",
    colors: [
      { name: "Xanh rêu", hex: "#3f5446" },
      { name: "Xám ghi", hex: "#73787b" },
      { name: "Trắng ngà", hex: "#f2eee7" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/ao-thun-waffle-long-sleeve.jpg",
    gallery: [
      "/products/ao-thun-waffle-long-sleeve.jpg",
      "/products/ao-thun-waffle-long-sleeve-detail.jpg",
    ],
    description: "Cấu trúc dệt waffle tạo các túi khí nhỏ giữ nhiệt ấm áp tự nhiên nhưng vẫn thông thoáng. Bo tay thun đàn hồi giữ tay áo gọn gàng khi cử động.",
    material: "95% Cotton waffle, 5% Spandex tăng độ đàn hồi.",
    fit: "Comfortable regular fit, tay dài bo chun.",
    details: [
      "Kết cấu dệt tổ ong 3D nổi bật",
      "Bo tay co giãn bền bỉ không dão",
      "Thích hợp mặc lót trong hoặc mặc ngoài đơn lẻ",
    ],
    chart: {
      name: "Bảng size Áo Waffle Long Sleeve",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 82, max: 90 }, waist_cm: { min: 66, max: 80 } },
        { size: "M", chest_cm: { min: 90, max: 98 }, waist_cm: { min: 74, max: 88 } },
        { size: "L", chest_cm: { min: 98, max: 106 }, waist_cm: { min: 82, max: 96 } },
        { size: "XL", chest_cm: { min: 106, max: 116 }, waist_cm: { min: 90, max: 104 } },
      ],
    },
  },
  {
    id: "ao-thun-striped-relaxed",
    slug: "ao-thun-striped-relaxed",
    name: "Áo thun Kẻ sọc Relaxed",
    subtitle: "Họa tiết sọc ngang Breton cổ điển trên nền vải dệt cotton mềm.",
    category: "ao-thun",
    categoryName: "Áo thun",
    price: 420000,
    color: "Trắng sọc xanh",
    colors: [
      { name: "Trắng sọc xanh", hex: "#d8e1e8" },
      { name: "Kem sọc nâu", hex: "#e2d5c3" },
    ],
    sizes: ["XS", "S", "M", "L"],
    image: "/products/ao-thun-striped-relaxed.jpg",
    gallery: [
      "/products/ao-thun-striped-relaxed.jpg",
      "/products/ao-thun-striped-relaxed-detail.jpg",
    ],
    description: "Lấy cảm hứng từ phong cách thủy thủ Pháp, áo thun sọc kẻ mang đến vẻ đẹp thanh lịch vượt thời gian. Họa tiết dệt sợi nhuộm màu bền chặt.",
    material: "100% Cotton nhuộm sợi tự nhiên.",
    fit: "Relaxed fit suông rộng thoải mái.",
    details: [
      "Sọc dệt từ sợi nhuộm (yarn-dyed) không bay màu",
      "Cổ viền đơn sắc thanh lịch",
      "Vạt áo may phẳng đều tay",
    ],
    chart: {
      name: "Bảng size Áo Striped Relaxed",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "XS", chest_cm: { min: 72, max: 80 }, waist_cm: { min: 60, max: 72 } },
        { size: "S", chest_cm: { min: 80, max: 88 }, waist_cm: { min: 66, max: 78 } },
        { size: "M", chest_cm: { min: 88, max: 96 }, waist_cm: { min: 74, max: 86 } },
        { size: "L", chest_cm: { min: 96, max: 105 }, waist_cm: { min: 82, max: 95 } },
      ],
    },
  },

  // ==========================================
  // SƠ MI (5 sản phẩm)
  // ==========================================
  {
    id: "so-mi-oxford-classic",
    slug: "so-mi-oxford-classic",
    name: "Sơ mi Oxford Dáng suông",
    subtitle: "Chất vải oxford dày dặn, cổ bẻ có khuy cài gọn gàng chuẩn mực.",
    category: "so-mi",
    categoryName: "Sơ mi",
    price: 620000,
    originalPrice: 700000,
    color: "Trắng ngọc",
    colors: [
      { name: "Trắng ngọc", hex: "#fcfbf7" },
      { name: "Xanh nhạt", hex: "#cde0eb" },
      { name: "Hồng nhạt", hex: "#eedbd9" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/so-mi-oxford-classic.jpg",
    gallery: [
      "/products/so-mi-oxford-classic.jpg",
      "/products/so-mi-oxford-classic-detail.jpg",
    ],
    description: "Sơ mi Oxford dệt cấu trúc hạt râm truyền thống. Phom dáng suông nhẹ nhàng kết hợp khuy cài cổ giữ ve áo ngay ngắn, phù hợp cả công sở lẫn dạo phố.",
    material: "100% Cotton Oxford 80/2 dệt nổi.",
    fit: "Regular straight fit suông thẳng hiện đại.",
    details: [
      "Khuy cài xà cừ tự nhiên sáng bóng",
      "Túi ngực đơn phong cách tối giản",
      "Đường may cuộn cuốn mép chống xơ sợi",
    ],
    isFeatured: true,
    chart: {
      name: "Bảng size Sơ mi Oxford",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 82, max: 90 }, waist_cm: { min: 68, max: 80 } },
        { size: "M", chest_cm: { min: 90, max: 98 }, waist_cm: { min: 76, max: 88 } },
        { size: "L", chest_cm: { min: 98, max: 106 }, waist_cm: { min: 84, max: 96 } },
        { size: "XL", chest_cm: { min: 106, max: 115 }, waist_cm: { min: 92, max: 105 } },
      ],
    },
  },
  {
    id: "so-mi-linen-thoang-khi",
    slug: "so-mi-linen-thoang-khi",
    name: "Sơ mi Linen Thoáng khí",
    subtitle: "Linen tự nhiên 100% mộc mạc, thấm hút nhanh và siêu nhẹ.",
    category: "so-mi",
    categoryName: "Sơ mi",
    price: 680000,
    color: "Kem cát",
    colors: [
      { name: "Kem cát", hex: "#ded4be" },
      { name: "Nâu olive", hex: "#5a5b47" },
      { name: "Trắng tinh", hex: "#ffffff" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/so-mi-linen-thoang-khi.jpg",
    gallery: [
      "/products/so-mi-linen-thoang-khi.jpg",
      "/products/so-mi-linen-thoang-khi-detail.jpg",
    ],
    description: "Chất liệu sợi lanh tự nhiên từ vùng Normandy mát lạnh, có nếp nhăn tự nhiên đặc trưng mang lại vẻ phóng khoáng, thanh lịch không gắng gượng.",
    material: "100% Linen tự nhiên đã giặt mềm enzym.",
    fit: "Relaxed fit rộng rãi, thoáng gió.",
    details: [
      "Khả năng tản nhiệt và thoát hơi ẩm cao gấp 2 lần cotton",
      "Xử lý enzym làm mềm sợi mà không mất đi độ bền",
      "Cúc áo khắc logo MORPH Studio tinh xảo",
    ],
    isNew: true,
    chart: {
      name: "Bảng size Sơ mi Linen",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 82, max: 91 }, waist_cm: { min: 68, max: 82 } },
        { size: "M", chest_cm: { min: 91, max: 99 }, waist_cm: { min: 77, max: 90 } },
        { size: "L", chest_cm: { min: 99, max: 107 }, waist_cm: { min: 85, max: 98 } },
        { size: "XL", chest_cm: { min: 107, max: 116 }, waist_cm: { min: 93, max: 106 } },
      ],
    },
  },
  {
    id: "so-mi-cuban-collar",
    slug: "so-mi-cuban-collar",
    name: "Sơ mi Cổ Cuba Nghỉ dưỡng",
    subtitle: "Cổ bẻ chữ V mở rộng, tay ngắn mang tinh thần mùa hè thư thái.",
    category: "so-mi",
    categoryName: "Sơ mi",
    price: 590000,
    color: "Xanh navy",
    colors: [
      { name: "Xanh navy", hex: "#1e293b" },
      { name: "Nâu đất", hex: "#5c4333" },
      { name: "Xanh ngọc râm", hex: "#2b5650" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/so-mi-cuban-collar.jpg",
    gallery: [
      "/products/so-mi-cuban-collar.jpg",
      "/products/so-mi-cuban-collar-detail.jpg",
    ],
    description: "Cổ áo Cuba mở không khuy gài trên cùng mang đến nét cuốn hút đậm chất retro. Vải pha cotton-tencel rủ nhẹ, mượt mà khi chạm vào da.",
    material: "60% Tencel, 40% Cotton dệt chéo mềm.",
    fit: "Boxy fit thân vuông ngắn, gấu áo ngang.",
    details: [
      "Cổ áo camp collar chữ V mở phóng khoáng",
      "Vạt áo ngang có thể mặc buông hoặc đóng thùng",
      "Chất liệu chống nhăn tự nhiên tiện bảo quản",
    ],
    chart: {
      name: "Bảng size Sơ mi Cổ Cuba",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 84, max: 92 }, waist_cm: { min: 70, max: 82 } },
        { size: "M", chest_cm: { min: 92, max: 100 }, waist_cm: { min: 78, max: 90 } },
        { size: "L", chest_cm: { min: 100, max: 108 }, waist_cm: { min: 86, max: 98 } },
        { size: "XL", chest_cm: { min: 108, max: 118 }, waist_cm: { min: 94, max: 108 } },
      ],
    },
  },
  {
    id: "so-mi-denim-nhe",
    slug: "so-mi-denim-nhe",
    name: "Sơ mi Denim Dệt nhẹ",
    subtitle: "Chất denim mềm 6.5oz, wash màu chàm cổ điển bền bỉ với thời gian.",
    category: "so-mi",
    categoryName: "Sơ mi",
    price: 720000,
    color: "Xanh chàm",
    colors: [
      { name: "Xanh chàm", hex: "#2d4560" },
      { name: "Xanh wash sáng", hex: "#6c89a8" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/so-mi-denim-nhe.jpg",
    gallery: [
      "/products/so-mi-denim-nhe.jpg",
      "/products/so-mi-denim-nhe-detail.jpg",
    ],
    description: "Sơ mi denim định lượng nhẹ 6.5oz được wash đá sinh học tạo sắc chàm mờ cuốn hút. Có thể mặc riêng lẻ hoặc làm áo khoác mỏng nhẹ bên ngoài.",
    material: "100% Cotton Denim 6.5oz dệt thoi.",
    fit: "Regular fit dáng thẳng khoẻ khoắn.",
    details: [
      "Khuy bấm kim loại đồng cổ điển",
      "Túi ốp đôi có nắp trước ngực",
      "Đường chần chỉ nổi màu vàng nghệ đặc trưng",
    ],
    chart: {
      name: "Bảng size Sơ mi Denim",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 83, max: 91 }, waist_cm: { min: 69, max: 81 } },
        { size: "M", chest_cm: { min: 91, max: 99 }, waist_cm: { min: 77, max: 89 } },
        { size: "L", chest_cm: { min: 99, max: 107 }, waist_cm: { min: 85, max: 97 } },
        { size: "XL", chest_cm: { min: 107, max: 117 }, waist_cm: { min: 93, max: 107 } },
      ],
    },
  },
  {
    id: "so-mi-co-tru-minimal",
    slug: "so-mi-co-tru-minimal",
    name: "Sơ mi Cổ trụ Tối giản",
    subtitle: "Cổ tàu gọn gàng, nẹp che khuy tinh tế mang âm hưởng Á Đông hiện đại.",
    category: "so-mi",
    categoryName: "Sơ mi",
    price: 650000,
    color: "Trắng ngọc",
    colors: [
      { name: "Trắng ngọc", hex: "#f9f8f4" },
      { name: "Xám nhạt", hex: "#c4c7c5" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/so-mi-co-tru-minimal.jpg",
    gallery: [
      "/products/so-mi-co-tru-minimal.jpg",
      "/products/so-mi-co-tru-minimal-detail.jpg",
    ],
    description: "Thiết kế cổ trụ cao 3cm kết hợp hàng nẹp giấu khuy mang đến diện mạo gọn gàng, sạch sẽ tuyệt đối cho người mặc.",
    material: "80% Cotton Ai Cập, 20% Silk tạo độ óng nhẹ.",
    fit: "Slim regular fit vừa vặn tôn dáng.",
    details: [
      "Nẹp áo giấu hàng cúc thanh lịch",
      "Cổ trụ đệm keo nhập khẩu giữ form đứng",
      "Vải mềm mượt chống nhăn nhẹ",
    ],
    chart: {
      name: "Bảng size Sơ mi Cổ trụ",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 81, max: 89 }, waist_cm: { min: 67, max: 79 } },
        { size: "M", chest_cm: { min: 89, max: 97 }, waist_cm: { min: 75, max: 87 } },
        { size: "L", chest_cm: { min: 97, max: 105 }, waist_cm: { min: 83, max: 95 } },
        { size: "XL", chest_cm: { min: 105, max: 114 }, waist_cm: { min: 91, max: 104 } },
      ],
    },
  },

  // ==========================================
  // ÁO KHOÁC (4 sản phẩm)
  // ==========================================
  {
    id: "ao-khoac-blazer-linen",
    slug: "ao-khoac-blazer-linen",
    name: "Áo khoác Blazer Khuy đơn",
    subtitle: "Blazer một hàng khuy không đệm vai cứng, thanh lịch và mềm mại.",
    category: "ao-khoac",
    categoryName: "Áo khoác",
    price: 1290000,
    originalPrice: 1550000,
    color: "Be sáng",
    colors: [
      { name: "Be sáng", hex: "#ded6c4" },
      { name: "Xanh forest", hex: "#194e3d" },
      { name: "Đen tuyền", hex: "#1d201e" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/ao-khoac-blazer-linen.jpg",
    gallery: [
      "/products/ao-khoac-blazer-linen.jpg",
      "/products/ao-khoac-blazer-linen-detail.jpg",
    ],
    description: "Áo khoác blazer may đo theo cấu trúc unconstructed tự nhiên, vai không đệm mút dày mang đến phom dáng mềm mại, thanh lịch dễ phối đồ.",
    material: "Vải Linen pha Cotton nhập khẩu cao cấp, lót lụa habotai nửa thân.",
    fit: "Relaxed tailored fit tôn dáng không gò bó.",
    details: [
      "Cấu trúc vai tự nhiên (unpadded) thoải mái",
      "Khuy sừng đúc nguyên khối chống xước",
      "Túi áo mổ đôi có nắp lật linh hoạt",
    ],
    isFeatured: true,
    chart: {
      name: "Bảng size Blazer Linen",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 84, max: 92 }, waist_cm: { min: 70, max: 82 } },
        { size: "M", chest_cm: { min: 92, max: 100 }, waist_cm: { min: 78, max: 90 } },
        { size: "L", chest_cm: { min: 100, max: 108 }, waist_cm: { min: 86, max: 98 } },
        { size: "XL", chest_cm: { min: 108, max: 118 }, waist_cm: { min: 94, max: 108 } },
      ],
    },
  },
  {
    id: "ao-khoac-bomber-minimal",
    slug: "ao-khoac-bomber-minimal",
    name: "Áo khoác Bomber Gió nhẹ",
    subtitle: "Chất liệu dù trượt nước, lót lưới thông thoáng và khóa kéo kim loại.",
    category: "ao-khoac",
    categoryName: "Áo khoác",
    price: 950000,
    color: "Đen nhám",
    colors: [
      { name: "Đen nhám", hex: "#222425" },
      { name: "Xanh rêu", hex: "#3b4f42" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/ao-khoac-bomber-minimal.jpg",
    gallery: [
      "/products/ao-khoac-bomber-minimal.jpg",
      "/products/ao-khoac-bomber-minimal-detail.jpg",
    ],
    description: "Mẫu bomber cổ điển được tái hiện với phong cách tối giản. Vải dù kỹ thuật cao trượt nước nhẹ hạt sen, cản gió tốt trong những ngày chuyển mùa.",
    material: "100% Nylon trượt nước công nghệ DWR, lót lưới polyester thoáng khí.",
    fit: "Semi-oversized fit bo chun gấu và cổ tay.",
    details: [
      "Khóa kéo kim loại hai chiều YKK êm mượt",
      "Túi trong có khóa an toàn đựng điện thoại",
      "Bo cổ và gấu dệt rib dầy dặn",
    ],
    isNew: true,
    chart: {
      name: "Bảng size Bomber Minimal",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 85, max: 93 }, waist_cm: { min: 70, max: 83 } },
        { size: "M", chest_cm: { min: 93, max: 101 }, waist_cm: { min: 78, max: 91 } },
        { size: "L", chest_cm: { min: 101, max: 110 }, waist_cm: { min: 86, max: 100 } },
        { size: "XL", chest_cm: { min: 110, max: 120 }, waist_cm: { min: 94, max: 110 } },
      ],
    },
  },
  {
    id: "ao-khoac-trench-coat-ngan",
    slug: "ao-khoac-trench-coat-ngan",
    name: "Áo khoác Trench Coat Dáng lửng",
    subtitle: "Phom áo trench coat lửng hiện đại, hai hàng khuy và đai lưng tinh tế.",
    category: "ao-khoac",
    categoryName: "Áo khoác",
    price: 1450000,
    color: "Nâu lạc đà",
    colors: [
      { name: "Nâu lạc đà", hex: "#a4815a" },
      { name: "Đen tuyền", hex: "#1c1e1d" },
    ],
    sizes: ["S", "M", "L"],
    image: "/products/ao-khoac-trench-coat-ngan.jpg",
    gallery: [
      "/products/ao-khoac-trench-coat-ngan.jpg",
      "/products/ao-khoac-trench-coat-ngan-detail.jpg",
    ],
    description: "Phiên bản dáng lửng trẻ trung của mẫu trench coat kinh điển. Chiều dài qua hông vừa phải giúp tôn dáng đôi chân, phối cùng đai thắt eo điều chỉnh linh hoạt.",
    material: "Vải Gabardine cotton chéo dày dặn cản gió.",
    fit: "Tailored crop fit dáng lửng tôn eo.",
    details: [
      "Hàng khuy kép đôi vạt đắp kinh điển",
      "Đai thắt lưng có khóa kim loại chống gỉ",
      "Cầu vai và ve áo may đo sắc nét",
    ],
    chart: {
      name: "Bảng size Trench Coat Lửng",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 80, max: 88 }, waist_cm: { min: 64, max: 76 } },
        { size: "M", chest_cm: { min: 88, max: 96 }, waist_cm: { min: 72, max: 84 } },
        { size: "L", chest_cm: { min: 96, max: 105 }, waist_cm: { min: 80, max: 94 } },
      ],
    },
  },
  {
    id: "ao-khoac-cardigan-len",
    slug: "ao-khoac-cardigan-len",
    name: "Áo khoác Cardigan Dệt kim",
    subtitle: "Len dệt mũi gân mềm xốp, cổ V sâu cài khuy sừng ấm áp.",
    category: "ao-khoac",
    categoryName: "Áo khoác",
    price: 790000,
    color: "Nâu cà phê",
    colors: [
      { name: "Nâu cà phê", hex: "#4b392b" },
      { name: "Kem yến mạch", hex: "#e7decb" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/ao-khoac-cardigan-len.jpg",
    gallery: [
      "/products/ao-khoac-cardigan-len.jpg",
      "/products/ao-khoac-cardigan-len-detail.jpg",
    ],
    description: "Cardigan dệt kim gân rib với độ dày dặn vừa phải, êm ái khi tiếp xúc trực tiếp với da mà không gây dặm ngứa. Thiết kế cổ V dễ phối cùng áo thun hay sơ mi bên trong.",
    material: "60% Sợi len Merino pha 40% Acrylic xơ dài giữ nhiệt.",
    fit: "Relaxed slouchy fit vai trễ nhẹ nhàng.",
    details: [
      "Sợi len xử lý chống xù và co khi giặt",
      "Khuy sừng đúc 4 lỗ hoàn thiện thủ công",
      "Túi ốp vuông hai bên hông tiện dụng",
    ],
    chart: {
      name: "Bảng size Cardigan Dệt kim",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", chest_cm: { min: 82, max: 90 }, waist_cm: { min: 66, max: 80 } },
        { size: "M", chest_cm: { min: 90, max: 98 }, waist_cm: { min: 74, max: 88 } },
        { size: "L", chest_cm: { min: 98, max: 107 }, waist_cm: { min: 82, max: 96 } },
        { size: "XL", chest_cm: { min: 107, max: 118 }, waist_cm: { min: 90, max: 106 } },
      ],
    },
  },

  // ==========================================
  // QUẦN (4 sản phẩm) - Lưu ý: Garment là "bottom", cần waist_cm và hip_cm!
  // ==========================================
  {
    id: "quan-tay-pleated-wide-leg",
    slug: "quan-tay-pleated-wide-leg",
    name: "Quần tây Xếp ly Dáng rộng",
    subtitle: "Xếp ly đôi phía trước, ống suông rộng rủ tạo vẻ đẹp thanh lịch.",
    category: "quan",
    categoryName: "Quần",
    price: 790000,
    originalPrice: 920000,
    color: "Đen tuyền",
    colors: [
      { name: "Đen tuyền", hex: "#1f2120" },
      { name: "Xám than", hex: "#484d4b" },
      { name: "Nâu hạt dẻ", hex: "#5e4b3c" },
    ],
    sizes: ["28", "29", "30", "31", "32"],
    image: "/products/quan-tay-pleated-wide-leg.jpg",
    gallery: [
      "/products/quan-tay-pleated-wide-leg.jpg",
      "/products/quan-tay-pleated-wide-leg-detail.jpg",
    ],
    description: "Quần âu xếp ly kép với phom dáng suông rộng thời thượng. Chất vải tuyết mưa rủ tự nhiên, đứng phom và ít nhăn suốt ngày dài làm việc.",
    material: "70% Polyester tái chế, 28% Rayon mềm rủ, 2% Spandex.",
    fit: "Wide-leg cạp cao vừa, ống suông rộng rủ đẹp mắt.",
    details: [
      "Xếp ly đôi sâu tạo độ rộng và cử động thoải mái",
      "Cạp quần may tỉ mỉ có tăng đơ chun ẩn phía trong",
      "Gấu quần may giấu chỉ sắc sảo",
    ],
    isFeatured: true,
    chart: {
      name: "Bảng size Quần Pleated Wide-leg",
      garment: "bottom",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "28", waist_cm: { min: 66, max: 72 }, hip_cm: { min: 86, max: 92 } },
        { size: "29", waist_cm: { min: 70, max: 76 }, hip_cm: { min: 90, max: 96 } },
        { size: "30", waist_cm: { min: 74, max: 80 }, hip_cm: { min: 94, max: 100 } },
        { size: "31", waist_cm: { min: 78, max: 84 }, hip_cm: { min: 98, max: 104 } },
        { size: "32", waist_cm: { min: 82, max: 88 }, hip_cm: { min: 102, max: 108 } },
      ],
    },
  },
  {
    id: "quan-khaki-chino-straight",
    slug: "quan-khaki-chino-straight",
    name: "Quần Khaki Chino Ống đứng",
    subtitle: "Chino cotton twill bền chắc, ống đứng thẳng thắn cho phong cách thường nhật.",
    category: "quan",
    categoryName: "Quần",
    price: 650000,
    color: "Be cát",
    colors: [
      { name: "Be cát", hex: "#d8cbb5" },
      { name: "Xanh rêu", hex: "#3e5243" },
      { name: "Xanh navy", hex: "#232e3d" },
    ],
    sizes: ["28", "29", "30", "31", "32"],
    image: "/products/quan-khaki-chino-straight.jpg",
    gallery: [
      "/products/quan-khaki-chino-straight.jpg",
      "/products/quan-khaki-chino-straight-detail.jpg",
    ],
    description: "Quần chino kinh điển dệt chéo từ cotton 100% bền bỉ. Phom ống đứng chuẩn mực kết hợp xử lý enzyme giúp bề mặt vải mềm mại ngay lần mặc đầu tiên.",
    material: "98% Cotton Twill 8.5oz, 2% Elastane co giãn nhẹ.",
    fit: "Straight fit ống đứng cân đối.",
    details: [
      "Túi chéo hai bên và túi mổ sau có khuy",
      "Khóa kéo kim loại và khuy sừng cao cấp",
      "Đường chần đũng quần gia cố chống rách",
    ],
    chart: {
      name: "Bảng size Quần Chino",
      garment: "bottom",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "28", waist_cm: { min: 68, max: 74 }, hip_cm: { min: 87, max: 93 } },
        { size: "29", waist_cm: { min: 72, max: 78 }, hip_cm: { min: 91, max: 97 } },
        { size: "30", waist_cm: { min: 76, max: 82 }, hip_cm: { min: 95, max: 101 } },
        { size: "31", waist_cm: { min: 80, max: 86 }, hip_cm: { min: 99, max: 105 } },
        { size: "32", waist_cm: { min: 84, max: 90 }, hip_cm: { min: 103, max: 109 } },
      ],
    },
  },
  {
    id: "quan-linen-cap-chun",
    slug: "quan-linen-cap-chun",
    name: "Quần Linen Cạp chun Thư giãn",
    subtitle: "Linen nguyên chất mát rượi, cạp chun kèm dây rút thoải mái tối đa.",
    category: "quan",
    categoryName: "Quần",
    price: 620000,
    color: "Trắng ngà",
    colors: [
      { name: "Trắng ngà", hex: "#f0ede3" },
      { name: "Nâu đất", hex: "#5b483b" },
      { name: "Xanh navy", hex: "#223140" },
    ],
    sizes: ["S", "M", "L", "XL"],
    image: "/products/quan-linen-cap-chun.jpg",
    gallery: [
      "/products/quan-linen-cap-chun.jpg",
      "/products/quan-linen-cap-chun-detail.jpg",
    ],
    description: "Được thiết kế cho những ngày nghỉ ngơi hoặc làm việc linh hoạt, quần linen cạp chun đem đến sự thông thoáng tuyệt đối nhờ chất lanh tự nhiên giặt mềm.",
    material: "100% Linen hữu cơ tự nhiên.",
    fit: "Relaxed tapered fit ống hơi túm nhẹ ở gấu.",
    details: [
      "Cạp thun co giãn toàn phần có dây rút điều chỉnh",
      "Túi sâu hai bên để vừa ví và điện thoại",
      "Vải giặt mềm chống kích ứng da",
    ],
    isNew: true,
    chart: {
      name: "Bảng size Quần Linen Cạp chun",
      garment: "bottom",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "S", waist_cm: { min: 66, max: 76 }, hip_cm: { min: 88, max: 96 } },
        { size: "M", waist_cm: { min: 74, max: 84 }, hip_cm: { min: 94, max: 102 } },
        { size: "L", waist_cm: { min: 82, max: 92 }, hip_cm: { min: 100, max: 108 } },
        { size: "XL", waist_cm: { min: 90, max: 100 }, hip_cm: { min: 106, max: 114 } },
      ],
    },
  },
  {
    id: "quan-jeans-regular-selvedge",
    slug: "quan-jeans-regular-selvedge",
    name: "Quần Jeans Regular Selvedge",
    subtitle: "Denim biên đỏ dệt thoi con thoi 13oz, phom suông đứng cổ điển.",
    category: "quan",
    categoryName: "Quần",
    price: 890000,
    color: "Xanh chàm đậm",
    colors: [
      { name: "Xanh chàm đậm", hex: "#1d2b3a" },
      { name: "Đen wash", hex: "#2b2d2f" },
    ],
    sizes: ["28", "29", "30", "31", "32"],
    image: "/products/quan-jeans-regular-selvedge.jpg",
    gallery: [
      "/products/quan-jeans-regular-selvedge.jpg",
      "/products/quan-jeans-regular-selvedge-detail.jpg",
    ],
    description: "Quần jeans selvedge dệt trên máy dệt con thoi cổ xưa với đường biên đỏ đặc trưng. Chất vải 13oz đứng phom, sẽ tạo vệt phai tự nhiên độc nhất theo thời gian sử dụng.",
    material: "100% Cotton Selvedge Denim 13oz dệt thoi.",
    fit: "Regular fit ống suông thẳng đứng cổ điển.",
    details: [
      "Đường viền biên đỏ selvedge khi xắn gấu",
      "Đinh tán và khuy đồng đúc nguyên khối",
      "Túi lót bằng vải cotton dày dặn",
    ],
    chart: {
      name: "Bảng size Quần Jeans Selvedge",
      garment: "bottom",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "28", waist_cm: { min: 69, max: 75 }, hip_cm: { min: 88, max: 94 } },
        { size: "29", waist_cm: { min: 73, max: 79 }, hip_cm: { min: 92, max: 98 } },
        { size: "30", waist_cm: { min: 77, max: 83 }, hip_cm: { min: 96, max: 102 } },
        { size: "31", waist_cm: { min: 81, max: 87 }, hip_cm: { min: 100, max: 106 } },
        { size: "32", waist_cm: { min: 85, max: 91 }, hip_cm: { min: 104, max: 110 } },
      ],
    },
  },

  // ==========================================
  // VÁY (4 sản phẩm) - 3 chân váy (bottom) + 1 đầm (top)
  // ==========================================
  {
    id: "chan-vay-pleated-midi",
    slug: "chan-vay-pleated-midi",
    name: "Chân váy Xếp ly Dáng dài Midi",
    subtitle: "Dập ly sắc sảo uyển chuyển, cạp bản vừa ôm khít tôn vòng eo.",
    category: "vay",
    categoryName: "Váy",
    price: 750000,
    originalPrice: 850000,
    color: "Xanh forest",
    colors: [
      { name: "Xanh forest", hex: "#194e3d" },
      { name: "Nâu hạt dẻ", hex: "#523c2d" },
      { name: "Đen tuyền", hex: "#202221" },
    ],
    sizes: ["XS", "S", "M", "L"],
    image: "/products/chan-vay-pleated-midi.jpg",
    gallery: [
      "/products/chan-vay-pleated-midi.jpg",
      "/products/chan-vay-pleated-midi-detail.jpg",
    ],
    description: "Chân váy midi xếp ly nhuyễn dập nhiệt cố định không bay ly khi giặt. Độ xòe nhẹ nhàng tạo chuyển động thướt tha khi bước đi, tôn lên vẻ nữ tính thanh lịch.",
    material: "Chiffon tuyết cao cấp dập ly nhiệt, lót lụa habotai kín đáo.",
    fit: "Midi A-line phom dài ngang bắp chân, cạp cao.",
    details: [
      "Công nghệ ép nhiệt giữ nếp ly vĩnh viễn",
      "Khóa kéo giọt nước ẩn sau lưng",
      "Lớp lót chống dính tĩnh điện",
    ],
    isFeatured: true,
    chart: {
      name: "Bảng size Chân váy Pleated Midi",
      garment: "bottom",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "XS", waist_cm: { min: 58, max: 64 }, hip_cm: { min: 82, max: 88 } },
        { size: "S", waist_cm: { min: 64, max: 70 }, hip_cm: { min: 88, max: 94 } },
        { size: "M", waist_cm: { min: 70, max: 76 }, hip_cm: { min: 94, max: 100 } },
        { size: "L", waist_cm: { min: 76, max: 83 }, hip_cm: { min: 100, max: 107 } },
      ],
    },
  },
  {
    id: "chan-vay-chu-a-linen",
    slug: "chan-vay-chu-a-linen",
    name: "Chân váy Chữ A Vải Linen",
    subtitle: "Phom chữ A tôn dáng, hàng khuy gỗ dọc thân trước mộc mạc.",
    category: "vay",
    categoryName: "Váy",
    price: 590000,
    color: "Kem cát",
    colors: [
      { name: "Kem cát", hex: "#dfd6c5" },
      { name: "Đen tuyền", hex: "#222423" },
      { name: "Xanh rêu", hex: "#3e5144" },
    ],
    sizes: ["XS", "S", "M", "L"],
    image: "/products/chan-vay-chu-a-linen.jpg",
    gallery: [
      "/products/chan-vay-chu-a-linen.jpg",
      "/products/chan-vay-chu-a-linen-detail.jpg",
    ],
    description: "Chân váy chữ A dài qua đầu gối từ chất lanh mộc mạc. Điểm nhấn hàng khuy gỗ tự nhiên chạy dọc thân trước mang lại cảm giác vintage tinh tế.",
    material: "100% Linen tự nhiên wash mềm.",
    fit: "A-line fit phom chữ A cạp cao tôn dáng.",
    details: [
      "Hàng khuy gỗ tự nhiên đính thủ công",
      "Hai túi ốp chéo tiện lợi phía trước",
      "Lót mềm thoáng khí bên trong",
    ],
    chart: {
      name: "Bảng size Chân váy Chữ A",
      garment: "bottom",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "XS", waist_cm: { min: 60, max: 65 }, hip_cm: { min: 84, max: 89 } },
        { size: "S", waist_cm: { min: 65, max: 71 }, hip_cm: { min: 89, max: 95 } },
        { size: "M", waist_cm: { min: 71, max: 77 }, hip_cm: { min: 95, max: 101 } },
        { size: "L", waist_cm: { min: 77, max: 84 }, hip_cm: { min: 101, max: 108 } },
      ],
    },
  },
  {
    id: "dam-suong-linen-minimal",
    slug: "dam-suong-linen-minimal",
    name: "Đầm suông Linen Tối giản",
    subtitle: "Dáng suông thoải mái, cổ thuyền nhẹ nhàng và đường xẻ tà bên hông.",
    category: "vay",
    categoryName: "Váy",
    price: 890000,
    color: "Kem tự nhiên",
    colors: [
      { name: "Kem tự nhiên", hex: "#ece6d7" },
      { name: "Xanh rêu", hex: "#44594a" },
      { name: "Đen tuyền", hex: "#232524" },
    ],
    sizes: ["XS", "S", "M", "L"],
    image: "/products/dam-suong-linen-minimal.jpg",
    gallery: [
      "/products/dam-suong-linen-minimal.jpg",
      "/products/dam-suong-linen-minimal-detail.jpg",
    ],
    description: "Đầm suông liền thân được may từ vải linen thô mộc. Thiết kế tối giản không chi tiết thừa giúp người mặc cảm thấy tự do và nhẹ nhàng trong từng cử động.",
    material: "100% Linen sợi tự nhiên cao cấp.",
    fit: "Loose straight fit suông rộng thư giãn.",
    details: [
      "Đường xẻ tà 2 bên hông tăng tính linh hoạt khi đi lại",
      "Túi mổ hai bên hông kín đáo",
      "Khóa kéo sau gáy tinh tế",
    ],
    isNew: true,
    chart: {
      name: "Bảng size Đầm suông Linen",
      garment: "top",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "XS", chest_cm: { min: 74, max: 82 }, waist_cm: { min: 60, max: 72 } },
        { size: "S", chest_cm: { min: 82, max: 90 }, waist_cm: { min: 68, max: 80 } },
        { size: "M", chest_cm: { min: 90, max: 98 }, waist_cm: { min: 76, max: 88 } },
        { size: "L", chest_cm: { min: 98, max: 106 }, waist_cm: { min: 84, max: 96 } },
      ],
    },
  },
  {
    id: "chan-vay-jean-xe-ta",
    slug: "chan-vay-jean-xe-ta",
    name: "Chân váy Denim Xẻ tà Cổ điển",
    subtitle: "Denim cotton bền bỉ, xẻ tà trước năng động và tôn dáng đôi chân.",
    category: "vay",
    categoryName: "Váy",
    price: 680000,
    color: "Xanh wash",
    colors: [
      { name: "Xanh wash", hex: "#527599" },
      { name: "Xanh nhạt", hex: "#8aa3be" },
    ],
    sizes: ["26", "27", "28", "29", "30"],
    image: "/products/chan-vay-jean-xe-ta.jpg",
    gallery: [
      "/products/chan-vay-jean-xe-ta.jpg",
      "/products/chan-vay-jean-xe-ta-detail.jpg",
    ],
    description: "Chân váy bò midi cạp cao với đường xẻ tà trước vừa đủ để bước đi thoải mái và kéo dài đôi chân. Vải denim được giặt wash mài nhẹ phong trần.",
    material: "100% Cotton Denim 11oz wash mài nhẹ.",
    fit: "Midi straight fit cạp cao ôm hông suông nhẹ.",
    details: [
      "Đường xẻ tà trước thời thượng",
      "5 túi phong cách denim kinh điển",
      "Cúc đinh đồng và đỉa thắt lưng chắc chắn",
    ],
    chart: {
      name: "Bảng size Chân váy Denim",
      garment: "bottom",
      source: "illustrative",
      measurement_basis: "body_cm",
      rows: [
        { size: "26", waist_cm: { min: 60, max: 65 }, hip_cm: { min: 84, max: 89 } },
        { size: "27", waist_cm: { min: 64, max: 69 }, hip_cm: { min: 88, max: 93 } },
        { size: "28", waist_cm: { min: 68, max: 73 }, hip_cm: { min: 92, max: 97 } },
        { size: "29", waist_cm: { min: 72, max: 77 }, hip_cm: { min: 96, max: 101 } },
        { size: "30", waist_cm: { min: 76, max: 81 }, hip_cm: { min: 100, max: 105 } },
      ],
    },
  },
];

// Helper functions for easy querying
export function getAllProducts(): Product[] {
  return PRODUCTS;
}

export function getProductBySlug(slug: string): Product | undefined {
  return PRODUCTS.find((p) => p.slug === slug || p.id === slug);
}

export function getRelatedProducts(productId: string, limit = 4): Product[] {
  const current = PRODUCTS.find((p) => p.id === productId);
  if (!current) return PRODUCTS.slice(0, limit);
  // Match same category first, then others
  const sameCategory = PRODUCTS.filter((p) => p.id !== productId && p.category === current.category);
  const otherCategory = PRODUCTS.filter((p) => p.id !== productId && p.category !== current.category);
  return [...sameCategory, ...otherCategory].slice(0, limit);
}

export function getProductsByCategory(category: CategoryKey): Product[] {
  return PRODUCTS.filter((p) => p.category === category);
}

// Backward-compatible export for essential t-shirt
export const essential = PRODUCTS[0];
export type FitProduct = Product;

export const money = (value: number) =>
  new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(value);
