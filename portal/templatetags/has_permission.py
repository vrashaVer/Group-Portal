from django import template
from portal.models import UserRole

register = template.Library()

@register.filter
def has_permission(current_user, target_user):
    """
    Перевіряє, чи має поточний користувач право змінювати ролі іншого користувача.
    """
    # Поточний користувач є суперкористувачем
    if current_user.is_superuser:
        return True

    # Поточний користувач є власником і цільовий користувач не власник
    if UserRole.objects.filter(user=current_user, role__name="Owner").exists():
        return not UserRole.objects.filter(user=target_user, role__name="Owner").exists()

    # Поточний користувач є адміністратором і цільовий користувач не власник/адміністратор
    if UserRole.objects.filter(user=current_user, role__name="Admin").exists():
        return not UserRole.objects.filter(user=target_user, role__name__in=["Owner", "Admin"]).exists()

    # В інших випадках доступу немає
    return False