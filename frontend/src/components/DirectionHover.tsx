// Adapted from OriginKit "directionhover" (https://mcp.originkit.dev)
// Real effect logic preserved (accent copy slides in from the edge the cursor
// entered). Framer property-control boilerplate removed for plain React + Vite.
import * as React from "react"

type Props = {
  title: string
  href?: string
  fontSize?: number
  fontWeight?: number | string
  letterSpacing?: string
  gap?: number
  textColor?: string
  hoverColor?: string
  duration?: number
  className?: string
  style?: React.CSSProperties
  onClick?: () => void
}

const EASE = "cubic-bezier(0.22, 1, 0.36, 1)"

export default function DirectionHover({
  title,
  href,
  fontSize = 24,
  fontWeight = 700,
  letterSpacing = "0em",
  gap = 6,
  textColor = "#EDE6DD",
  hoverColor = "#C2613F",
  duration = 0.32,
  className,
  style,
  onClick,
}: Props) {
  const ref = React.useRef<HTMLSpanElement>(null)
  const [dir, setDir] = React.useState<"none" | "top" | "bottom">("none")

  const onEnter = (e: React.MouseEvent) => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const y = e.clientY - rect.top
    setDir(y < rect.height / 2 ? "top" : "bottom")
  }
  const onLeave = () => setDir("none")

  const lineBox = fontSize * 0.72
  const gapPx = (gap || 0) * 3
  const step = lineBox + gapPx
  const yByDir = { none: -step, top: 0, bottom: -2 * step }

  const labelStyle: React.CSSProperties = {
    margin: 0,
    whiteSpace: "pre" as const,
    lineHeight: 1,
    height: lineBox,
    display: "flex",
    alignItems: "center",
    overflow: "hidden",
    fontFamily: "Inter, system-ui, sans-serif",
    fontSize,
    fontWeight,
    letterSpacing,
  }

  const inner = (
    <span
      ref={ref}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onClick={onClick}
      className={className}
      style={{
        ...style,
        position: "relative",
        display: "inline-block",
        overflow: "hidden",
        height: lineBox,
        cursor: "pointer",
        userSelect: "none",
      }}
    >
      <span
        style={{
          display: "flex",
          flexDirection: "column",
          gap: gapPx,
          transform: `translateY(${yByDir[dir]}px)`,
          transition: `transform ${duration}s ${EASE}`,
        }}
      >
        <span style={{ ...labelStyle, color: hoverColor }}>{title}</span>
        <span style={{ ...labelStyle, color: textColor }}>{title}</span>
        <span style={{ ...labelStyle, color: hoverColor }}>{title}</span>
      </span>
    </span>
  )

  if (href) {
    return (
      <a href={href} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
        {inner}
      </a>
    )
  }
  return inner
}
