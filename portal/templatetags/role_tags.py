from django import template

register = template.Library()

@register.filter
def has_role(user, role_name):
    return user.roles.filter(role__name=role_name).exists()