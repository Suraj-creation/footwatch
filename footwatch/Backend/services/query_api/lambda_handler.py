from __future__ import annotations

from mangum import Mangum

from services.query_api.app import app

handler = Mangum(app, api_gateway_base_path="/query")
