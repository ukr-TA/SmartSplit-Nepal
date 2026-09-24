import { useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'
import { mlApi } from '../api/services'
import { CategoryIcon } from './ui'
import { CATEGORIES } from '../utils/constants'

const MIN_CHARS = 4
const DEBOUNCE_MS = 450
const MIN_CONFIDENCE = 0.35

const labelOf = (value) => CATEGORIES.find((c) => c.value === value)?.label || value

/**
 * Shows the category predicted by the ML model for what the user has typed, and applies it
 * with one click. It is only a hint: nothing is rendered if the model is unavailable, unsure,
 * already agrees with the chosen category, or the user waved the suggestion away.
 *
 * The suggestion carries the text it was made for, so a stale response for an older
 * description is simply ignored during render instead of being cleared in an effect.
 */
export default function CategorySuggestion({ description, amount, category, onApply }) {
  const [suggestion, setSuggestion] = useState(null)
  const [dismissedFor, setDismissedFor] = useState(null)

  const text = (description || '').trim()

  useEffect(() => {
    if (text.length < MIN_CHARS) return undefined
    const timer = setTimeout(() => {
      mlApi
        .suggestCategory(text, amount)
        .then((result) => {
          if (result && result.source !== 'empty') setSuggestion({ ...result, text })
        })
        .catch(() => {})
    }, DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [text, amount])

  const visible =
    suggestion &&
    suggestion.text === text &&
    text.length >= MIN_CHARS &&
    suggestion.confidence >= MIN_CONFIDENCE &&
    suggestion.category !== category &&
    dismissedFor !== text

  if (!visible) return null

  return (
    <div className="ml-suggestion">
      <Sparkles size={15} className="ml-spark" />
      <span className="grow">
        Suggested category: <strong>{labelOf(suggestion.category)}</strong>
        <small className="muted"> · {Math.round(suggestion.confidence * 100)}% confident</small>
      </span>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => onApply(suggestion.category)}>
        <CategoryIcon category={suggestion.category} size={20} /> Use this
      </button>
      <button type="button" className="link-btn small" onClick={() => setDismissedFor(text)}>
        No thanks
      </button>
    </div>
  )
}
