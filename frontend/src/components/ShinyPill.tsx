// Adapted from OriginKit "shiny-pill" (https://mcp.originkit.dev)
// Real effect logic preserved (pure-CSS sweeping sheen). Framer property-control
// boilerplate removed for use in a plain React + Vite app.
import * as React from "react"

type Props = {
  text: string
  link?: string
  textColor?: string
  shineColor?: string
  speed?: number
  className?: string
  style?: React.CSSProperties
}

const KEYFRAMES_ID = "storyforge-shiny-pill-keyframes"

export default function ShinyPill({
  text,
  link,
  textColor = "#EDE6DD",
  shineColor = "#C2613F",
  speed = 2,
  className,
  style,
}: Props) {
  const isFixedWidth = style?.width === "100%"

  const shellStyle: React.CSSProperties = {
    ...style,
    position: "relative",
    display: "inline-flex",
    alignItems: "center",
    boxSizing: "border-box",
    ...(isFixedWidth ? {} : { minWidth: "max-content", width: "auto" }),
    whiteSpace: "nowrap",
  }

  const shineLayerStyle: React.CSSProperties = {
    position: "absolute",
    inset: 0,
    display: "flex",
    alignItems: "center",
    whiteSpace: "nowrap",
    color: shineColor,
    pointerEvents: "none",
    WebkitMaskImage:
      "linear-gradient(to right, transparent 30%, #000 50%, transparent 70%)",
    maskImage:
      "linear-gradient(to right, transparent 30%, #000 50%, transparent 70%)",
    WebkitMaskSize: "150% auto",
    maskSize: "150% auto",
    animation: `storyforgeShinySweep ${speed}s ease-in-out infinite`,
  }

  const content = (
    <span style={shellStyle} className={className}>
      <style
        id={KEYFRAMES_ID}
        dangerouslySetInnerHTML={{
          __html: `@keyframes storyforgeShinySweep {
            0% { -webkit-mask-position: 200%; mask-position: 200%; }
            100% { -webkit-mask-position: -100%; mask-position: -100%; }
          }`,
        }}
      />
      <span style={{ color: textColor }}>{text}</span>
      <span style={shineLayerStyle} aria-hidden="true">
        {text}
      </span>
    </span>
  )

  if (link) {
    return (
      <a href={link} style={{ textDecoration: "none", display: "inline-flex" }}>
        {content}
      </a>
    )
  }
  return content
}
