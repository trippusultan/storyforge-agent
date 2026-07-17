// Delivered by Originkit · stack: framer
// Set these props to match the Originkit preview:
//   overrides={{"glowColor":"#FFFFFF"}}
//   __curationVersion={1}
// Paste into a Framer code component. Property controls included.
import { addPropertyControls, ControlType, useIsStaticRenderer } from "framer"
import { useEffect, useRef, type CSSProperties } from "react"

function random(x: number): number {
    return (Math.sin(x * 12.9898) * 43758.5453) % 1
}

function noise2D(x: number, y: number): number {
    const i = Math.floor(x)
    const j = Math.floor(y)
    const fx = x - i
    const fy = y - j
    const a = random(i + j * 57)
    const b = random(i + 1 + j * 57)
    const c = random(i + (j + 1) * 57)
    const d = random(i + 1 + (j + 1) * 57)
    const ux = fx * fx * (3.0 - 2.0 * fx)
    const uy = fy * fy * (3.0 - 2.0 * fy)
    return (
        a * (1 - ux) * (1 - uy) +
        b * ux * (1 - uy) +
        c * (1 - ux) * uy +
        d * ux * uy
    )
}

function octavedNoise(
    x: number,
    octaves: number,
    lacunarity: number,
    gain: number,
    baseAmplitude: number,
    baseFrequency: number,
    time: number,
    seed: number,
    baseFlatness: number
): number {
    let y = 0
    let amplitude = baseAmplitude
    let frequency = baseFrequency
    for (let i = 0; i < octaves; i++) {
        let octaveAmplitude = amplitude
        if (i === 0) octaveAmplitude *= baseFlatness
        y +=
            octaveAmplitude *
            noise2D(frequency * x + seed * 100, time * frequency * 0.3)
        frequency *= lacunarity
        amplitude *= gain
    }
    return y
}

function corner(
    cx: number,
    cy: number,
    r: number,
    start: number,
    arc: number,
    p: number
) {
    const a = start + p * arc
    return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) }
}

function roundedRectPoint(
    t: number,
    left: number,
    top: number,
    width: number,
    height: number,
    radius: number
) {
    const sw = width - 2 * radius
    const sh = height - 2 * radius
    const arc = (Math.PI * radius) / 2
    const total = 2 * sw + 2 * sh + 4 * arc
    const dist = t * total
    let acc = 0
    if (dist <= acc + sw) {
        const p = (dist - acc) / sw
        return { x: left + radius + p * sw, y: top }
    }
    acc += sw
    if (dist <= acc + arc) {
        const p = (dist - acc) / arc
        return corner(
            left + width - radius,
            top + radius,
            radius,
            -Math.PI / 2,
            Math.PI / 2,
            p
        )
    }
    acc += arc
    if (dist <= acc + sh) {
        const p = (dist - acc) / sh
        return { x: left + width, y: top + radius + p * sh }
    }
    acc += sh
    if (dist <= acc + arc) {
        const p = (dist - acc) / arc
        return corner(
            left + width - radius,
            top + height - radius,
            radius,
            0,
            Math.PI / 2,
            p
        )
    }
    acc += arc
    if (dist <= acc + sw) {
        const p = (dist - acc) / sw
        return { x: left + width - radius - p * sw, y: top + height }
    }
    acc += sw
    if (dist <= acc + arc) {
        const p = (dist - acc) / arc
        return corner(
            left + radius,
            top + height - radius,
            radius,
            Math.PI / 2,
            Math.PI / 2,
            p
        )
    }
    acc += arc
    if (dist <= acc + sh) {
        const p = (dist - acc) / sh
        return { x: left, y: top + height - radius - p * sh }
    }
    acc += sh
    const p = (dist - acc) / arc
    return corner(left + radius, top + radius, radius, Math.PI, Math.PI / 2, p)
}

interface ElectricBorderProps {
    color: string
    bgColor: string
    speed: number
    chaos: number
    thickness: number
    borderRadius: number
    glow: boolean
    glowColor: string
    glowIntensity: number
    style?: CSSProperties
}

