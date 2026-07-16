# -*- coding: utf-8 -*-
"""
Frappe web page that serves the html5-qrcode.min.js library as raw JavaScript.
This avoids JSON wrapping issues that occur with frappe.whitelist() API methods.

Accessed at: http://yoursite/get_qr_scanner_js
"""
import os
import frappe

no_cache = 1


def get_context(context):
    """Serve the QR scanner JS library as raw JavaScript content."""
    js_path = frappe.get_app_path("workforce_manager", "public", "js", "html5-qrcode.min.js")
    if os.path.exists(js_path):
        with open(js_path, "rb") as f:
            content = f.read()
        # Set raw response - no template wrapping
        frappe.response["content_type"] = "application/javascript"
        frappe.local.response["type"] = "download"
        frappe.local.response["filecontent"] = content
        frappe.local.response["filename"] = "html5-qrcode.min.js"
    else:
        frappe.local.response["type"] = "download"
        frappe.local.response["filecontent"] = b"// QR scanner library not found"
        frappe.local.response["content_type"] = "application/javascript"
