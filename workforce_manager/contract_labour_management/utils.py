# -*- coding: utf-8 -*-
"""
Shared utilities for Contract Labour Management.
Statutory rates below are standard India defaults — edit these constants
to match your state/company specific rates. No code changes needed elsewhere.
"""
import math
import frappe
from frappe.utils import flt, getdate, get_first_day, get_last_day, add_months

# ---------------------------------------------------------------------------
# STATUTORY RATE CONFIG (edit these to match your company/state)
# ---------------------------------------------------------------------------
PF_EMPLOYEE_RATE = 12.0          # % of gross wage (PF wage ceiling ignored for simplicity)
ESI_EMPLOYEE_RATE = 0.75         # % of gross wage
ESI_WAGE_CEILING = 21000.0       # ESI not applicable above this gross wage/month
PT_SLABS = [                     # Professional Tax monthly slabs (edit per state)
    (0, 15000, 0.0),
    (15000, 25000, 175.0),
    (25000, float("inf"), 200.0),
]
LWF_EMPLOYEE_AMOUNT = 20.0       # Labour Welfare Fund - fixed employee contribution
DEFAULT_SERVICE_CHARGE_PERCENT = 10.0   # Contractor service charge on wages, if not set on invoice
GST_RATE = 18.0                  # GST % on (wages + service charge)
GEOFENCE_DEFAULT_RADIUS_M = 50.0

STANDARD_SHIFT_HOURS = 8.0       # used when shift-specific hours aren't computable


def haversine_distance_m(lat1, lon1, lat2, lon2):
    """Return distance in meters between two lat/long points."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    lat1, lon1, lat2, lon2 = map(flt, [lat1, lon1, lat2, lon2])
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def calc_pt(gross_wage):
    """Professional Tax based on PT_SLABS."""
    gross_wage = flt(gross_wage)
    for low, high, amount in PT_SLABS:
        if low <= gross_wage < high:
            return amount
    return 0.0


def calc_statutory_deductions(gross_wage):
    """Return dict of PF/ESI/PT/LWF employee-side deductions for a given gross wage."""
    gross_wage = flt(gross_wage)
    pf = round(gross_wage * PF_EMPLOYEE_RATE / 100.0, 2)
    esi = round(gross_wage * ESI_EMPLOYEE_RATE / 100.0, 2) if gross_wage <= ESI_WAGE_CEILING else 0.0
    pt = calc_pt(gross_wage)
    lwf = LWF_EMPLOYEE_AMOUNT
    total = pf + esi + pt + lwf
    return {
        "pf_deduction": pf,
        "esi_deduction": esi,
        "pt_deduction": pt,
        "lwf_deduction": lwf,
        "total_deduction": total,
        "net_wage": round(gross_wage - total, 2),
    }


def month_date_range(wage_month):
    """
    wage_month is expected as 'YYYY-MM' (e.g. '2026-07').
    Returns (start_date, end_date) as date objects.
    """
    first = getdate(f"{wage_month}-01")
    return get_first_day(first), get_last_day(first)


def default_statutory_due_date(wage_month):
    """PF/ESI/PT challans are typically due by the 15th of the following month."""
    first_of_month = getdate(f"{wage_month}-01")
    next_month_first = add_months(first_of_month, 1)
    return next_month_first.replace(day=15)
