import React, { useEffect } from "react";

interface Props {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ title, onClose, children }: Props) {
  useEffect(() => {
    const fn = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", fn);
    return () => window.removeEventListener("keydown", fn);
  }, [onClose]);

  return (
    <div className="modalOverlay" onClick={onClose}>
      <div className="modalBox" onClick={e => e.stopPropagation()}>
        <div className="modalHeader">
          <span className="modalTitle">{title}</span>
          <button className="modalClose" onClick={onClose}>✕</button>
        </div>
        <div className="modalBody">{children}</div>
      </div>
    </div>
  );
}
