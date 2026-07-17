import frappe
import os


def get_context(context):
    """Load the jsQR library and inject it into the page context.

    This avoids relying on Frappe's /assets/ URL path (which isn't
    serving individual files) or external CDNs (which need internet).
    """
    app_path = frappe.get_app_path("workforce_manager")
    js_path = os.path.join(app_path, "public", "js", "jsqr.min.js")
    try:
        with open(js_path) as f:
            context["jsqr_js"] = f.read()
    except FileNotFoundError:
        context["jsqr_js"] = "console.warn('jsQR library not found — falling back to CDN');"
    except Exception as e:
        context["jsqr_js"] = "console.warn('Failed to load jsQR library — falling back to CDN');"
