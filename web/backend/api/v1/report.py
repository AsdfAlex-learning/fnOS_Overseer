import importlib
from flask import jsonify
from web.backend.api.v1 import bp, require_super_admin
from core.report.daily_report import DailyReportBuilder
from core.report.static_renderer import StaticReportRenderer
from web.backend.models.data_models import ok, err


@bp.post("/report/generate")
@require_super_admin
def generate_report():
    try:
        data = DailyReportBuilder().build()
        out = StaticReportRenderer().save(data)
        return jsonify(ok({"path": str(out)}))
    except Exception:
        return jsonify(err(500, "generate_failed")), 500
