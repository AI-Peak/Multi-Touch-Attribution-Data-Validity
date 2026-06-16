"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type CFStatus = "focus" | "muted" | "idle";

type CrossFilterCtx = {
  selected: string | null;
  selectedLabel: string | null;
  activeKeys: ReadonlySet<string>;
  isActive: boolean;
  select: (key: string | null, label?: string) => void;
  clear: () => void;
  status: (key?: string | null) => CFStatus;
  cls: (key?: string | null) => string;
};

const NOOP: CrossFilterCtx = {
  selected: null,
  selectedLabel: null,
  activeKeys: new Set(),
  isActive: false,
  select: () => undefined,
  clear: () => undefined,
  status: () => "idle",
  cls: () => "",
};

const Ctx = createContext<CrossFilterCtx>(NOOP);

export function CrossFilterProvider({
  links,
  children,
}: {
  links: Record<string, string[]>;
  children: ReactNode;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);

  const activeKeys = useMemo<ReadonlySet<string>>(() => {
    if (!selected) return new Set();
    return new Set([selected, ...(links[selected] ?? [])]);
  }, [selected, links]);

  const isActive = selected !== null;

  const select = useCallback((key: string | null, label?: string) => {
    if (!key) {
      setSelected(null);
      setSelectedLabel(null);
      return;
    }
    setSelected((prev) => {
      if (prev === key) {
        setSelectedLabel(null);
        return null;
      }
      setSelectedLabel(label ?? key);
      return key;
    });
  }, []);

  const clear = useCallback(() => {
    setSelected(null);
    setSelectedLabel(null);
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") clear();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [clear]);

  const status = useCallback(
    (key?: string | null): CFStatus => {
      if (!isActive || !key) return "idle";
      return activeKeys.has(key) ? "focus" : "muted";
    },
    [isActive, activeKeys],
  );

  const cls = useCallback(
    (key?: string | null): string => {
      const s = status(key);
      if (s === "focus") return " cross-focus";
      if (s === "muted") return " cross-muted";
      return "";
    },
    [status],
  );

  return (
    <Ctx.Provider value={{ selected, selectedLabel, activeKeys, isActive, select, clear, status, cls }}>
      {children}
    </Ctx.Provider>
  );
}

export function useCrossFilter(): CrossFilterCtx {
  return useContext(Ctx);
}
