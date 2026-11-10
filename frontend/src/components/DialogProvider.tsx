import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

export interface PromptOptions {
  title: string;
  label?: string;
  help?: string;
  placeholder?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  multiline?: boolean;
  allowEmpty?: boolean;
  initialValue?: string;
}

interface DialogApi {
  /** Opens a dialog and resolves with the trimmed text, or null if cancelled. */
  promptText: (options: PromptOptions) => Promise<string | null>;
}

const Ctx = createContext<DialogApi | null>(null);

export function DialogProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<PromptOptions | null>(null);
  const [value, setValue] = useState("");
  const resolver = useRef<((result: string | null) => void) | null>(null);
  const field = useRef<HTMLInputElement & HTMLTextAreaElement>(null);
  const opener = useRef<Element | null>(null);

  const promptText = useCallback((next: PromptOptions) => {
    opener.current = document.activeElement;
    setValue(next.initialValue ?? "");
    setOptions(next);
    return new Promise<string | null>((resolve) => {
      resolver.current = resolve;
    });
  }, []);

  const close = useCallback((result: string | null) => {
    resolver.current?.(result);
    resolver.current = null;
    setOptions(null);
    if (opener.current instanceof HTMLElement) opener.current.focus();
  }, []);

  const required = options ? options.allowEmpty !== true : false;

  useEffect(() => {
    if (!options) return;
    field.current?.focus();
    field.current?.select();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [options, close]);

  if (!options) return <Ctx.Provider value={{ promptText }}>{children}</Ctx.Provider>;

  const submit = () => {
    const trimmed = value.trim();
    if (required && !trimmed) return;
    close(trimmed);
  };

  return (
    <Ctx.Provider value={{ promptText }}>
      {children}
      <div
        className="dialog-veil"
        onMouseDown={(e) => {
          if (e.target === e.currentTarget) close(null);
        }}
      >
        <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
          <h2 className="dialog-title" id="dialog-title">
            {options.title}
          </h2>
          {options.help && <p className="dialog-help">{options.help}</p>}

          <label className="dialog-label">
            <span>{options.label ?? "Your answer"}</span>
            {options.multiline ? (
              <textarea
                ref={field}
                value={value}
                placeholder={options.placeholder}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    submit();
                  }
                }}
              />
            ) : (
              <input
                ref={field}
                value={value}
                placeholder={options.placeholder}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    submit();
                  }
                }}
              />
            )}
          </label>

          <div className="dialog-actions">
            <span className="dialog-key">
              {options.multiline ? "Ctrl + Enter to save · Esc to cancel" : "Enter to save · Esc to cancel"}
            </span>
            <button type="button" className="btn" onClick={() => close(null)}>
              {options.cancelLabel ?? "Cancel"}
            </button>
            <button type="button" className="btn go" disabled={required && !value.trim()} onClick={submit}>
              {options.confirmLabel ?? "Save"}
            </button>
          </div>
        </div>
      </div>
    </Ctx.Provider>
  );
}

export function useDialog(): DialogApi {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useDialog must be used inside DialogProvider");
  return ctx;
}
