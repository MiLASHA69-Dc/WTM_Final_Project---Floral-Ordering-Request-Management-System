from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from shop import views as shop_views

urlpatterns = [
    path('', shop_views.home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('orders/', include('orders.urls')),
    path('catalog/', include('catalog.urls')),   # staff: florist/..., management/...
    path('catalog/', include('shop.urls')),      # customer catalog
    path('cart/', include('shop.cart_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
