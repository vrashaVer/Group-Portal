import re
from django import template

register = template.Library()

@register.filter
def extract_video_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    if match:
        return match.group(1)
    return None


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
