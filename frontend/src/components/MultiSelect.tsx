import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

interface Props {
  label: string;
  options: string[];
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}

/**
 * A dropdown that holds several choices.
 *
 * The menu is drawn in a portal on <body>, positioned from the trigger's measured
 * rectangle. That way a rounded card with `overflow: hidden`, a scrolling table or
 * the side panel can never clip it. The options come from the dataset, so they
 * always match the words the scoring engine compares against.
 */
export default function MultiSelect({ label, options, value, onChange, placeholder }: Props) {
  const [open, setOpen] = useState(false);
  const [box, setBox] = useState<{ top?: number; bottom?: number; left: number; width: number; maxHeight: number } | null>(null);

  const control = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);

  const measure = () => {
    const trigger = control.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const gap = 4;
    const spaceBelow = window.innerHeight - rect.bottom - gap;
    const spaceAbove = rect.top - gap;
    const openUp = spaceBelow < 200 && spaceAbove > spaceBelow;

    setBox({
      left: Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8)),
      width: rect.width,
      maxHeight: Math.max(120, Math.min(260, openUp ? spaceAbove - 8 : spaceBelow - 8)),
      ...(openUp ? { bottom: window.innerHeight - rect.top + gap } : { top: rect.bottom + gap }),
    });
  };

  const show = () => {
    measure();
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const onDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (control.current?.contains(target) || menu.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    // Closing on scroll keeps the menu glued to its button, but a scroll *inside* the
    // menu is the user reading the list, so that one must be ignored.
    const onScroll = (event: Event) => {
      const target = event.target as Node | null;
      if (target && menu.current?.contains(target)) return;
      setOpen(false);
    };
    const onResize = () => setOpen(false);

    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onResize);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onResize);
    };
  }, [open]);

  // Chips wrap onto more lines as you tick more, so the trigger grows. Re-measure
  // to keep the menu glued to its bottom edge.
  useEffect(() => {
    if (open) measure();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, value.length]);

  const toggle = (option: string) =>
    onChange(value.includes(option) ? value.filter((v) => v !== option) : [...value, option]);

  return (
    <div className="ms">
      <span className="ms-label">{label}</span>
      <button
        ref={control}
        type="button"
        className="ms-control"
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => (open ? setOpen(false) : show())}
      >
        {value.length === 0 ? (
          <span className="ms-placeholder">{placeholder ?? "Nothing chosen yet"}</span>
        ) : (
          <span className="ms-chips">
            {value.map((item) => (
              <span className="ms-chip" key={item}>
                {item}
              </span>
            ))}
          </span>
        )}
        <span className="ms-caret" aria-hidden="true">
          ▾
        </span>
      </button>

      {open &&
        box &&
        createPortal(
          <div
            ref={menu}
            className="ms-panel"
            role="group"
            aria-label={label}
            style={{
              top: box.top,
              bottom: box.bottom,
              left: box.left,
              width: box.width,
              maxHeight: box.maxHeight,
            }}
          >
            {options.length === 0 ? (
              <p className="hint" style={{ padding: "6px 8px" }}>
                Nothing to choose from.
              </p>
            ) : (
              options.map((option) => (
                <label className="ms-option" key={option}>
                  <input
                    type="checkbox"
                    checked={value.includes(option)}
                    onChange={() => toggle(option)}
                  />
                  <span>{option}</span>
                </label>
              ))
            )}
          </div>,
          document.body,
        )}
    </div>
  );
}
