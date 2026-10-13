"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

// Track active modals globally across component instances to prevent background scroll leaks when switching modals
let globalActiveModalCount = 0;
let originalBodyOverflow = "";

export default function Modal({
  open,
  onClose,
  title,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  wide?: boolean;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open) {
      // Remember which element had focus when the modal was opened
      triggerRef.current = document.activeElement as HTMLElement | null;

      if (!dialog.open) {
        dialog.showModal();
      }

      // Prevent background scroll while modal is active
      globalActiveModalCount++;
      if (globalActiveModalCount === 1) {
        originalBodyOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
      }

      // Initial focus: focus first focusable element inside dialog or the dialog itself
      const focusTimer = setTimeout(() => {
        if (!dialog.open) return;
        const focusableElements = dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [tabindex]:not([tabindex="-1"]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
        );
        if (focusableElements.length > 0) {
          focusableElements[0].focus();
        } else {
          dialog.focus();
        }
      }, 30);

      return () => {
        clearTimeout(focusTimer);
        globalActiveModalCount = Math.max(0, globalActiveModalCount - 1);
        if (globalActiveModalCount === 0) {
          document.body.style.overflow = originalBodyOverflow;
        }
        if (dialog.open) {
          dialog.close();
        }

        // Restore focus to opening element on close, provided no other modal opened
        const remainingOpenDialog = document.querySelector("dialog[open]");
        if (!remainingOpenDialog && triggerRef.current && typeof triggerRef.current.focus === "function") {
          triggerRef.current.focus();
        }
      };
    } else {
      if (dialog.open) {
        dialog.close();
      }
    }
  }, [open]);

  // Trap focus within dialog & handle Escape key
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDialogElement>) => {
    if (e.key === "Escape") {
      if (dialogRef.current?.querySelector(".capture-session.is-expanded")) {
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      onClose();
      return;
    }

    if (e.key === "Tab") {
      const dialog = dialogRef.current;
      if (!dialog) return;

      const focusable = dialog.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [tabindex]:not([tabindex="-1"]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
      );
      if (focusable.length === 0) {
        e.preventDefault();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first || document.activeElement === dialog) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
  };

  const closeLabel = title.startsWith("Tìm size của tôi")
    ? "Đóng Tìm size của tôi"
    : `Đóng ${title}`;

  return (
    <dialog
      ref={dialogRef}
      tabIndex={-1}
      className={`shop-modal ${wide ? "fit-modal" : ""}`}
      aria-label={title}
      onCancel={(e) => {
        if (dialogRef.current?.querySelector(".capture-session.is-expanded")) {
          e.preventDefault();
          return;
        }
        e.preventDefault();
        onClose();
      }}
      onKeyDown={handleKeyDown}
      onClick={(e) => {
        if (e.target === dialogRef.current) {
          onClose();
        }
      }}
    >
      <div className="shop-modal-header">
        <span className="shop-modal-title">{title}</span>
        <button
          type="button"
          className="shop-icon modal-close-btn"
          aria-label={closeLabel}
          onClick={onClose}
        >
          <X size={21} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
