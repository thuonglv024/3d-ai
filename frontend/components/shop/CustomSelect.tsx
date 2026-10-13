"use client";

import React, { useState, useRef, useEffect, useId } from "react";
import { ChevronDown, Check } from "lucide-react";

export interface SelectOption {
  value: string;
  label: string;
  sublabel?: string;
  disabled?: boolean;
  icon?: React.ReactNode;
}

export interface CustomSelectProps {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  ariaLabel?: string;
  id?: string;
  className?: string;
  menuClassName?: string;
  size?: "sm" | "md" | "lg";
  variant?: "default" | "compact" | "header";
}

export default function CustomSelect({
  options,
  value,
  onChange,
  placeholder = "Chọn...",
  disabled = false,
  ariaLabel,
  id,
  className = "",
  menuClassName = "",
  size = "md",
  variant = "default",
}: CustomSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const generatedId = useId();
  const selectId = id || generatedId;
  const listboxId = `${selectId}-listbox`;

  const [position, setPosition] = useState<{
    flipUp: boolean;
    alignRight: boolean;
    maxHeight: number;
  }>({
    flipUp: false,
    alignRight: false,
    maxHeight: 280,
  });

  const selectedOption = options.find((opt) => opt.value === value);

  // Position calculation with edge detection
  useEffect(() => {
    if (!isOpen || !triggerRef.current) return;

    const updatePosition = () => {
      const trigger = triggerRef.current;
      if (!trigger) return;

      const rect = trigger.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      const viewportWidth = window.innerWidth;

      const spaceBelow = viewportHeight - rect.bottom;
      const spaceAbove = rect.top;
      const menuHeight = menuRef.current?.offsetHeight || 220;
      const menuWidth = menuRef.current?.offsetWidth || 240;

      const flipUp = spaceBelow < menuHeight && spaceAbove > spaceBelow;
      const alignRight = variant === "header" || rect.left + menuWidth > viewportWidth - 16;
      const availableHeight = flipUp ? spaceAbove - 16 : spaceBelow - 16;

      setPosition({
        flipUp,
        alignRight,
        maxHeight: Math.max(160, Math.min(360, availableHeight)),
      });
    };

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [isOpen]);

  // Click outside to close
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Keyboard navigation within listbox
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;

    if (!isOpen) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
      return;
    }

    if (e.key === "Tab") {
      setIsOpen(false);
      return;
    }

    if (!menuRef.current) return;
    const items = Array.from(
      menuRef.current.querySelectorAll<HTMLButtonElement>("button:not([disabled])")
    );
    if (!items.length) return;

    const currentIndex = items.indexOf(document.activeElement as HTMLButtonElement);

    if (e.key === "ArrowDown") {
      e.preventDefault();
      const nextIndex = (currentIndex + 1) % items.length;
      items[nextIndex].focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prevIndex = (currentIndex - 1 + items.length) % items.length;
      items[prevIndex].focus();
    } else if (e.key === "Home") {
      e.preventDefault();
      items[0].focus();
    } else if (e.key === "End") {
      e.preventDefault();
      items[items.length - 1].focus();
    }
  };

  // Focus active option when opened
  useEffect(() => {
    if (isOpen && menuRef.current) {
      const selectedEl =
        menuRef.current.querySelector<HTMLButtonElement>(".is-selected") ||
        menuRef.current.querySelector<HTMLButtonElement>("button:not([disabled])");
      selectedEl?.focus();
    }
  }, [isOpen]);

  const handleSelect = (val: string) => {
    onChange(val);
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  return (
    <div
      ref={containerRef}
      className={`morph-custom-select-wrapper select-size-${size} select-variant-${variant} ${className}`}
      onKeyDown={handleKeyDown}
    >
      {/* Visual Trigger Button */}
      <button
        ref={triggerRef}
        type="button"
        id={selectId}
        className={`morph-custom-select-trigger ${isOpen ? "is-open" : ""} ${disabled ? "is-disabled" : ""}`}
        onClick={() => !disabled && setIsOpen((prev) => !prev)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-label={ariaLabel || selectedOption?.label || placeholder}
      >
        <span className="morph-select-label-wrap">
          {selectedOption?.icon && (
            <span className="morph-select-icon">{selectedOption.icon}</span>
          )}
          <span className="morph-select-text">
            {selectedOption ? selectedOption.label : placeholder}
          </span>
          {selectedOption?.sublabel && (
            <span className="morph-select-subtext">· {selectedOption.sublabel}</span>
          )}
        </span>
        <ChevronDown size={14} className="morph-select-chevron" />
      </button>

      {/* Floating Listbox Popup */}
      {isOpen && (
        <div
          ref={menuRef}
          id={listboxId}
          className={`morph-custom-select-menu ${position.flipUp ? "is-flipped-up" : ""} ${position.alignRight ? "is-align-right" : ""} ${menuClassName}`}
          style={{ maxHeight: `${position.maxHeight}px` }}
          role="listbox"
          tabIndex={-1}
          aria-label={ariaLabel || "Tùy chọn"}
        >
          {options.map((opt) => {
            const isSelected = opt.value === value;
            return (
              <button
                key={opt.value}
                type="button"
                className={`morph-select-option ${isSelected ? "is-selected" : ""} ${opt.disabled ? "is-disabled" : ""}`}
                onClick={() => !opt.disabled && handleSelect(opt.value)}
                disabled={opt.disabled}
                role="option"
                aria-selected={isSelected}
              >
                <div className="morph-option-body">
                  {opt.icon && <span className="morph-option-icon">{opt.icon}</span>}
                  <div className="morph-option-text-group">
                    <span className="morph-option-label">{opt.label}</span>
                    {opt.sublabel && (
                      <span className="morph-option-sublabel">{opt.sublabel}</span>
                    )}
                  </div>
                </div>
                {isSelected && (
                  <Check size={14} className="morph-option-check" strokeWidth={2.4} />
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Hidden Native Select for Form Accessibility & Automated Testing */}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} disabled={opt.disabled}>
            {opt.label} {opt.sublabel ? `(${opt.sublabel})` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}
