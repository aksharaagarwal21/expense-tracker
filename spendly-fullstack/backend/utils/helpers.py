from flask import jsonify
import calendar
from datetime import date


def success(data=None, message="Success", status=200):
    r = {"success": True, "message": message}
    if data is not None:
        r["data"] = data
    return jsonify(r), status


def error(message="Error", status=400):
    return jsonify({"success": False, "error": message}), status


def get_month_range(year, month):
    start = date(year, month, 1)
    end   = date(year, month, calendar.monthrange(year, month)[1])
    return start, end


def paginate(query, page, per_page):
    p = query.paginate(page=page, per_page=per_page, error_out=False)
    return {"items": p.items, "total": p.total, "page": p.page,
            "pages": p.pages, "per_page": p.per_page}
