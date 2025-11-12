from django import template

register = template.Library()

@register.filter
def range_inclusive(start, end):
    """Genera un rango de números desde 'start' hasta 'end' (ambos incluidos)."""
    try:
        start, end = int(start), int(end)
        return range(start, end + 1)
    except Exception:
        return []
