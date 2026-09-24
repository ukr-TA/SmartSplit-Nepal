/**
 * SmartSplit Nepal logo: a Nepali 2-rupee coin (farmer ploughing with an ox under the Himalaya)
 * with three arrows circling it — money shared and settled between
 * friends. Artwork: public/logo.svg
 */
export default function BrandMark({ size = 36 }) {
  return (
    <img
      src="/logo.svg"
      width={size}
      height={size}
      alt="SmartSplit Nepal"
      style={{ display: 'block', flexShrink: 0 }}
    />
  )
}
