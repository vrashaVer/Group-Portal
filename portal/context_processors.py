from .models import ProfilePhoto

def profile_photo_context(request):
    profile_photo = None
    if request.user.is_authenticated:
        profile_photo = ProfilePhoto.objects.filter(user=request.user).first()
    return {'profile_photo': profile_photo}