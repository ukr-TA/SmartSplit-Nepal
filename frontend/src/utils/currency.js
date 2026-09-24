// NPR-first money formatting used everywhere in the UI.
// Nepal uses the South Asian digit grouping (1,00,000), which the en-IN locale provides.
const formatter = new Intl.NumberFormat('en-IN', {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

/** formatNPR(1250) -> "Rs. 1,250" ; formatNPR(-500, { sign: true }) -> "-Rs. 500" */
export function formatNPR(amount, { sign = false } = {}) {
  const value = Number(amount) || 0
  const abs = formatter.format(Math.abs(value))
  if (value < 0) return `-Rs. ${abs}`
  if (sign && value > 0) return `+Rs. ${abs}`
  return `Rs. ${abs}`
}
