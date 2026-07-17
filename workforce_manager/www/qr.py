import frappe
import os


def get_context(context):
    """Load the QR code generation library and inject it into the page context.

    This avoids relying on Frappe's /assets/ URL path (which isn't
    serving individual files) or external CDNs (which need internet).
    """
    app_path = frappe.get_app_path("workforce_manager")
    js_path = os.path.join(app_path, "public", "js", "qrcode.min.js")
    try:
        with open(js_path) as f:
            context["qrcode_js"] = f.read()
    except FileNotFoundError:
        context["qrcode_js"] = "console.warn('qrcode library not found — falling back to CDN');"
    except Exception as e:
        context["qrcode_js"] = "console.warn('Failed to load qrcode library — falling back to CDN');"
