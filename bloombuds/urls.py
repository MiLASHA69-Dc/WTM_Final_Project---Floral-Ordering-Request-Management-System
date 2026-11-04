from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from shop import views as shop_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', shop_views.home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('catalog/', include('shop.urls')),
    path('cart/', include('shop.cart_urls')),
    path('orders/', include('orders.urls')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)