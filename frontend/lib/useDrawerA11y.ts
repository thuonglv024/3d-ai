"use client";

import { useEffect, useRef } from "react";

/**
 * Reusable accessibility hook for drawers and dialogs.
 * Enforces:
 * - Body scroll locking when open (with restoration on close)
 * - Escape key to close
 * - Focus trapping within the panel
 * - Focus restoration to the trigger element when closed
 */
export function useDrawerA11y(
  isOpen: boolean,
  onClose: () => void,
  panelRef?: React.RefObject<HTMLElement | null>
) {
  const triggerRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!isOpen) return;

    // Capture the trigger element that had focus before opening
    triggerRef.current = document.activeElement as HTMLElement | null;

    // Lock body scroll
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Focus panel or first interactive element
    const timer = setTimeout(() => {
      if (panelRef?.current) {
        const focusableElements = panelRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [tabindex]:not([tabindex="-1"]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
        );
        if (focusableElements.length > 0) {
          focusableElements[0].focus();
        } else {
          panelRef.current.focus();
        }
      }
    }, 40);

    // Escape key and Tab focus trap
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.defaultPrevented) return;

      const targetWrapper =
        (e.target as HTMLElement | null)?.closest?.(".morph-custom-select-wrapper") ||
        (document.activeElement as HTMLElement | null)?.closest?.(".morph-custom-select-wrapper");
      if (
        targetWrapper &&
        (targetWrapper.querySelector(".morph-custom-select-trigger.is-open") ||
          targetWrapper.querySelector(".morph-custom-select-menu"))
      ) {
        return;
      }

      if (e.key === "Escape") {
        if (
          panelRef?.current?.querySelector(
            ".morph-custom-select-trigger.is-open, .morph-custom-select-menu"
          )
        ) {
          return;
        }
        e.preventDefault();
        e.stopPropagation();
        onCloseRef.current();
        return;
      }

      if (e.key === "Tab" && panelRef?.current) {
        const focusables = panelRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [tabindex]:not([tabindex="-1"]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
        );
        if (focusables.length === 0) {
          e.preventDefault();
          return;
        }

        const first = focusables[0];
        const last = focusables[focusables.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first || document.activeElement === panelRef.current) {
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

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      clearTimeout(timer);
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", handleKeyDown);

      // Restore focus to opener element
      if (triggerRef.current && typeof triggerRef.current.focus === "function") {
        triggerRef.current.focus();
      }
    };
  }, [isOpen, panelRef]);
}
