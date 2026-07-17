// Adapted from OriginKit "spotlighttext" (https://mcp.originkit.dev)
// Real effect logic preserved; Framer property-control boilerplate removed so it
// runs in a plain React + Vite app (uses framer-motion instead of "framer").
import * as React from "react"
import { useEffect, useRef } from "react"
import {
  motion,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
} from "framer-motion"

type Props = {
  text: string
  brightColor?: string
  dimColor?: string
  maskSize?: number
  intensity?: number
  className?: string
  style?: React.CSSProperties
}

// FlashlightText — a recreation of Cred's "Flashlight Effect". A block of text
// is DIMMED by default; a soft circular spotlight follows the cursor on hover
// and reveals the BRIGHT version of the text within it.
export default function SpotlightText({
  text,
  brightColor = "#FFFFFF",
  dimColor = "rgba(237, 230, 221, 0.22)",
  maskSize = 150,
  intensity = 10,
  className,
  style,
}: Props) {
  const prefersReducedMotion = useReducedMotion()
  const interactive = !prefersReducedMotion

  const containerRef = useRef<HTMLDivElement | null>(null)
  const contentRef = useRef<HTMLDivElement | null>(null)

  const maskX = useMotionValue(0)
  const maskY = useMotionValue(0)
  const maskSizeMV = useMotionValue(0)

  const core = Math.max(10, Math.min(100, intensity))
  const maskImage = useMotionTemplate`radial-gradient(circle ${maskSizeMV}px at ${maskX}px ${maskY}px, black, black ${core}%, transparent 100%)`

  useEffect(() => {
    if (!interactive) return
    const el = containerRef.current
    if (!el) return
    const onMove = (e: PointerEvent) => {
      const rect = (contentRef.current ?? el).getBoundingClientRect()
      maskX.set(e.clientX - rect.left)
      maskY.set(e.clientY - rect.top)
    }
    const onEnter = () => {
      maskSizeMV.set(maskSize)
    }
    const onLeave = () => {
      maskSizeMV.set(0)
    }
    el.addEventListener("pointermove", onMove)
    el.addEventListener("pointerenter", onEnter)
    el.addEventListener("pointerleave", onLeave)
    return () => {
      el.removeEventListener("pointermove", onMove)
      el.removeEventListener("pointerenter", onEnter)
      el.removeEventListener("pointerleave", onLeave)
    }
  }, [interactive, maskSize, maskX, maskY, maskSizeMV])

  useEffect(() => {
    if (interactive) return
    const el = contentRef.current
    const w = el?.clientWidth ?? 720
    const h = el?.clientHeight ?? 240
    maskX.set(w / 2)
    maskY.set(h / 2)
    maskSizeMV.set(maskSize)
  }, [interactive, maskSize, maskX, maskY, maskSizeMV])

  const textTypography: React.CSSProperties = {
    margin: 0,
    boxSizing: "border-box",
    width: "100%",
    fontFamily:
      'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    userSelect: "none",
  }

  const rootStyle: React.CSSProperties = {
    ...style,
    position: "relative",
    boxSizing: "border-box",
    width: "100%",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    cursor: interactive ? "none" : undefined,
  }

  return (
    <div ref={containerRef} style={rootStyle} className={className}>
      <div ref={contentRef} style={{ position: "relative", width: "100%" }}>
        <div
          aria-label={text}
          style={{ ...textTypography, position: "relative", color: dimColor }}
        >
          {text}
        </div>
        <motion.div
          aria-hidden
          style={{
            ...textTypography,
            position: "absolute",
            top: 0,
            left: 0,
            color: brightColor,
            pointerEvents: "none",
            WebkitMaskImage: maskImage,
            maskImage: maskImage,
            WebkitMaskSize: "100%",
            maskSize: "100%",
            WebkitMaskRepeat: "no-repeat",
            maskRepeat: "no-repeat",
          }}
        >
          {text}
        </motion.div>
      </div>
    </div>
  )
}
