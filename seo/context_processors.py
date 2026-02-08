from .models import SEOMetadata
from django.urls import resolve

def seo_context(request):
    """
    Context processor to inject SEO metadata into templates.
    Prioritizes exact path match, then view name match.
    """
    path = request.path
    seo_obj = None
    
    # Try to find by exact path
    try:
        seo_obj = SEOMetadata.objects.get(path=path)
    except SEOMetadata.DoesNotExist:
        # Try to find by view name
        try:
            match = resolve(path)
            if match.view_name:
                seo_obj = SEOMetadata.objects.filter(view_name=match.view_name).first()
        except:
            pass
            
    if seo_obj:
        return {'seo': seo_obj}
    return {}
