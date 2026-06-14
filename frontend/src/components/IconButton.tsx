import type { ButtonHTMLAttributes } from "react";
import type { LucideIcon } from "lucide-react";

type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  icon: LucideIcon;
  label: string;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "warning";
};

export function IconButton({
  icon: Icon,
  label,
  variant = "primary",
  className = "",
  ...props
}: IconButtonProps) {
  return (
    <button className={`button button-${variant} ${className}`} type="button" title={label} {...props}>
      <Icon aria-hidden="true" />
      <span>{label}</span>
    </button>
  );
}
