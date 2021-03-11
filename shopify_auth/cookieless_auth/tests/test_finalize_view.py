import json
from unittest.mock import patch

from django.shortcuts import reverse
from django.test import TestCase, override_settings

import shopify

from console.models import AppInstallation, AuthAppShopUser


def request_token(self, params):
    self.token = "TOKEN"


@override_settings(INTERCOM_ACCESS_TOKEN="")
class FinalizeViewTest(TestCase):
    def setUp(self):
        super().setUp()
        self.shop_patcher = patch("shopify.Shop", autospec=True)
        mck = self.shop_patcher.start()
        mck.current().currency = "CZK"
        self.addCleanup(self.shop_patcher.stop)
        self.url = reverse("cookieless-auth:finalize") + "?shop=random_shop"

    @patch.object(shopify.Session, "request_token", request_token)
    @patch("shopify.RecurringApplicationCharge", autospec=True)
    @patch("webhooks.webhook.init_webhooks_task")
    @patch("console.shopify_theme_update.update_theme_task")
    def test_creates_user(self, update_theme_mock, init_webhooks_mock, charge_mock):
        response = self.client.get(self.url)
        self.assertTrue(AuthAppShopUser.objects.filter(myshopify_domain="random_shop.myshopify.com").exists())
        self.assertEqual(response.status_code, 302)

    @patch.object(shopify.Session, "request_token", request_token)
    @patch("shopify.RecurringApplicationCharge", autospec=True)
    @patch("webhooks.webhook.init_webhooks_task")
    @patch("console.shopify_theme_update.update_theme_task")
    def test_valid_utm_params(self, update_theme_mock, init_webhooks_mock, charge_mock):
        utm_params = {
            "utm_source": "google",
            "utm_medium": "email",
            "utm_campaign": "spring_sale",
        }
        self.client.cookies["utm_params"] = json.dumps(utm_params)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

        app_install = AppInstallation.objects.get(app_id="candyrack", token="TOKEN")
        self.assertIsNotNone(app_install.utm_params_saved_at)
        self.assertEqual(app_install.utm_params, utm_params)

        # do not change utm_params when already exist
        utm_params["utm_campaign"] = "summer_sale"
        self.client.cookies["utm_params"] = json.dumps(utm_params)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(init_webhooks_mock.called)
        app_install.refresh_from_db()
        self.assertEqual(app_install.utm_params["utm_campaign"], "spring_sale")
        init_webhooks_mock.assert_called()
        update_theme_mock.assert_called()

    @patch.object(shopify.Session, "request_token", request_token)
    @patch("shopify.RecurringApplicationCharge", autospec=True)
    @patch("webhooks.webhook.init_webhooks_task")
    @patch("console.shopify_theme_update.update_theme_task")
    def test_corrupted_utm_params(self, update_theme_mock, init_webhooks_mock, charge_mock):
        self.client.cookies["utm_params"] = "xxxyyzz"
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(init_webhooks_mock.called)
        app_install = AppInstallation.objects.get(app_id="candyrack", token="TOKEN")
        self.assertIsNotNone(app_install.utm_params_saved_at)
        self.assertIsNone(app_install.utm_params)
        init_webhooks_mock.assert_called()
        update_theme_mock.assert_called()
