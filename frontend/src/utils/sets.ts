/** Return a new Set with `value` added if missing, or removed if present. */
export function toggleSetValue<T>(values: Set<T>, value: T) {
  const next = new Set(values);
  if (next.has(value)) {
    next.delete(value);
  } else {
    next.add(value);
  }
  return next;
}
