export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      width="28"
      height="28"
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M23 8 C23 5.5 20 5 16.5 5 C12 5 9 6.5 9 10 C9 15 23 14 23 20 C23 24 19 26 15 26 C11 26 9 25 9 22.5"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="23" cy="8" r="2.6" fill="#F2913D" />
      <circle cx="9" cy="22.5" r="2.6" fill="currentColor" />
    </svg>
  );
}
