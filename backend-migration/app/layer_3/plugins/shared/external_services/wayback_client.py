from app.layer_3.plugins.shared.foundation.caching_http_client import CachingHttpClient
from app.layer_3.steps.contracts import ExtractionState, ExtractionContext

class WaybackClient(CachingHttpClient):
    
    name = 'de.zbmed.wayback.client'

    def __init__(self, context: ExtractionContext, state: ExtractionState):
        super().__init__(context, state)

    def get_archive_url(self):
        archive_url = f"https://web.archive.org/web/{self.context.repo_url}"
        try:
            res = self._caching_get(archive_url)
            if res.ok:
                return archive_url
            return None
        except:
            return None
    
    def _build_headers(self):
        return {}