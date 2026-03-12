"""PetPooja API client — orders and menu data retrieval.

Credentials are read from restaurant.petpooja_config JSONB first,
falling back to global settings for single-tenant deployments.
"""

import logging
from datetime import date
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("ytip.etl.petpooja_client")

HTTP_TIMEOUT = 30  # seconds
# Verified live endpoints (from MEMORY.md)
ORDERS_URL = "https://api.petpooja.com/V1/thirdparty/generic_get_orders/"
MENU_URL = "https://onlineapipp.petpooja.com/thirdparty_fetch_dinein_menu"


class PetPoojaError(Exception):
    """Raised when the PetPooja API returns an error or is unreachable."""


class PetPoojaClient:
    """Thin HTTP client for PetPooja v2 API.

    Multi-tenant: credentials are resolved from the restaurant's
    petpooja_config JSONB first, global settings second.
    """

    def __init__(self, restaurant: Any, settings: Any) -> None:
        self._restaurant = restaurant
        self._settings = settings

    # ------------------------------------------------------------------
    # Credential resolution
    # ------------------------------------------------------------------

    def _cfg(self) -> Dict[str, str]:
        """Return the restaurant-level PetPooja config dict (may be empty)."""
        config = self._restaurant.petpooja_config
        if config is None:
            return {}
        return config

    def _get_orders_credentials(self) -> Dict[str, str]:
        """Resolve Orders API credentials (plain underscore keys)."""
        cfg = self._cfg()
        s = self._settings
        return {
            "app_key": cfg.get("app_key") or s.petpooja_app_key,
            "app_secret": cfg.get("app_secret") or s.petpooja_app_secret,
            "access_token": cfg.get("access_token") or s.petpooja_access_token,
            "rest_id": cfg.get("rest_id") or s.petpooja_restaurant_id,
        }

    def _get_menu_credentials(self) -> Dict[str, str]:
        """Resolve Menu API credentials (hyphenated keys per API spec)."""
        cfg = self._cfg()
        s = self._settings
        return {
            "app-key": cfg.get("menu_app_key") or s.petpooja_menu_app_key,
            "app-secret": cfg.get("menu_app_secret") or s.petpooja_menu_app_secret,
            "access-token": cfg.get("menu_access_token") or s.petpooja_menu_access_token,
            "rest_id": cfg.get("rest_id") or s.petpooja_rest_id,
            "cookie": cfg.get("cookie") or s.petpooja_cookie,
        }

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def get_orders(self, order_date: date) -> List[Dict[str, Any]]:
        """Fetch all orders for a given date from the PetPooja Orders API.

        Returns a list of raw order dicts exactly as the API returns them.
        Raises PetPoojaError on any failure (HTTP, API status, or parse).
        """
        creds = self._get_orders_credentials()
        payload = {
            "app_key": creds["app_key"],
            "app_secret": creds["app_secret"],
            "access_token": creds["access_token"],
            "restID": creds["rest_id"],
            "order_date": order_date.strftime("%Y-%m-%d"),
        }
        cookie = self._settings.petpooja_cookie or "PETPOOJA_API=mgnhpm6a8r5u11gatkpqhg7q00"

        logger.info(
            "Fetching PetPooja orders for restaurant=%s date=%s",
            self._restaurant.id,
            order_date,
        )

        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                response = client.post(
                    ORDERS_URL,
                    json=payload,
                    headers={"Cookie": cookie},
                )
        except httpx.RequestError as exc:
            raise PetPoojaError(
                "Orders API network error: " + str(exc)
            ) from exc

        if response.status_code != 200:
            raise PetPoojaError(
                "Orders API HTTP " + str(response.status_code)
                + " for restaurant=" + str(self._restaurant.id)
            )

        try:
            body = response.json()
        except Exception as exc:
            raise PetPoojaError("Orders API non-JSON response") from exc

        # API returns {"success": "1"/"1", "order_json": [...]}
        if str(body.get("success", "0")) != "1":
            message = body.get("message", "unknown error")
            raise PetPoojaError(
                "Orders API error: " + str(message)
                + " (restaurant=" + str(self._restaurant.id) + ")"
            )

        orders = body.get("order_json", [])
        if not isinstance(orders, list):
            raise PetPoojaError("Orders API returned non-list 'order_json' field")

        logger.info(
            "Fetched %d orders for restaurant=%s date=%s",
            len(orders),
            self._restaurant.id,
            order_date,
        )
        return orders

    def get_menu(self) -> Dict[str, Any]:
        """Fetch restaurant details (including menu) from the Menu API.

        The Menu API uses hyphenated credential keys and requires a cookie header.
        Returns the full response dict.
        Raises PetPoojaError on any failure.
        """
        creds = self._get_menu_credentials()
        cookie_value = creds.pop("cookie")
        rest_id = creds.pop("rest_id")

        payload = dict(creds)
        payload["tableNo"] = "1"
        payload["menuSharingCode"] = rest_id

        headers = {}
        if cookie_value:
            headers["Cookie"] = cookie_value

        logger.info("Fetching PetPooja menu for restaurant=%s", self._restaurant.id)

        try:
            with httpx.Client(timeout=HTTP_TIMEOUT) as client:
                response = client.post(MENU_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise PetPoojaError("Menu API network error: " + str(exc)) from exc

        if response.status_code != 200:
            raise PetPoojaError(
                "Menu API HTTP " + str(response.status_code)
                + " for restaurant=" + str(self._restaurant.id)
            )

        try:
            body = response.json()
        except Exception as exc:
            raise PetPoojaError("Menu API non-JSON response") from exc

        if body.get("status") != 1:
            message = body.get("message", "unknown error")
            raise PetPoojaError(
                "Menu API error: " + str(message)
                + " (restaurant=" + str(self._restaurant.id) + ")"
            )

        logger.info("Fetched menu for restaurant=%s", self._restaurant.id)
        return body