/**
 * Electric Border
 *
 * Wraps its content in a glowing border that crackles like electricity — drawn
 * on a canvas with octaved value-noise displacing a rounded-rect path.
 * Component inspired by @BalintFerenczy (codepen.io/BalintFerenczy/pen/KwdoyEN).
 *
 * @framerIntrinsicWidth 600
 * @framerIntrinsicHeight 600
 *
 * @framerSupportedLayoutWidth any-prefer-fixed
 * @framerSupportedLayoutHeight any-prefer-fixed
 */
export default function ElectricBorder(props: ElectricBorderProps) {
    const {
        color = "#FFFFFF",
        bgColor = "#000000",
        speed = 1,
        chaos = 4,
        thickness = 3.5,
        borderRadius = 0,
        glow = true,
        glowColor = "#00FFCC",
        glowIntensity = 10,
    } = props

    const isStatic = useIsStaticRenderer()
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const containerRef = useRef<HTMLDivElement>(null)
    const animationRef = useRef<number | null>(null)
    const timeRef = useRef(0)
    const lastFrameTimeRef = useRef(0)

    useEffect(() => {
        if (typeof window === "undefined") return
        const canvas = canvasRef.current
        const container = containerRef.current
        if (!canvas || !container) return
        const ctx = canvas.getContext("2d")
        if (!ctx) return

        const octaves = 10
        const lacunarity = 1.6
        const gain = 0.7
        // Chaos control is 0–20; map to the internal noise amplitude (0–1).
        const amplitude = chaos / 20
        const frequency = 10
        const baseFlatness = 0
        const displacement = 40
        // Glow — controlled only by Glow Intensity (1–10). More intensity =
        // brighter/thicker glow around the field, not a bigger field. Blur
        // sets the spread; passes stack the shadow so it builds up in strength.
        const gi = Math.max(1, Math.min(10, glowIntensity))
        const glowBlur = glow ? 6 + gi * 2 : 0
        const glowPasses = glow ? gi : 0
        // The border is drawn at the component's exact edges (field size ===
        // component size). PAD gives the canvas extra room so the crackle and
        // glow can bleed outside those edges without being clipped — the
        // container uses overflow:visible, like GlowingShape.
        const PAD = 120

        let width = 0,
            height = 0
        let lastDpr = Math.min(window.devicePixelRatio || 1, 2)

        function updateSize(mw?: number, mh?: number) {
            const rect = container.getBoundingClientRect()
            const w = Math.max(1, mw ?? rect.width)
            const h = Math.max(1, mh ?? rect.height)
            const cw = w + PAD * 2
            const ch = h + PAD * 2
            const dpr = Math.min(window.devicePixelRatio || 1, 2)
            canvas.width = Math.max(1, Math.floor(cw * dpr))
            canvas.height = Math.max(1, Math.floor(ch * dpr))
            canvas.style.width = `${cw}px`
            canvas.style.height = `${ch}px`
            canvas.style.left = `${-PAD}px`
            canvas.style.top = `${-PAD}px`
            width = w
            height = h
        }
        updateSize()

        function draw(currentTime: number) {
            const dpr = Math.min(window.devicePixelRatio || 1, 2)
            if (dpr !== lastDpr) {
                lastDpr = dpr
                updateSize()
            }

            if (!lastFrameTimeRef.current)
                lastFrameTimeRef.current = currentTime
            const dt = (currentTime - lastFrameTimeRef.current) / 1000
            timeRef.current += dt * speed
            lastFrameTimeRef.current = currentTime

            ctx.setTransform(1, 0, 0, 1, 0, 0)
            ctx.clearRect(0, 0, canvas.width, canvas.height)
            ctx.scale(dpr, dpr)
            ctx.lineCap = "round"
            ctx.lineJoin = "round"

            const left = PAD
            const top = PAD
            const bw = width
            const bh = height
            const maxR = Math.min(bw, bh) / 2
            const radius = Math.min(borderRadius, Math.max(0, maxR))
            const perim = 2 * (bw + bh) + 2 * Math.PI * radius
            const samples = Math.max(16, Math.floor(perim / 2))

            ctx.beginPath()
            for (let i = 0; i <= samples; i++) {
                const t = i / samples
                const pt = roundedRectPoint(t, left, top, bw, bh, radius)
                const xn = octavedNoise(
                    t * 8,
                    octaves,
                    lacunarity,
                    gain,
                    amplitude,
                    frequency,
                    timeRef.current,
                    0,
                    baseFlatness
                )
                const yn = octavedNoise(
                    t * 8,
                    octaves,
                    lacunarity,
                    gain,
                    amplitude,
                    frequency,
                    timeRef.current,
                    1,
                    baseFlatness
                )
                const dx = pt.x + xn * displacement
                const dy = pt.y + yn * displacement
                if (i === 0) ctx.moveTo(dx, dy)
                else ctx.lineTo(dx, dy)
            }
            ctx.closePath()

            // Glow hugs the stroke only (canvas shadow), never the whole box.
            // Fixed thin line so glow spread depends on Glow Intensity only,
            // independent of the core line Thickness. Stack passes so higher
            // intensity = stronger glow, same field size.
            if (glowBlur > 0) {
                ctx.lineWidth = 1
                ctx.strokeStyle = glowColor
                ctx.shadowColor = glowColor
                ctx.shadowBlur = glowBlur
                for (let p = 0; p < glowPasses; p++) ctx.stroke()
                ctx.shadowBlur = 0
            }
            // Crisp core line on top — the only thing Thickness controls.
            ctx.lineWidth = thickness
            ctx.strokeStyle = color
            ctx.stroke()

            // Always animate so the effect is live on the Framer canvas too.
            animationRef.current = requestAnimationFrame(draw)
        }

        animationRef.current = requestAnimationFrame(draw)

        const ro =
            typeof ResizeObserver !== "undefined"
                ? new ResizeObserver((entries) => {
                      // contentRect is reliable; getBoundingClientRect can be
                      // stale (pre-layout) when the effect first runs, which
                      // makes the field draw smaller than the component.
                      const cr = entries[0]?.contentRect
                      updateSize(cr?.width, cr?.height)
                  })
                : null
        ro?.observe(container)

        return () => {
            if (animationRef.current) cancelAnimationFrame(animationRef.current)
            ro?.disconnect()
        }
    }, [
        color,
        speed,
        chaos,
        thickness,
        borderRadius,
        glow,
        glowColor,
        glowIntensity,
        isStatic,
    ])

    return (
        // Fill whatever frame Framer gives us. overflow:visible so the crackle
        // and glow can bleed past the component edges (the canvas is padded by
        // PAD on every side) instead of being clipped at the frame.
        <div
            ref={containerRef}
            style={{
                position: "relative",
                overflow: "visible",
                isolation: "isolate",
                width: "100%",
                height: "100%",
                borderRadius,
                background: bgColor,
                ...props.style,
            }}
        >
            <canvas
                ref={canvasRef}
                style={{
                    position: "absolute",
                    display: "block",
                    pointerEvents: "none",
                    zIndex: 2,
                }}
            />
        </div>
    )
}

