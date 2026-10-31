"use client";

import { ArrowRight, X } from "lucide-react";
import type { Product } from "../../lib/catalog";
import Modal from "./Modal";

export default function SizeChartModal({
  product,
  open,
  onClose,
  onOpenScan,
}: {
  product: Product;
  open: boolean;
  onClose: () => void;
  onOpenScan: () => void;
}) {
  const isBottom = product.chart.garment === "bottom";

  return (
    <Modal open={open} onClose={onClose} title={`Bảng size · ${product.name}`}>
      <div className="shop-modal-body">
        <h2>Thông số số đo cơ thể chuẩn</h2>
        <p>
          Bảng size tính theo khoảng <strong>số đo cơ thể (cm)</strong>, không phải kích thước trang phục trải phẳng.
          Đo sát cơ thể khi mặc đồ ôm nhẹ để đối chiếu kích cỡ phù hợp.
        </p>

        <table className="shop-size-table">
          <thead>
            <tr>
              <th>Size</th>
              {isBottom ? (
                <>
                  <th>Vòng eo (cm)</th>
                  <th>Vòng mông (cm)</th>
                </>
              ) : (
                <>
                  <th>Vòng ngực (cm)</th>
                  <th>Vòng eo (cm)</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {product.chart.rows.map((r) => (
              <tr key={r.size}>
                <th>{r.size}</th>
                {isBottom ? (
                  <>
                    <td>
                      {r.waist_cm ? `${r.waist_cm.min}–${r.waist_cm.max}` : "—"}
                    </td>
                    <td>
                      {r.hip_cm ? `${r.hip_cm.min}–${r.hip_cm.max}` : "—"}
                    </td>
                  </>
                ) : (
                  <>
                    <td>
                      {r.chest_cm ? `${r.chest_cm.min}–${r.chest_cm.max}` : "—"}
                    </td>
                    <td>
                      {r.waist_cm ? `${r.waist_cm.min}–${r.waist_cm.max}` : "—"}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>

        {product.garment_specs && product.garment_specs.length > 0 && (
          <div className="shop-garment-specs">
            <h3>Số đo may (trải phẳng)</h3>
            <p>
              Vòng ngực áo = chiều rộng ngực trải phẳng × 2.{" "}
              {product.garment_source ? `Nguồn: ${product.garment_source}.` : ""}
            </p>
            <table className="shop-size-table">
              <thead>
                <tr>
                  <th>Size</th>
                  <th>Vòng ngực áo</th>
                  <th>Dài áo</th>
                  <th>Rộng vai</th>
                  <th>Dài tay</th>
                </tr>
              </thead>
              <tbody>
                {product.garment_specs.map((spec) => (
                  <tr key={spec.size}>
                    <th>{spec.size}</th>
                    <td>{spec.chest_cm != null ? `${spec.chest_cm} cm` : "—"}</td>
                    <td>{spec.length_cm != null ? `${spec.length_cm} cm` : "—"}</td>
                    <td>{spec.shoulder_cm != null ? `${spec.shoulder_cm} cm` : "—"}</td>
                    <td>{spec.sleeve_cm != null ? `${spec.sleeve_cm} cm` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="chart-disclaimer">
          <p>
            Nếu số đo của bạn nằm giữa hai size, hãy chọn size lớn hơn nếu thích mặc rộng rãi hoặc size nhỏ hơn nếu thích ôm vừa vặn.
          </p>
        </div>

        <button
          className="shop-primary"
          onClick={() => {
            onClose();
            onOpenScan();
          }}
        >
          Tìm size bằng webcam 3D
          <ArrowRight size={18} />
        </button>
      </div>
    </Modal>
  );
}
