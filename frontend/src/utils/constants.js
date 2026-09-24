import {
  Bed, Briefcase, Bus, GraduationCap, Heart, Home, Lightbulb, MoreHorizontal,
  Plane, Popcorn, ShoppingBag, Sparkles, Users, UtensilsCrossed, Building2,
} from 'lucide-react'

export const CATEGORIES = [
  { value: 'food', label: 'Food', icon: UtensilsCrossed, emoji: '🍛', tint: '#fff4e5', ink: '#b45309' },
  { value: 'transport', label: 'Transport', icon: Bus, emoji: '🚌', tint: '#e8f1fd', ink: '#1d4ed8' },
  { value: 'hotel', label: 'Hotel', icon: Bed, emoji: '🏨', tint: '#f1ecfe', ink: '#6d28d9' },
  { value: 'entertainment', label: 'Entertainment', icon: Popcorn, emoji: '🎉', tint: '#fdebf3', ink: '#be185d' },
  { value: 'shopping', label: 'Shopping', icon: ShoppingBag, emoji: '🛍️', tint: '#e7f8f1', ink: '#047857' },
  { value: 'education', label: 'Education', icon: GraduationCap, emoji: '📚', tint: '#eaf6fb', ink: '#0e7490' },
  { value: 'utilities', label: 'Utilities', icon: Lightbulb, emoji: '💡', tint: '#fef9e3', ink: '#a16207' },
  { value: 'rent', label: 'Rent', icon: Building2, emoji: '🏠', tint: '#eef2f6', ink: '#334155' },
  { value: 'other', label: 'Other', icon: MoreHorizontal, emoji: '🧾', tint: '#f1f3f2', ink: '#4b5563' },
]

export const categoryOf = (value) => CATEGORIES.find((c) => c.value === value) || CATEGORIES.at(-1)

export const GROUP_TYPES = [
  { value: 'trip', label: 'Trip', icon: Plane, hint: 'Travel with trip dashboard & analytics' },
  { value: 'college', label: 'College', icon: GraduationCap, hint: 'Projects, printing, canteen' },
  { value: 'friends', label: 'Friends', icon: Users, hint: 'Hangouts, food, movies' },
  { value: 'roommates', label: 'Roommates', icon: Home, hint: 'Rent, bills, groceries' },
  { value: 'family', label: 'Family', icon: Heart, hint: 'Household & family events' },
  { value: 'custom', label: 'Custom', icon: Sparkles, hint: 'Anything else' },
]

export const groupTypeOf = (value) => GROUP_TYPES.find((t) => t.value === value) || { label: 'Group', icon: Briefcase }

export const PAYMENT_METHODS = {
  esewa: { label: 'eSewa', color: '#41a124', soft: '#ecf8e8', tagline: 'Pay with your eSewa wallet' },
  khalti: { label: 'Khalti', color: '#5c2d91', soft: '#f2ecfa', tagline: 'Pay with your Khalti wallet' },
  cash: { label: 'Cash', color: '#0f766e', soft: '#e6f5f3', tagline: 'Already paid in person' },
}
