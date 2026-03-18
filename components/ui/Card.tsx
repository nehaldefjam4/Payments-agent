import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  title?: string;
}

export default function Card({ children, className = "", title }: CardProps) {
  return (
    <div
      className={`bg-white rounded-2xl shadow-sm border border-gray-100 p-6 ${className}`}
    >
      {title && (
        <h3 className="text-lg font-bold text-fam-dark mb-4">{title}</h3>
      )}
      {children}
    </div>
  );
}
