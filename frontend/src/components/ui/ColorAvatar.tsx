interface ColorAvatarProps {
  name: string
  color: string
  size?: 'sm' | 'md' | 'lg'
  ringColor?: string
}

export default function ColorAvatar({ name, color, size = 'md', ringColor }: ColorAvatarProps) {
  const initials = name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  const sizeClass =
    size === 'sm'
      ? 'w-7 h-7 text-xs'
      : size === 'md'
        ? 'w-9 h-9 text-sm'
        : 'w-12 h-12 text-base'

  // box-shadow: inner gap layer (zinc-900) + outer ring in player color
  const shadow = ringColor
    ? `0 0 0 2px #18181b, 0 0 0 4px ${ringColor}`
    : undefined

  return (
    <div
      className={`${sizeClass} rounded-full flex items-center justify-center font-semibold text-zinc-950 shrink-0 select-none`}
      style={{ backgroundColor: color, boxShadow: shadow }}
    >
      {initials}
    </div>
  )
}
