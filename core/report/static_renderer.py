from pathlib import Path
from datetime import date
from typing import Dict, Any, Optional, Union
import importlib


class StaticReportRenderer:
    def __init__(
        self,
        template_path: Optional[Union[str, Path]] = None,
        output_dir: Optional[Union[str, Path]] = None,
    ):
        base_dir = Path(__file__).resolve().parent
        if template_path is None:
            template_path = base_dir / "template" / "static_report.html"
        project_root = base_dir.parent.parent
        if output_dir is None:
            output_dir = project_root / "data" / "reports"
        self.template_path = (
            Path(template_path)
            if not isinstance(template_path, Path)
            else template_path
        )
        self.output_dir = (
            Path(output_dir) if not isinstance(output_dir, Path) else output_dir
        )

    def render(self, data: Dict[str, Any]) -> str:
        jinja2 = importlib.import_module("jinja2")
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_path.parent)),
            autoescape=jinja2.select_autoescape(["html"]),
        )
        tpl = env.get_template(self.template_path.name)
        return tpl.render(data=data)

    def save(self, data: Dict[str, Any], filename: Optional[str] = None) -> Path:
        html = self.render(data)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if filename is None:
            d = data.get("meta", {}).get("date")
            if not d:
                d = date.today().isoformat()
            filename = f"report_{d}.html"
        out_path = self.output_dir / filename
        out_path.write_text(html, encoding="utf-8")
        return out_path
