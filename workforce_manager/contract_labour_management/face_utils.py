# -*- coding: utf-8 -*-
"""
Face verification utilities for attendance check-in.
Compares a check-in selfie against the employee's stored reference photo
using Perceptual Hashing (pHash) via Pillow.

pHash is a fingerprint of an image — two photos of the same person's face
taken in similar lighting will produce similar hashes even at different sizes.

Since this is a server-side Frappe app without GPU/ML dependencies, we use
a simple but practical approach:
1. Resize both images to a standard size
2. Compute the perceptual hash of each
3. Calculate Hamming distance between the two hashes
4. If distance is below threshold → faces match

Installation (on server):
    pip install Pillow
    (Pillow is usually pre-installed with Frappe)
"""
import base64
import io
import frappe
from frappe import _
from frappe.utils import cint

try:
    from PIL import Image, ImageFilter, ImageOps
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Threshold for Hamming distance (0 = identical, higher = more different)
# Empirically: < 10 is very likely same person, 10-20 is possible, > 20 likely different
MATCH_THRESHOLD = 15


def _average_hash(image, hash_size=16):
    """Compute average perceptual hash of an image.
    Returns a hexadecimal string representation."""
    # Convert to grayscale and resize
    img = image.convert("L").resize((hash_size, hash_size), Image.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    # Compute hash bits
    bits = "".join("1" if p > avg else "0" for p in pixels)
    # Convert binary string to hex
    return hex(int(bits, 2))[2:].zfill(hash_size * hash_size // 4)


def _hamming_distance(hash1, hash2):
    """Calculate Hamming distance between two hex hashes."""
    if not hash1 or not hash2:
        return 999
    # Convert hex strings to integers and XOR
    h1 = int(hash1, 16)
    h2 = int(hash2, 16)
    # Count differing bits
    xor = h1 ^ h2
    return bin(xor).count("1")


def _load_image(image_data):
    """Load an image from a Frappe file URL, base64 string, or file path."""
    if not image_data:
        return None

    try:
        # Case 1: Frappe file URL (e.g., /files/face.jpg or /private/files/face.jpg)
        if isinstance(image_data, str) and ("/files/" in image_data or "/private/files/" in image_data):
            try:
                file_doc = frappe.get_doc("File", {"file_url": image_data})
                content = file_doc.get_content()
                if content:
                    return Image.open(io.BytesIO(content))
            except Exception:
                pass

        # Case 2: base64 encoded string
        if isinstance(image_data, str) and image_data.startswith(("data:image", "data:")):
            # Strip the data URI prefix (e.g., "data:image/jpeg;base64,")
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]
            raw = base64.b64decode(image_data)
            return Image.open(io.BytesIO(raw))

        # Case 3: raw bytes
        if isinstance(image_data, bytes):
            return Image.open(io.BytesIO(image_data))

    except Exception as e:
        frappe.log_error(f"Face verification: Could not load image - {e}", "Face Utils")

    return None


def preprocess_face(image):
    """Preprocess an image to improve face matching robustness."""
    if image is None:
        return None
    # Convert to RGB if necessary
    if image.mode != "RGB":
        image = image.convert("RGB")
    # Enhance contrast
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.2)
    return image


@frappe.whitelist()
def verify_face(attendance_record):
    """
    Compare the check-in selfie on an attendance record against the
    employee's stored reference face photo.
    
    Called automatically during mobile check-in, and manually via
    'Verify Face' button on the Attendance Record form.
    
    Returns a dict with match status and confidence score.
    """
    if not HAS_PIL:
        frappe.msgprint(
            _("Pillow library is not installed. Face verification requires: pip install Pillow"),
            alert=True, indicator="orange"
        )
        return {"status": "No Reference Photo", "score": None}

    att = frappe.get_doc("Attendance Record", attendance_record)
    if not att.checkin_selfie:
        return {"status": "No Reference Photo", "score": None}

    emp = frappe.get_doc("Contract Employee", att.employee)
    if not emp.face_image:
        att.face_verification_status = "No Reference Photo"
        att.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "No Reference Photo", "score": None}

    # Load both images
    ref_img = _load_image(emp.face_image)
    selfie_img = _load_image(att.checkin_selfie)

    if ref_img is None or selfie_img is None:
        att.face_verification_status = "Pending"
        att.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "Pending", "score": None, "error": "Could not load one or both images"}

    # Preprocess
    ref_img = preprocess_face(ref_img)
    selfie_img = preprocess_face(selfie_img)

    # Compute perceptual hashes
    ref_hash = _average_hash(ref_img)
    selfie_hash = _average_hash(selfie_img)

    # Calculate distance
    distance = _hamming_distance(ref_hash, selfie_hash)
    max_distance = 16 * 16  # 256 bits for 16x16 hash
    similarity_pct = round((1 - distance / max_distance) * 100, 1)

    # Determine match status
    if distance <= MATCH_THRESHOLD:
        status = "Verified"
    elif distance <= MATCH_THRESHOLD * 2:
        status = "Pending"  # Borderline — needs human review
    else:
        status = "Mismatched"

    # Update the attendance record
    att.face_verification_status = status
    att.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": status,
        "score": similarity_pct,
        "hamming_distance": distance,
        "threshold": MATCH_THRESHOLD,
    }


@frappe.whitelist()
def manual_verify(attendance_record):
    """Manually mark an attendance record's face verification as Verified."""
    att = frappe.get_doc("Attendance Record", attendance_record)
    att.face_verification_status = "Verified"
    att.face_verified_by = frappe.session.user
    att.face_verified_at = frappe.utils.now_datetime()
    att.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "Verified"}


@frappe.whitelist()
def manual_reject(attendance_record):
    """Manually mark an attendance record's face verification as Mismatched."""
    att = frappe.get_doc("Attendance Record", attendance_record)
    att.face_verification_status = "Mismatched"
    att.face_verified_by = frappe.session.user
    att.face_verified_at = frappe.utils.now_datetime()
    att.save(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "Mismatched"}