addPropertyControls(ElectricBorder, {
    color: {
        type: ControlType.Color,
        title: "Line Color",
        defaultValue: "#FFFFFF",
    },
    bgColor: {
        type: ControlType.Color,
        title: "Background",
        defaultValue: "#000000",
    },
    speed: {
        type: ControlType.Number,
        title: "Speed",
        defaultValue: 1,
        min: 0,
        max: 10,
        step: 1,
    },
    chaos: {
        type: ControlType.Number,
        title: "Chaos",
        defaultValue: 4,
        min: 0,
        max: 20,
        step: 1,
    },
    thickness: {
        type: ControlType.Number,
        title: "Line Thickness",
        defaultValue: 3.5,
        min: 0.5,
        max: 10,
        step: 0.5,
        unit: "px",
    },
    borderRadius: {
        type: ControlType.Number,
        title: "Radius",
        defaultValue: 0,
        min: 0,
        max: 100,
        unit: "px",
    },
    glow: { type: ControlType.Boolean, title: "Glow", defaultValue: true },
    glowColor: {
        type: ControlType.Color,
        title: "Glow Color",
        defaultValue: "#00FFCC",
        hidden: ({ glow }) => !glow,
    },
    glowIntensity: {
        type: ControlType.Number,
        title: "Glow Intensity",
        defaultValue: 10,
        min: 1,
        max: 10,
        step: 1,
        hidden: ({ glow }) => !glow,
    },
})
