type ProductLogoProps = {
  className?: string
}

export function ProductLogo({ className = '' }: ProductLogoProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      focusable="false"
      viewBox="0 0 32 32"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M4 7.5c4.7-.8 8.5.3 12 3.2v15.1c-3.5-2.7-7.3-3.7-12-2.9V7.5Z"
        fill="#EFF6FF"
        stroke="#2563EB"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
      <path
        d="M28 7.5c-4.7-.8-8.5.3-12 3.2v15.1c3.5-2.7 7.3-3.7 12-2.9V7.5Z"
        fill="#FFFFFF"
        stroke="#2563EB"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
      <path d="M16 10.7v15.1" stroke="#2563EB" strokeLinecap="round" strokeWidth="1.8" />
      <path d="m20.1 12.6 3.4 2.2 2.1-3.1" stroke="#6D28D9" strokeWidth="1.4" />
      <circle cx="20" cy="12.5" r="1.5" fill="#6D28D9" />
      <circle cx="23.6" cy="14.8" r="1.5" fill="#6D28D9" />
      <circle cx="25.7" cy="11.6" r="1.5" fill="#6D28D9" />
    </svg>
  )
}
