from django.shortcuts import reverse
from django.test import Client, TestCase
from django.test.client import RequestFactory

from console.factories import AuthAppShopUserFactory
from cookieless_auth.views import get_scope_permission
from upsell_platform.shopify_apps import ShopifyApp


class GetScopePermissionTest(TestCase):
    def test_get_scope_permission(self):
        self.client = Client()
        rf = RequestFactory()
        shop = AuthAppShopUserFactory()
        request = rf.get(reverse("console:dashboard") + f"?{shop.myshopify_domain}")
        request.user = shop
        request.shopify_app = ShopifyApp(
            id="test_app",
            config={
                "API_KEY": "x",
                "API_SECRET": "y",
                "HOSTS": [],
                "APP_NAME": "test",
                "API_SCOPES": ["read_products"],
                "WEBHOOKS_BASE_URL": "",
                "BILLING_FUNCTION": None,
            },
        )
        response = get_scope_permission(request, shop.myshopify_domain)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, shop.myshopify_domain)
